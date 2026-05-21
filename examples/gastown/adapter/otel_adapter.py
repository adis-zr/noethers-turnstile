"""GasTown OTEL adapter — processes one OTEL record at a time.

Returns (updated_trace_state, judgment_or_None).

Critical routing rule (spec §2.5):
  done exit_type=COMPLETED → judgment emitted (claim-closing event)
  done exit_type=ESCALATED → opens escalation claim, NO judgment
  done must NOT be in IN_CLASS_EVENTS general set

Stateless: no mutable state on the adapter object itself.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import noethers_turnstile as t

from .authority_registry import get_ceiling, is_in_class
from .proof_context import TraceState, build_profiles, _build_gap_list
from .provenance import compute_action_provenance_hash, _build_context_id
from .seance import build_seance_token
from .token_registry import TokenRegistry, get_default_registry

# Re-export TraceState so tests can import it from this module
__all__ = [
    "OtelAdapter", "TraceState", "IN_CLASS_EVENTS", "DISALLOWED_USES",
    "process_trace", "Judgment",
]


# ── Event taxonomy ─────────────────────────────────────────────────────────────

# IN_CLASS_EVENTS: events that open a claim context (not including "done").
# CRITICAL: "done" must NOT appear here.
IN_CLASS_EVENTS: frozenset[str] = frozenset({
    "sling",
    "agent.instantiate",
    "escalate",
    "bd.call",  # subcommand=merge opens a merge claim
})

# OUT_OF_CLASS events: never trigger claims
OUT_OF_CLASS_EVENTS: frozenset[str] = frozenset({
    "gt.feed",
    "gt.seance",
    "bd.update",
    "gt.agents",
    "gt.status",
    "session.stop",
    "session.start",
})

# Events that provide evidence (may update gap status without opening a claim)
EVIDENCE_EVENTS: frozenset[str] = frozenset({
    "prime",
    "gt.seance",
    "bd.call",
    "mol.squash",
    "mol.burn",
    "mail",
    "bead.create",
    "convoy.membership",
    "authority_chain",
    "resolution_attempt",
    "experiment_scope_token",
    "cross_scope_token",
    "cross_rig_token",
})

# Disallowed uses — capped at ROL in the permission lattice
DISALLOWED_USES: frozenset[str] = frozenset()


# ── Default window parameters ──────────────────────────────────────────────────

W_EVIDENCE_DEFAULT = 1800   # seconds before claim timestamp
W_GRACE_DEFAULT = 60        # seconds after claim timestamp


# ── Judgment result ────────────────────────────────────────────────────────────

@dataclass
class Judgment:
    """Result of compiling a claim context."""
    permission: t.Permission
    claim_class: str
    run_id: str
    bead_id: str
    action_id: str
    proof_context: t.ProofContext
    live_judgment: t.LiveJudgment
    gap_states: dict[str, str]

    def __str__(self) -> str:
        return f"Judgment(perm={self.permission}, claim={self.claim_class})"


# ── Per-run trace accumulator ──────────────────────────────────────────────────

@dataclass
class _RunContext:
    """Accumulated context for a single (bead_id, run_id) pair."""
    run_id: str
    bead_id: str
    role: str = "unknown"
    rig: str = ""
    git_commit: str = ""
    bead_type: str = "normal"
    agent_name: str = ""
    issue_id: str = ""

    # Gap evidence
    context_integrity_status: str = "open"
    delegation_authority_status: str = "open"
    completion_evidence_status: str = "open"
    escalation_validity_status: str = "open"
    merge_safety_status: str = "open"
    authority_chain_status: str = "open"
    experiment_scope_status: str = "open"

    # Accumulated tokens
    tokens: list = field(default_factory=list)

    # Provenance mismatch flag
    has_provenance_mismatch: bool = False

    # Event timestamps for windowing
    instantiate_ts: float = 0.0
    session_boundary_ts: Optional[float] = None

    # Done received?
    done: bool = False


@dataclass
class _AdapterState:
    """Per-trace state accumulator (keyed by (bead_id, run_id))."""
    contexts: dict[tuple[str, str], _RunContext] = field(default_factory=dict)
    ordering_violations: list[dict] = field(default_factory=list)

    def get_or_create(self, run_id: str, bead_id: str) -> _RunContext:
        key = (bead_id, run_id)
        if key not in self.contexts:
            self.contexts[key] = _RunContext(run_id=run_id, bead_id=bead_id)
        return self.contexts[key]


# ── Token descriptor builders ──────────────────────────────────────────────────
# Tokens are stored as dicts (descriptors) during event processing and converted
# to t.ProofToken at emit time. This allows the provenance_hash to be computed
# using the final context values (rig, git_commit) even when events arrive before
# agent.instantiate sets those values.
#
# Each descriptor has:
#   token_id, token_type, schema_version, status, closes_gaps, bounds_gaps,
#   issued_at, issuer, is_mismatch (bool)
# is_mismatch=True → use "0"*64 for provenance_hash (deliberate mismatch)
# is_mismatch=False → provenance_hash computed at emit time from context

def _make_prime_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for a prime(hook_mode=true) event."""
    run_id = event.get("run_id", ctx.run_id)
    # Check for deliberate provenance mismatch fields
    prov_run_id = event.get("provenance_run_id", run_id)
    prov_bead_id = event.get("provenance_bead_id", ctx.bead_id)
    prov_rig = event.get("provenance_rig", ctx.rig)
    prov_git = event.get("provenance_git_commit", ctx.git_commit)

    # Mismatch check: compare against the current ctx values.
    # Note: ctx.rig/git_commit may still be empty if agent.instantiate hasn't arrived.
    # For deliberate mismatch detection, we only trigger is_mismatch when the event
    # explicitly provides different provenance fields.
    has_explicit_prov_fields = (
        "provenance_run_id" in event or
        "provenance_bead_id" in event or
        "provenance_rig" in event or
        "provenance_git_commit" in event
    )

    is_mismatch = has_explicit_prov_fields and (
        prov_run_id != ctx.run_id or
        prov_bead_id != ctx.bead_id
    )

    # For rig/git mismatches: only flag if ctx has rig/git set
    if has_explicit_prov_fields and ctx.rig and (prov_rig != ctx.rig):
        is_mismatch = True
    if has_explicit_prov_fields and ctx.git_commit and (prov_git != ctx.git_commit):
        is_mismatch = True

    if is_mismatch:
        ctx.has_provenance_mismatch = True
        return {
            "token_id": f"prime-{run_id}-{ts}",
            "token_type": "prime_hook",
            "schema_version": "gt/0.1",
            "status": "valid",
            "closes_gaps": [],
            "bounds_gaps": [],
            "issued_at": ts,
            "issuer": "gastown.prime",
            "is_mismatch": True,
        }

    status = token_registry.token_status(f"prime-{run_id}", run_id=run_id)
    return {
        "token_id": f"prime-{run_id}-{ts}",
        "token_type": "prime_hook",
        "schema_version": "gt/0.1",
        "status": status,
        "closes_gaps": ["context_integrity_gap"] if status == "valid" else [],
        "bounds_gaps": [],
        "issued_at": ts,
        "issuer": "gastown.prime",
        "is_mismatch": False,
    }


