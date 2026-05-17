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

from ._turnstile import (  # noqa: F401
    # Exceptions
    TurnstileError,
    ExpiredError,
    CompositionError,
    ProvenanceError,

    # Types
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
