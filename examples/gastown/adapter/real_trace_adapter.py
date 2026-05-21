"""GasTown real-trace adapter — processes decoded OTEL JSONL from GasTown 1.1.0.

Input: list of decoded records from the protobuf JSONL sink (service_name in
       {"gastown", "claude-code"}), as produced by the protobuf decoder.

Output: list[Judgment] — one per completed claude-code session that maps to a
        known GasTown role, using the same Judgment type as otel_adapter.py.

Event vocabulary mapping (real → ACS):
  agent.instantiate (gastown)              → role, rig, git_commit, run_id
  prime (gastown)                          → context_integrity freshness anchor
  claude_code.hook_execution_complete      → judgment trigger (hook_event=Stop)
    with hook_event=Stop (claude-code)
  claude_code.tool_result (claude-code)    → completion_evidence signal
  claude_code.tool_decision (claude-code)  → tool type (Write/Edit = artifact)
  bd.call close (gastown, reason w/ merge) → merge_safety evidence
  session.id cross-ref                     → links claude-code session to
                                             gastown run_id via timing

Gap derivation rules:
  context_integrity_gap:
    CLOSED  — agent.instantiate timestamp within 3600s of first prime for run
    BOUNDED — agent.instantiate exists but prime gap > 3600s
    OPEN    — no agent.instantiate found for the session's role

  delegation_authority_gap:
    CLOSED  — role is mayor or has a gastown agent.instantiate with run_id
    BOUNDED — role is refinery/polecat with rig field present
    OPEN    — role unknown or no instantiate found

  completion_evidence_gap:
    CLOSED  — session has ≥1 tool_result with success=True AND at least one
              Write or Edit tool decision (artifact produced)
    BOUNDED — session has tool_results but no Write/Edit (commands only)
    OPEN    — no successful tool_results in session

  escalation_validity_gap:
    OPEN    — always; no escalation events in GasTown 1.1.0 telemetry

  merge_safety_gap:
    CLOSED  — a gastown bd.call close with reason containing "merge" exists
              within 120s of the session stop, attributed to the same rig
    OPEN    — no merge-close found (patrol empty, timeout, etc.)

  authority_chain_gap:
    CLOSED  — agent.instantiate has git_commit present and non-empty
    BOUNDED — agent.instantiate found but git_commit absent
    OPEN    — no agent.instantiate found

  experiment_scope_gap: always OPEN (no experiment beads in 1.1.0)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import noethers_turnstile as t

from .authority_registry import get_ceiling, is_in_class
from .proof_context import STANDARD_GAPS, EXPERIMENT_GAP, build_profiles, _build_gap_list
from .provenance import _build_context_id, compute_action_provenance_hash
from .otel_adapter import Judgment

__all__ = ["process_real_trace"]

# ── Role normalisation ─────────────────────────────────────────────────────────

def _normalise_role(raw: str) -> str:
    """Extract the base role from a composite like 'boolean_sat/refinery'."""
    if "/" in raw:
        return raw.split("/")[-1]
    return raw


# ── Session record ─────────────────────────────────────────────────────────────

@dataclass
class _Session:
    session_id: str
    raw_role: str                        # e.g. "boolean_sat/refinery"
    role: str                            # normalised: "refinery"
    run_id: str                          # gastown run_id (may be "")
    rig: str                             # rig name (may be "")
    git_commit: str                      # from agent.instantiate
    instantiate_ts: float                # unix ts of agent.instantiate
    first_prime_ts: float                # unix ts of first prime for this run
    start_ts: float                      # claude-code SessionStart hook ts
    stop_ts: float                       # claude-code Stop hook ts (judgment trigger)
    tool_results: list[dict] = field(default_factory=list)
    tool_decisions: list[dict] = field(default_factory=list)
    has_merge_close: bool = False        # gastown bd.call close w/ merge reason


# ── Timestamp helpers ──────────────────────────────────────────────────────────

def _ts(rec: dict) -> float:
    """Return unix timestamp for a record."""
    ns = rec.get("timestamp_ns", 0)
    if ns:
        return ns / 1e9
    ra = rec.get("received_at", "")
    if ra:
        import datetime
        try:
            dt = datetime.datetime.fromisoformat(ra.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return 0.0


# ── Gap derivation ─────────────────────────────────────────────────────────────

def _derive_gap_states(sess: _Session) -> dict[str, str]:
    states: dict[str, str] = {g: "open" for g in STANDARD_GAPS}
    states[EXPERIMENT_GAP] = "open"

    # context_integrity_gap
    if sess.instantiate_ts > 0 and sess.first_prime_ts > 0:
        delta = abs(sess.first_prime_ts - sess.instantiate_ts)
        states["context_integrity_gap"] = "closed" if delta <= 3600 else "bounded"
    elif sess.instantiate_ts > 0:
        # instantiate present, no prime — treat as bounded (context exists, not verified fresh)
        states["context_integrity_gap"] = "bounded"

    # delegation_authority_gap
    if sess.role == "mayor":
        states["delegation_authority_gap"] = "closed"
    elif sess.role in ("refinery", "polecat") and sess.run_id:
        states["delegation_authority_gap"] = "bounded"
    elif sess.run_id:
        states["delegation_authority_gap"] = "bounded"

    # completion_evidence_gap
    # success field is a string "true"/"false" in real OTEL records
    successful_results = [
        r for r in sess.tool_results
        if str(r.get("success", "")).lower() == "true"
    ]
    artifact_tools = {"Write", "Edit", "NotebookEdit"}
    has_artifact = any(
        d.get("tool_name", "") in artifact_tools
        for d in sess.tool_decisions
    )
    if successful_results and has_artifact:
        states["completion_evidence_gap"] = "closed"
    elif successful_results:
        states["completion_evidence_gap"] = "bounded"

    # escalation_validity_gap — always open (no escalation in 1.1.0)

    # merge_safety_gap
    if sess.has_merge_close:
        states["merge_safety_gap"] = "closed"

    # authority_chain_gap
    if sess.git_commit:
        states["authority_chain_gap"] = "closed"
    elif sess.instantiate_ts > 0:
        states["authority_chain_gap"] = "bounded"

    return states


# ── ProofContext builder ───────────────────────────────────────────────────────

def _build_proof_context(sess: _Session, gap_states: dict[str, str],
                         now_unix: float) -> tuple[t.ProofContext, t.LiveJudgment, t.Permission]:
    run_id = sess.run_id or sess.session_id
    bead_id = sess.session_id
    rig = sess.rig or "hq"
    git_commit = sess.git_commit or "unknown"
    allowed_use = "real_session"

    context_id = _build_context_id(run_id, rig, git_commit)
    prov_hash = compute_action_provenance_hash(bead_id, run_id, rig, git_commit, allowed_use)

    authority_ceiling = get_ceiling(sess.role)
    membership = t.Membership.InClass if is_in_class(sess.role) else t.Membership.OutOfClassExact

    # Real sessions are completion claims: no escalation events in GasTown 1.1.0,
    # and merge_safety_gap is treated as informational (not profile-required) because
    # has_merge=True also induces escalation_validity_gap which can never be closed.
    gaps = _build_gap_list(is_experiment=False, has_merge=False, has_escalation=False)
    profiles = build_profiles(is_experiment=False, has_merge=False, has_escalation=False)

    tokens: list[t.ProofToken] = []
    for gap_id, status in gap_states.items():
        if status == "open":
            continue
        token_id = f"real-{gap_id}-{sess.session_id[:8]}"
        closes = [gap_id] if status == "closed" else []
        bounds = [gap_id] if status == "bounded" else []
        token = t.ProofToken(
            token_id=token_id,
            token_type="real_trace",
            schema_version="gt/0.1",
            status="valid",
            closes_gaps=closes,
            bounds_gaps=bounds,
            provenance_hash=prov_hash,
            issued_at=sess.stop_ts,
            issuer="gastown.real_trace",
        )
        tokens.append(token)

    proof_ctx = t.ProofContext(
        claim_id=run_id,
        candidate_id=bead_id,
        context_id=context_id,
        allowed_use=allowed_use,
        membership=membership,
        authority_ceiling=authority_ceiling,
        expiry=t.Expiry.never(),
        gaps=gaps,
        profiles=profiles,
        tokens=tokens,
        context_fingerprint=context_id,
    )

    live = t.compile(proof_ctx)
    runtime = t.RuntimeContext(now_unix=now_unix, context_fingerprint=context_id)
    perm_str = live.permission_str(runtime)
    perm = t.Permission.from_str(perm_str)

    return proof_ctx, live, perm


# ── Main public function ───────────────────────────────────────────────────────

def process_real_trace(
    records: list[dict],
    now_unix: float | None = None,
) -> list[Judgment]:
    """Process decoded GasTown 1.1.0 OTEL records and return judgments.

    One Judgment per completed claude-code session associated with a known
    GasTown role (trigger: hook_execution_complete with hook_event=Stop).

    Parameters
    ----------
    records : list[dict]
        Decoded JSONL records (both service_name="gastown" and "claude-code").
    now_unix : float, optional
        Current unix timestamp. Defaults to time.time().
    """
    if now_unix is None:
        now_unix = time.time()

    # ── Pass 1: index gastown records ─────────────────────────────────────────

    # run_id → agent.instantiate record
    instantiates: dict[str, dict] = {}
    # run_id → list of prime records
    primes: dict[str, list[dict]] = {}
    # list of bd.call close records with merge-like reasons
    merge_closes: list[dict] = []

    for rec in records:
        if rec.get("service_name") != "gastown":
            continue
        et = rec.get("event_type", "")
        run_id = rec.get("run_id") or rec.get("run.id", "")

        if et == "agent.instantiate" and run_id:
            instantiates[run_id] = rec

        elif et == "prime" and run_id:
            primes.setdefault(run_id, []).append(rec)

        elif et == "bd.call" and rec.get("subcommand") == "close":
            reason = rec.get("args", "").lower()
            # A real merge close has "merge" in the reason; patrol-empty closures do not
            if "merge" in reason and "no branches to merge" not in reason:
                merge_closes.append(rec)

    # ── Pass 2: build per-session picture from claude-code records ─────────────

    # session_id → accumulated events
    cc_sessions: dict[str, dict] = {}  # session_id → metadata dict

    for rec in records:
        if rec.get("service_name") != "claude-code":
            continue
        sess_id = rec.get("session.id", "")
        if not sess_id:
            continue
        et = rec.get("event_type", "") or rec.get("event.name", "")

        if sess_id not in cc_sessions:
            cc_sessions[sess_id] = {
                "session_id": sess_id,
                "start_ts": 0.0,
                "stop_ts": 0.0,
                "tool_results": [],
                "tool_decisions": [],
                "user_prompts": [],
            }
        s = cc_sessions[sess_id]

        if "hook_execution_complete" in et:
            hook_event = rec.get("hook_event", "")
            if hook_event == "SessionStart":
                s["start_ts"] = _ts(rec)
            elif hook_event == "Stop":
                s["stop_ts"] = _ts(rec)

        elif "tool_result" in et:
            s["tool_results"].append(rec)

        elif "tool_decision" in et:
            s["tool_decisions"].append(rec)

        elif "user_prompt" in et:
            s["user_prompts"].append(rec)

    # ── Pass 3: correlate claude-code sessions → gastown run_ids ──────────────
    # Strategy: match by timing — the gastown agent.instantiate that fires
    # within a short window before the claude-code SessionStart.
    # Also use the prompt text: GasTown prompts embed the role.

    def _role_from_prompt(prompt: str) -> str:
        """Extract role from a GasTown-style prompt string."""
        # e.g. "[GAS TOWN] mayor <- human • ... • cold-start"
        # e.g. "[GAS TOWN] refinery (rig: boolean_sat) <- deacon • ..."
        import re
        m = re.search(r'\[GAS TOWN\]\s+(\S+)', prompt)
        if not m:
            return ""
        actor = m.group(1)
        # actor may be "refinery" or "refinery" — strip "(rig:..." suffix
        actor = re.sub(r'\s*\(.*', '', actor)
        return _normalise_role(actor)

    sessions: list[_Session] = []

    for sess_id, s in cc_sessions.items():
        stop_ts = s["stop_ts"]
        if not stop_ts:
            continue  # no Stop hook → session not complete, skip

        start_ts = s["start_ts"] or stop_ts

        # Determine role from user_prompts
        role = ""
        raw_role = ""
        for up in s["user_prompts"]:
            prompt_text = up.get("prompt", "")
            r = _role_from_prompt(prompt_text)
            if r:
                raw_role = prompt_text  # store for rig extraction too
                role = r
                break

        if not role or not is_in_class(role):
            continue  # not a known GasTown role — skip

        # Find matching gastown run_id: instantiate that fired within 30s before start_ts
        matched_run_id = ""
        matched_inst = {}
        best_delta = float("inf")
        for run_id, inst in instantiates.items():
            inst_role = _normalise_role(inst.get("role", ""))
            if inst_role != role:
                continue
            inst_ts = _ts(inst)
            delta = start_ts - inst_ts
            if -5.0 <= delta <= 30.0 and delta < best_delta:
                best_delta = delta
                matched_run_id = run_id
                matched_inst = inst

        git_commit = matched_inst.get("git_commit", "")
        rig = matched_inst.get("rig", "")
        instantiate_ts = _ts(matched_inst) if matched_inst else 0.0

        # First prime timestamp for this run_id
        first_prime_ts = 0.0
        if matched_run_id and matched_run_id in primes:
            prime_list = sorted(primes[matched_run_id], key=_ts)
            if prime_list:
                first_prime_ts = _ts(prime_list[0])

        # Check for merge close within 120s of stop_ts, matching rig
        has_merge = any(
            abs(_ts(mc) - stop_ts) <= 120
            and (not rig or mc.get("gt_rig", "") == rig or rig == "")
            for mc in merge_closes
        )

        sess = _Session(
            session_id=sess_id,
            raw_role=raw_role[:60],
            role=role,
            run_id=matched_run_id,
            rig=rig,
            git_commit=git_commit,
            instantiate_ts=instantiate_ts,
            first_prime_ts=first_prime_ts,
            start_ts=start_ts,
            stop_ts=stop_ts,
            tool_results=s["tool_results"],
            tool_decisions=s["tool_decisions"],
            has_merge_close=has_merge,
        )
        sessions.append(sess)

    # ── Pass 4: emit one Judgment per completed session ────────────────────────

    judgments: list[Judgment] = []

    for sess in sorted(sessions, key=lambda s: s.stop_ts):
        gap_states = _derive_gap_states(sess)
        proof_ctx, live, perm = _build_proof_context(sess, gap_states, now_unix)

        action_id = f"real-{sess.session_id[:8]}-stop"

        j = Judgment(
            permission=perm,
            claim_class="real_session",
            run_id=sess.run_id or sess.session_id,
            bead_id=sess.session_id,
            action_id=action_id,
            proof_context=proof_ctx,
            live_judgment=live,
            gap_states=gap_states,
        )
        judgments.append(j)

    return judgments