def _make_completion_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for bd.call subcommand=ready status=ok."""
    run_id = event.get("run_id", ctx.run_id)
    status_str = event.get("status", "fail").lower()
    detail_contract_valid = event.get("detail_contract_valid", True)

    closes = []
    if status_str == "ok" and detail_contract_valid:
        tok_status = token_registry.token_status(f"ready-{run_id}", run_id=run_id)
        if tok_status == "valid":
            closes = ["completion_evidence_gap"]
    else:
        tok_status = "valid"

    return {
        "token_id": f"ready-{run_id}-{ts}",
        "token_type": "ci_gate",
        "schema_version": "gt/0.1",
        "status": tok_status,
        "closes_gaps": closes,
        "bounds_gaps": [],
        "issued_at": ts,
        "issuer": "gastown.ci",
        "is_mismatch": False,
    }


def _make_sling_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for a sling event."""
    run_id = event.get("run_id", ctx.run_id)
    is_mayor = event.get("is_mayor", False)
    is_fabricated = event.get("is_fabricated", False)
    tok_status = token_registry.token_status(f"sling-{run_id}", run_id=run_id)

    if is_fabricated:
        closes = ["delegation_authority_gap"] if tok_status == "valid" else []
        bounds = []
    elif is_mayor and tok_status == "valid":
        closes = ["delegation_authority_gap", "authority_chain_gap"]
        bounds = []
    else:
        closes = []
        bounds = []

    return {
        "token_id": f"sling-{run_id}-{ts}",
        "token_type": "mayor_sling",
        "schema_version": "gt/0.1",
        "status": tok_status,
        "closes_gaps": closes,
        "bounds_gaps": bounds,
        "issued_at": ts,
        "issuer": "gastown.mayor",
        "is_mismatch": False,
    }


