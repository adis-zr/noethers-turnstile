"""Type stubs for the Turnstile admissibility compiler."""

from __future__ import annotations

from typing import List, Optional

# ── Exceptions ─────────────────────────────────────────────────────────────────

class TurnstileError(Exception): ...
class ExpiredError(TurnstileError): ...
class CompositionError(TurnstileError): ...
class ProvenanceError(TurnstileError): ...

# ── Permission ─────────────────────────────────────────────────────────────────

class Permission:
    """Total-ordered permission level.  OOC is bottom, AAA is top.  Meet = min."""

    OOC: "Permission"
    EXP: "Permission"
    REF: "Permission"
    UNS: "Permission"
    ETA: "Permission"
    ESC: "Permission"
    ROL: "Permission"
    DIA: "Permission"
    REV: "Permission"
    AEX: "Permission"
    ALR: "Permission"
    AAA: "Permission"

    def meet(self, other: "Permission") -> "Permission": ...
    def as_str(self) -> str: ...
    @staticmethod
    def from_str(s: str) -> "Permission": ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __lt__(self, other: "Permission") -> bool: ...
    def __le__(self, other: "Permission") -> bool: ...
    def __gt__(self, other: "Permission") -> bool: ...
    def __ge__(self, other: "Permission") -> bool: ...
    def __hash__(self) -> int: ...

# ── Membership ─────────────────────────────────────────────────────────────────

class Membership:
    InClass: "Membership"
    OutOfClassExact: "Membership"
    OutOfClassAuthorizedDeterministicWrite: "Membership"
    OutOfClassNoConsequentialUse: "Membership"

    @staticmethod
    def other(reason: str) -> "Membership": ...
    def is_in_class(self) -> bool: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

# ── Expiry ─────────────────────────────────────────────────────────────────────

class Expiry:
    @staticmethod
    def never() -> "Expiry": ...
    @staticmethod
    def at(deadline_unix: float) -> "Expiry": ...
    def fired(self, now_unix: float) -> bool: ...
    def __repr__(self) -> str: ...

# ── Scope ──────────────────────────────────────────────────────────────────────

class Scope:
    def __init__(
        self,
        allowed_candidates: Optional[List[str]] = None,
        allowed_paths: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
        allowed_resources: Optional[List[str]] = None,
    ) -> None: ...
    @property
    def allowed_candidates(self) -> List[str]: ...
    @property
    def allowed_paths(self) -> List[str]: ...
    @property
    def allowed_tools(self) -> List[str]: ...
    @property
    def allowed_resources(self) -> List[str]: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

# ── GapRecord ──────────────────────────────────────────────────────────────────

class GapRecord:
    """A single gap in the proof context."""

    def __init__(
        self,
        gap_id: str,
        gap_type: str,
        status: str = "open",
        bound_value: Optional[float] = None,
    ) -> None: ...
    @property
    def gap_id(self) -> str: ...
    @property
    def gap_type(self) -> str: ...
    @property
    def status(self) -> str: ...  # "open" | "bounded" | "closed"
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

# ── GapRequirement ─────────────────────────────────────────────────────────────

class GapRequirement:
    def __init__(self, gap_id: str, minimum_status: str) -> None: ...
    @property
    def gap_id(self) -> str: ...
    @property
    def minimum_status(self) -> str: ...  # "bounded" | "closed"
    def __repr__(self) -> str: ...

# ── Profile ────────────────────────────────────────────────────────────────────

class Profile:
    def __init__(
        self, permission: Permission, required_gaps: List[GapRequirement]
    ) -> None: ...
    @property
    def permission(self) -> Permission: ...
    def __repr__(self) -> str: ...

# ── ProofToken ─────────────────────────────────────────────────────────────────

class ProofToken:
    def __init__(
        self,
        token_id: str,
        token_type: str,
        schema_version: str,
        status: str,
        closes_gaps: List[str],
        bounds_gaps: List[str],
        provenance_hash: str,
        issued_at: float,
        issuer: str,
        expires_at: Optional[float] = None,
    ) -> None: ...
    @property
    def token_id(self) -> str: ...
    @property
    def token_type(self) -> str: ...
    @property
    def schema_version(self) -> str: ...
    @property
    def status(self) -> str: ...
    @property
    def closes_gaps(self) -> List[str]: ...
    @property
    def bounds_gaps(self) -> List[str]: ...
    @property
    def provenance_hash(self) -> str: ...
    @property
    def issuer(self) -> str: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

# ── ProofContext ───────────────────────────────────────────────────────────────

class ProofContext:
    def __init__(
        self,
        claim_id: str,
        candidate_id: str,
        context_id: str,
        allowed_use: str,
        membership: Membership,
        authority_ceiling: Permission,
        expiry: Expiry,
        gaps: Optional[List[GapRecord]] = None,
        profiles: Optional[List[Profile]] = None,
        tokens: Optional[List[ProofToken]] = None,
        disallowed_uses: Optional[List[str]] = None,
        scope: Optional[Scope] = None,
        context_fingerprint: Optional[str] = None,
    ) -> None: ...
    @property
    def claim_id(self) -> str: ...
    @property
    def candidate_id(self) -> str: ...
    @property
    def context_id(self) -> str: ...
    @property
    def allowed_use(self) -> str: ...
    @property
    def authority_ceiling(self) -> Permission: ...
    def provenance_hash(self) -> str: ...
    def __repr__(self) -> str: ...

# ── Judgment ───────────────────────────────────────────────────────────────────

class Judgment:
    @property
    def permission(self) -> Permission: ...
    @property
    def permission_str(self) -> str: ...
    @property
    def expiry(self) -> Expiry: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

# ── RuntimeContext ─────────────────────────────────────────────────────────────

class RuntimeContext:
    def __init__(self, now_unix: float, context_fingerprint: str) -> None: ...
    def __repr__(self) -> str: ...

# ── LiveJudgment ──────────────────────────────────────────────────────────────

class LiveJudgment:
    """A live judgment handle.  Call .permission(runtime) to evaluate expiry."""

    def permission(self, runtime: RuntimeContext) -> Permission:
        """Raises ExpiredError if the judgment has expired at runtime.now."""
        ...

    def permission_str(self, runtime: RuntimeContext) -> str:
        """Returns permission name as string.  Returns 'EXP' if expired (no exception)."""
        ...

    def __repr__(self) -> str: ...

# ── Functions ──────────────────────────────────────────────────────────────────

def compile(ctx: ProofContext) -> LiveJudgment:
    """Compile a ProofContext into a LiveJudgment.

    Raises TurnstileError on malformed context.
    """
    ...

def compile_static(ctx: ProofContext) -> Judgment:
    """Compile a ProofContext into a static Judgment snapshot."""
    ...

def compose(g1: ProofContext, g2: ProofContext) -> ProofContext:
    """Compose two ProofContexts (lax monoidal composition).

    Raises CompositionError on use conflict or token conflict.
    """
    ...

def compute_provenance_hash(
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
) -> str:
    """Compute the SHA-256 provenance hash for a (claim, candidate, context, use) tuple."""
    ...
