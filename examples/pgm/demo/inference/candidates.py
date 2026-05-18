"""Candidate types: per-site inference candidates and whole-plan certified candidates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from .certificates import Certificate
from .memory import MemoryState


@dataclass(frozen=True)
class ResidualBracket:
    """
    Per-site residual bracket: certified [lower, upper] envelope around the exact message.

    Invariant:  lower[y] <= exact_message[y] <= upper[y]  for all output assignments y.

    executed[y] is the message the plan actually passes upstream (geometric mean of
    lower and upper for "bracketed" status; identical to exact for "exact" status).

    log_lower_ratio[y] = log(lower[y] / executed[y])  — lower bound on log-residual s(y)
    log_upper_ratio[y] = log(upper[y] / executed[y])  — upper bound on log-residual s(y)

    max_delta = max_y( log(upper[y]) - log(lower[y]) )
              = max_y( log_upper_ratio[y] - log_lower_ratio[y] )

    The certificate KL bound equals max_delta (for alpha=0.5 geometric-mean execution).

    status:
      "exact"            — lower == executed == upper; zero residual at this site
      "bracketed"        — Hölder/reverse-Hölder bracket from actual model-factor tables
      "analytic_fallback" — strict positivity failed or no compile-time tables available;
                           bracket falls back to analytic log(n_groups) bound
      "support_failure"  — a model factor has a zero entry; KL may be infinite
    """

    scope: tuple[int, ...]
    executed: tuple[float, ...]
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    log_lower_ratio: tuple[float, ...]
    log_upper_ratio: tuple[float, ...]
    max_delta: float
    status: Literal["exact", "bracketed", "analytic_fallback", "support_failure"]
    proof: "ProofToken"


@dataclass(frozen=True)
class ProofToken:
    """
    Human-readable justification for why a candidate's certificate is sound.

    Intentionally opaque to the compiler — never compared by the DP.
    Included in audit logs for reproducibility.
    """

    description: str


@dataclass
class Candidate:
    """
    A local inference candidate at a single site.

    The compiler never inspects `implementation` — it only compares
    (memory, certificate) across candidates.

    residual_bracket: optional per-site bracket [lower, upper] around the exact message.
    Set by HolderBracketKernelFamily; None for exact and analytic-Hilbert candidates.
    """

    implementation: Any
    memory: MemoryState
    certificate: Certificate
    audit: ProofToken
    residual_bracket: Optional[ResidualBracket] = None


@dataclass(frozen=True)
class CertifiedPlanCandidate:
    """
    A whole-plan certified candidate produced by Phase 2 (certificate selection).

    Pairs an execution kernel with a certificate geometry. The compiler
    enumerates all registered (execution, certificate) pairs and selects
    the argmin certified_kl among those that fit peak_memory <= budget.

    Fields
    ------
    execution_kernel    "exact" | "hilbert"
    certificate_geometry "exact" | "hilbert" | "fkkl" | "infinite"
    exec_memory         execution plan peak memory (bytes)
    cert_memory         certificate oracle memory beyond exec_memory (bytes)
    peak_memory         exec_memory + cert_memory (total budget requirement)
    certificate         the certificate object carrying kl_bound()
    certified_kl        certificate.kl_bound() — the certified upper bound
    audit               proof token explaining why this geometry is sound
    """

    execution_kernel: str
    certificate_geometry: str
    exec_memory: int
    cert_memory: int
    peak_memory: int
    certificate: Certificate
    certified_kl: float
    audit: ProofToken