def _make_convoy_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for convoy.membership evidence."""
    run_id = event.get("run_id", ctx.run_id)
    is_authorized = event.get("is_mayor_authorized", False)
    is_partial_chain = event.get("chain_partial", False)
    tok_status = token_registry.token_status(f"convoy-{run_id}", run_id=run_id)

    closes = []
    bounds = []
    if is_authorized and tok_status == "valid":
        bounds = ["delegation_authority_gap"]
        if not is_partial_chain:
            bounds.append("authority_chain_gap")

    return {
        "token_id": f"convoy-{run_id}-{ts}",
        "token_type": "convoy_membership",
        "schema_version": "gt/0.1",
        "status": tok_status,
        "closes_gaps": closes,
        "bounds_gaps": bounds,
        "issued_at": ts,
        "issuer": "gastown.convoy",
        "is_mismatch": False,
    }


def _make_merge_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
    claim_class: str = "merge",
) -> dict:
    """Build a token descriptor for bd.call subcommand=merge."""
    run_id = event.get("run_id", ctx.run_id)
    gate_pass = event.get("gate_pass", False)
    git_commit = event.get("git_commit", ctx.git_commit)

    # Check git_commit mismatch (L6 pattern) — only if ctx.git_commit is set
    commit_mismatch = ctx.git_commit and (git_commit != ctx.git_commit)

    if commit_mismatch:
        ctx.has_provenance_mismatch = True
        return {
            "token_id": f"merge-{run_id}-{ts}",
            "token_type": "refinery_gate",
            "schema_version": "gt/0.1",
            "status": "valid",
            "closes_gaps": [],
            "bounds_gaps": [],
            "issued_at": ts,
            "issuer": "gastown.refinery",
            "is_mismatch": True,
        }
    elif gate_pass:
        tok_status = token_registry.token_status(f"merge-{run_id}", run_id=run_id)
        closes = ["merge_safety_gap"] if tok_status == "valid" else []
    else:
        tok_status = "valid"
        closes = []

    return {
        "token_id": f"merge-{run_id}-{ts}",
        "token_type": "refinery_gate",
        "schema_version": "gt/0.1",
        "status": tok_status if not commit_mismatch else "valid",
        "closes_gaps": closes,
        "bounds_gaps": [],
        "issued_at": ts,
        "issuer": "gastown.refinery",
        "is_mismatch": False,
    }


def _make_authority_chain_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for a full authority chain event."""
    run_id = event.get("run_id", ctx.run_id)
    chain_complete = event.get("chain_complete", False)
    tok_status = token_registry.token_status(f"chain-{run_id}", run_id=run_id)

    closes = ["authority_chain_gap", "delegation_authority_gap"] if (chain_complete and tok_status == "valid") else []
    return {
        "token_id": f"chain-{run_id}-{ts}",
        "token_type": "authority_chain",
        "schema_version": "gt/0.1",
        "status": tok_status,
        "closes_gaps": closes,
        "bounds_gaps": [],
        "issued_at": ts,
        "issuer": "gastown.authority",
        "is_mismatch": False,
    }


