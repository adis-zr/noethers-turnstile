"""
Turnstile — admissibility compiler.

Judgment form: Γ ⊢ z : p until ε

The permission chain (total order, OOC=bottom, AAA=top):
    OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA

Usage::

    from turnstile import (
        Permission, Membership, Expiry, Scope,
        GapRecord, GapRequirement, Profile,
        ProofToken, ProofContext,
        RuntimeContext,
        compile, compose, compute_provenance_hash,
        TurnstileError, ExpiredError, CompositionError, ProvenanceError,
    )
    import time

    ctx = ProofContext(
        claim_id="my-claim",
        candidate_id="z-001",
        context_id="ctx-001",
        allowed_use="diagnostics",
        membership=Membership.InClass,
        authority_ceiling=Permission.AAA,
        expiry=Expiry.never(),
    )

    live = compile(ctx)
    rt = RuntimeContext(now_unix=time.time(), context_fingerprint="ctx-001")
    print(live.permission_str(rt))  # "OOC" (no profiles registered)
"""

import logging as _logging

from ._turnstile import (  # noqa: F401
    # Exceptions
    TurnstileError,
    ExpiredError,
    CompositionError,
    ProvenanceError,

    # Types
    NegativeControlStatus,
    DerivationStep,
    Derivation,
    Permission,
    Scope,
    GapRecord,
    GapRequirement,
    Profile,
    ProofToken,
    Expiry,
    Membership,
    ProofContext,
    Judgment,
    RuntimeContext,
    LiveJudgment,

    # Functions
    compile,
    compile_static,
    compose,
    compute_provenance_hash,
)

__all__ = [
    "TurnstileError",
    "ExpiredError",
    "CompositionError",
    "ProvenanceError",
    "NegativeControlStatus",
    "DerivationStep",
    "Derivation",
    "Permission",
    "Scope",
    "GapRecord",
    "GapRequirement",
    "Profile",
    "ProofToken",
    "Expiry",
    "Membership",
    "ProofContext",
    "Judgment",
    "RuntimeContext",
    "LiveJudgment",
    "compile",
    "compile_static",
    "compose",
    "compute_provenance_hash",
]

# Structured logging helpers.
# Callers install a handler on "turnstile"; we emit structured log records so
# that JSON formatters (e.g. python-json-logger) pick up the extra fields.

_logger = _logging.getLogger("turnstile")


def _log_compile(judgment: "Judgment", *, level: int = _logging.DEBUG) -> None:
    """Emit a structured log record for a compile result."""
    deriv = judgment.derivation
    _logger.log(
        level,
        "turnstile.compile",
        extra={
            "permission": judgment.permission_str,
            "provenance_hash": deriv.provenance_hash,
            "derivation_steps": [
                {
                    "phase": s.phase,
                    "permission_after": str(s.permission_after),
                    "note": s.note,
                    "token_ids": s.token_ids,
                }
                for s in deriv.steps
            ],
        },
    )


def _log_live_permission(
    live: "LiveJudgment",
    runtime: "RuntimeContext",
    *,
    level: int = _logging.DEBUG,
) -> None:
    """Emit a structured log record for a live permission read."""
    perm = live.permission_str(runtime)
    _logger.log(
        level,
        "turnstile.live_permission",
        extra={
            "permission": perm,
            "strict_mode": runtime.strict_mode,
        },
    )