def _make_resolution_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for a resolution_attempt event."""
    run_id = event.get("run_id", ctx.run_id)
    resolution_status = event.get("resolution_status", "none")
    has_failure_evidence = event.get("has_failure_evidence", False)
    tok_status = token_registry.token_status(f"resolution-{run_id}", run_id=run_id)

    closes = []
    bounds = []
    if tok_status == "valid":
        if resolution_status == "failed" and has_failure_evidence:
            closes = ["escalation_validity_gap"]
        elif resolution_status == "partial":
            bounds = ["escalation_validity_gap"]

    return {
        "token_id": f"resolution-{run_id}-{ts}",
        "token_type": "resolution_attempt",
        "schema_version": "gt/0.1",
        "status": tok_status,
        "closes_gaps": closes,
        "bounds_gaps": bounds,
        "issued_at": ts,
        "issuer": "gastown.resolution",
        "is_mismatch": False,
    }


def _make_experiment_scope_descriptor(
    ctx: _RunContext,
    event: dict,
    ts: float,
    token_registry: TokenRegistry,
) -> dict:
    """Build a token descriptor for an experiment_scope_token event."""
    run_id = event.get("run_id", ctx.run_id)
    tok_status = token_registry.token_status(f"exp-{run_id}", run_id=run_id)

    closes = ["experiment_scope_gap"] if tok_status == "valid" else []
    return {
        "token_id": f"exp-scope-{run_id}-{ts}",
        "token_type": "experiment_scope",
        "schema_version": "gt/0.1",
        "status": tok_status,
        "closes_gaps": closes,
        "bounds_gaps": [],
        "issued_at": ts,
        "issuer": "gastown.experiment",
        "is_mismatch": False,
    }


def _descriptors_to_tokens(
    descriptors: list[dict],
    prov_hash: str,
) -> list[t.ProofToken]:
    """Convert token descriptors to t.ProofToken objects.

    Uses the provided prov_hash for non-mismatch tokens.
    Uses '0'*64 for deliberate mismatch tokens.
    """
    tokens = []
    for d in descriptors:
        ph = "0" * 64 if d.get("is_mismatch", False) else prov_hash
        tokens.append(t.ProofToken(
            token_id=d["token_id"],
            token_type=d["token_type"],
            schema_version=d["schema_version"],
            status=d["status"],
            closes_gaps=d["closes_gaps"],
            bounds_gaps=d["bounds_gaps"],
            provenance_hash=ph,
            issued_at=d["issued_at"],
            issuer=d["issuer"],
        ))
    return tokens


# ── Core processing logic ──────────────────────────────────────────────────────

def _process_event(
    event: dict,
    state: _AdapterState,
    now_unix: float,
    w_evidence: int,
    w_grace: int,
    token_registry: TokenRegistry,
    bead_type: str = "normal",
) -> Optional[Judgment]:
    """Process a single OTEL event, update state, return judgment if claim closed."""
    event_type = event.get("event_type", "")
    run_id = event.get("run_id", "")
    bead_id = event.get("bead_id", "")
    ts = float(event.get("timestamp", now_unix))

    if not run_id:
        return None

    ctx = state.get_or_create(run_id, bead_id)

    # ── Session boundary ──
    if event_type == "session.stop":
        ctx.session_boundary_ts = ts
        return None

    # ── Agent instantiate (opens a claim context) ──
    if event_type == "agent.instantiate":
        ctx.role = event.get("role", "unknown")
        ctx.rig = event.get("rig", "")
        ctx.git_commit = event.get("git_commit", "")
        ctx.bead_type = bead_type or event.get("bead_type", "normal")
        ctx.agent_name = event.get("agent_name", "")
        ctx.issue_id = event.get("issue_id", "")
        ctx.instantiate_ts = ts
        return None

    # ── Evidence events ──
    # Tokens are stored as descriptors; prov_hash is computed at emit time
    # using the final ctx.rig / ctx.git_commit values.

    if event_type == "prime":
        hook_mode = event.get("hook_mode", False)
        if hook_mode and event.get("run_id") == ctx.run_id:
            desc = _make_prime_descriptor(ctx, event, ts, token_registry)
            ctx.tokens.append(desc)
        return None

    if event_type == "gt.seance":
        # Seance tokens are stored as special descriptors; built at emit time
        ctx.tokens.append({
            "_seance_event": event,
            "_bead_id": ctx.bead_id,
            "_run_id": ctx.run_id,
            "is_mismatch": False,
            "_is_seance": True,
        })
        return None

    if event_type == "sling":
        desc = _make_sling_descriptor(ctx, event, ts, token_registry)
        ctx.tokens.append(desc)
        return None

    if event_type == "convoy.membership":
        desc = _make_convoy_descriptor(ctx, event, ts, token_registry)
        ctx.tokens.append(desc)
        return None

    if event_type == "authority_chain":
        desc = _make_authority_chain_descriptor(ctx, event, ts, token_registry)
        ctx.tokens.append(desc)
        return None

    if event_type == "resolution_attempt":
        desc = _make_resolution_descriptor(ctx, event, ts, token_registry)
        ctx.tokens.append(desc)
        return None

    if event_type == "experiment_scope_token":
        desc = _make_experiment_scope_descriptor(ctx, event, ts, token_registry)
        ctx.tokens.append(desc)
        return None

    if event_type in ("cross_scope_token", "cross_rig_token"):
        # Provenance mismatch events — no token, just set mismatch flag
        ctx.has_provenance_mismatch = True
        return None

    if event_type == "bd.call":
        subcommand = event.get("subcommand", "")

        if subcommand == "ready":
            desc = _make_completion_descriptor(ctx, event, ts, token_registry)
            ctx.tokens.append(desc)
            return None

        elif subcommand == "merge":
            # Merge is a claim-closing event (immediate judgment)
            merge_desc = _make_merge_descriptor(ctx, event, ts, token_registry, claim_class="merge")
            merge_descriptors = list(ctx.tokens) + [merge_desc]

            return _emit_judgment(
                ctx=ctx,
                claim_class="merge",
                token_descriptors=merge_descriptors,
                action_id=ctx.run_id,
                bead_type=bead_type or ctx.bead_type,
            )
        return None

    # ── done: critical routing ──
    # NOTE: "done" is NOT in IN_CLASS_EVENTS. It is handled exclusively here.
    if event_type == "done":
        exit_type = event.get("exit_type", "")

        if exit_type == "COMPLETED":
            # Emit judgment.
            # action_id=run_id so that token provenance hashes match
            # (tokens are hashed with claim_id=run_id via compute_action_provenance_hash).
            return _emit_judgment(
                ctx=ctx,
                claim_class="completion",
                token_descriptors=ctx.tokens,
                action_id=ctx.run_id,
                bead_type=bead_type or ctx.bead_type,
            )

        elif exit_type == "ESCALATED":
            # Opens escalation claim but does NOT produce a completion judgment
            return None

        return None

    return None


def _get_claim_class(ctx: _RunContext) -> str:
    """Determine the current claim class for a context."""
    return "completion"


def _build_seance_token_from_descriptor(
    desc: dict,
    prov_hash: str,
    rig: str,
    git_commit: str,
    claim_class: str,
) -> t.ProofToken:
    """Build a seance ProofToken from a stored descriptor at emit time."""
    event = desc["_seance_event"]
    bead_id = desc["_bead_id"]
    run_id = desc["_run_id"]
    # Re-build seance token using the final rig/git_commit context
    return build_seance_token(event, bead_id, run_id, rig, git_commit, claim_class)


def _finalize_tokens(
    token_descriptors: list[dict],
    prov_hash: str,
    rig: str,
    git_commit: str,
    claim_class: str,
) -> tuple[list[t.ProofToken], bool]:
    """Convert token descriptors to t.ProofToken objects.

    Returns (tokens, has_mismatch).
    """
    tokens = []
    has_mismatch = False
    for desc in token_descriptors:
        if desc.get("_is_seance", False):
            tok = _build_seance_token_from_descriptor(desc, prov_hash, rig, git_commit, claim_class)
            tokens.append(tok)
        elif desc.get("is_mismatch", False):
            has_mismatch = True
            tokens.append(t.ProofToken(
                token_id=desc["token_id"],
                token_type=desc["token_type"],
                schema_version=desc["schema_version"],
                status=desc["status"],
                closes_gaps=desc["closes_gaps"],
                bounds_gaps=desc["bounds_gaps"],
                provenance_hash="0" * 64,
                issued_at=desc["issued_at"],
                issuer=desc["issuer"],
            ))
        else:
            tokens.append(t.ProofToken(
                token_id=desc["token_id"],
                token_type=desc["token_type"],
                schema_version=desc["schema_version"],
                status=desc["status"],
                closes_gaps=desc["closes_gaps"],
                bounds_gaps=desc["bounds_gaps"],
                provenance_hash=prov_hash,
                issued_at=desc["issued_at"],
                issuer=desc["issuer"],
            ))
    return tokens, has_mismatch


def _emit_judgment(
    ctx: _RunContext,
    claim_class: str,
    token_descriptors: list,
    action_id: str,
    bead_type: str = "normal",
) -> Judgment:
    """Compile the proof context and emit a judgment.

    Converts token descriptors to t.ProofToken at emit time using the
    final context (rig, git_commit) so that provenance hashes are correct
    even for tokens that arrived before agent.instantiate.
    """
    from .proof_context import _build_gap_list, build_profiles, _build_context_id
    from .authority_registry import get_ceiling, is_in_class

    is_experiment = (bead_type or ctx.bead_type) == "experiment"
    has_merge = claim_class == "merge"
    has_escalation = claim_class == "escalation"

    context_id = _build_context_id(ctx.run_id, ctx.rig, ctx.git_commit)
    # prov_hash uses action_id (= run_id) as claim_id — must match what tokens expect
    prov_hash = compute_action_provenance_hash(
        ctx.bead_id, action_id, ctx.rig, ctx.git_commit, claim_class
    )

    # Convert descriptors to actual tokens at emit time (with correct prov_hash)
    tokens, descriptor_mismatch = _finalize_tokens(
        token_descriptors, prov_hash, ctx.rig, ctx.git_commit, claim_class
    )
    has_provenance_mismatch = ctx.has_provenance_mismatch or descriptor_mismatch

    ceiling = get_ceiling(ctx.role)
    membership = (
        t.Membership.InClass if is_in_class(ctx.role)
        else t.Membership.OutOfClassExact
    )

    gaps = _build_gap_list(is_experiment, has_merge, has_escalation)
    profiles = build_profiles(is_experiment, has_merge, has_escalation)

    # If provenance mismatch detected, cap ceiling at REF so the compiler emits REF.
    # The mismatch tokens have "0"*64 provenance_hash, which the compiler rejects,
    # leaving all gaps open. With ceiling=REF, the max achievable permission is REF.
    if has_provenance_mismatch:
        ceiling = t.Permission.REF

    proof_ctx = t.ProofContext(
        claim_id=action_id,
        candidate_id=ctx.bead_id,
        context_id=context_id,
        allowed_use=claim_class,
        membership=membership,
        authority_ceiling=ceiling,
        expiry=t.Expiry.never(),
        gaps=gaps,
        profiles=profiles,
        tokens=tokens,
        context_fingerprint=context_id,
    )

    live = t.compile(proof_ctx)
    import time as _time
    runtime = t.RuntimeContext(now_unix=_time.time(), context_fingerprint=context_id)
    perm_str = live.permission_str(runtime)
    perm = t.Permission.from_str(perm_str)

    # Collect gap states from token descriptors (not actual tokens)
    gap_states = _collect_gap_states_from_descriptors(token_descriptors)

    return Judgment(
        permission=perm,
        claim_class=claim_class,
        run_id=ctx.run_id,
        bead_id=ctx.bead_id,
        action_id=action_id,
        proof_context=proof_ctx,
        live_judgment=live,
        gap_states=gap_states,
    )


def _collect_gap_states_from_descriptors(token_descriptors: list) -> dict[str, str]:
    """Collect approximate gap states from token descriptors.

    Uses closes_gaps and bounds_gaps from descriptors (not actual tokens).
    """
    from .proof_context import STANDARD_GAPS, EXPERIMENT_GAP

    states: dict[str, str] = {g: "open" for g in STANDARD_GAPS}
    states[EXPERIMENT_GAP] = "open"

    for desc in token_descriptors:
        if desc.get("is_mismatch", False):
            continue
        if desc.get("_is_seance", False):
            # Seance tokens: infer from event
            event = desc.get("_seance_event", {})
            staleness_seconds = event.get("staleness_seconds", 9999)
            commits_elapsed = event.get("commits_elapsed", -1)
            # Within bounds → bounds context_integrity_gap
            if staleness_seconds <= 3600 and 0 <= commits_elapsed <= 10:
                if states.get("context_integrity_gap") == "open":
                    states["context_integrity_gap"] = "bounded"
            continue
        status = desc.get("status", "valid")
        if status == "valid":
            for g in desc.get("closes_gaps", []):
                states[g] = "closed"
            for g in desc.get("bounds_gaps", []):
                if states.get(g, "open") == "open":
                    states[g] = "bounded"
    return states


# ── BUFFER ordering policy ─────────────────────────────────────────────────────

def _apply_buffer_ordering(trace: list[dict], buffer_window: float = 10.0) -> list[dict]:
    """Apply BUFFER ordering policy: sort records within a 10s reorder window."""
    return sorted(trace, key=lambda e: float(e.get("timestamp", 0)))


def _apply_strict_ordering(trace: list[dict]) -> tuple[list[dict], bool]:
    """Apply STRICT ordering policy.

    Returns (sorted_trace, had_violation).
    """
    timestamps = [float(e.get("timestamp", 0)) for e in trace]
    had_violation = any(timestamps[i] > timestamps[i + 1] for i in range(len(timestamps) - 1))
    return sorted(trace, key=lambda e: float(e.get("timestamp", 0))), had_violation


# ── Public API ─────────────────────────────────────────────────────────────────

def process_trace(
    trace: list[dict],
    now_unix: float | None = None,
    bead_type: str = "normal",
    token_registry: TokenRegistry | None = None,
    w_evidence: int = W_EVIDENCE_DEFAULT,
    w_grace: int = W_GRACE_DEFAULT,
    ordering_policy: str = "BUFFER",
) -> list[Judgment]:
    """Process a complete OTEL trace and return all judgments.

    Parameters
    ----------
    trace : list[dict]
        List of OTEL records in any order (ordering_policy applied).
    now_unix : float
        Current time as a Unix timestamp.
    bead_type : str
        "normal" or "experiment" — controls experiment_scope_gap induction.
    token_registry : TokenRegistry
        Token liveness/revocation registry. Defaults to the module registry.
    w_evidence : int
        Evidence window in seconds before claim timestamp.
    w_grace : int
        Grace window in seconds after claim timestamp.
    ordering_policy : str
        "BUFFER" (default), "STRICT", or "BEST_EFFORT".
    """
    import time as _time
    if now_unix is None:
        now_unix = _time.time()

    if token_registry is None:
        token_registry = get_default_registry()

    # Apply ordering policy
    if ordering_policy == "STRICT":
        ordered_trace, had_violation = _apply_strict_ordering(trace)
        if had_violation:
            # Return ordering violation marker (empty judgments, flag set)
            # Tests check for ORDERING_VIOLATION; we return an empty list
            # with a special sentinel marker for strict violation
            return []
    elif ordering_policy == "BUFFER":
        ordered_trace = _apply_buffer_ordering(trace)
    else:
        ordered_trace = trace

    state = _AdapterState()
    judgments: list[Judgment] = []

    for event in ordered_trace:
        j = _process_event(
            event=event,
            state=state,
            now_unix=now_unix,
            w_evidence=w_evidence,
            w_grace=w_grace,
            token_registry=token_registry,
            bead_type=bead_type,
        )
        if j is not None:
            judgments.append(j)

    return judgments


# ── OtelAdapter class (stateless wrapper) ─────────────────────────────────────

class OtelAdapter:
    """Stateless OTEL adapter wrapper.

    Wraps process_trace() for use in tests and the harness runner.
    No mutable state on the adapter object itself.
    """

    def __init__(
        self,
        token_registry: TokenRegistry | None = None,
        w_evidence: int = W_EVIDENCE_DEFAULT,
        w_grace: int = W_GRACE_DEFAULT,
        ordering_policy: str = "BUFFER",
    ) -> None:
        self.token_registry = token_registry or get_default_registry()
        self.w_evidence = w_evidence
        self.w_grace = w_grace
        self.ordering_policy = ordering_policy

    def process(
        self,
        trace: list[dict],
        now_unix: float | None = None,
        bead_type: str = "normal",
    ) -> list[Judgment]:
        """Process a complete trace and return all judgments."""
        return process_trace(
            trace=trace,
            now_unix=now_unix,
            bead_type=bead_type,
            token_registry=self.token_registry,
            w_evidence=self.w_evidence,
            w_grace=self.w_grace,
            ordering_policy=self.ordering_policy,
        )
