"""
Certificate algebra for certified inference.

A Certificate is a proof-carrying bound on KL(P||Q) for some approximate plan.
The three concrete types form a closed algebra under composition:

  - ExactCertificate:           KL = 0
  - HilbertIntervalCertificate: KL <= hi - lo  (oscillation of log-residual)
  - InfiniteCertificate:        KL = inf  (support failure or unrepresentable)

Composition rule (self.compose(other)):

  self \\ other    | Exact        | Hilbert(lo2,hi2)          | Infinite
  Exact            | Exact        | Hilbert(lo2,hi2)          | Infinite
  Hilbert(lo1,hi1) | Hilbert(lo1) | Hilbert(lo1+lo2,hi1+hi2)  | Infinite
  Infinite         | Infinite     | Infinite                  | Infinite

Soundness: log-residuals are additive over independent sites because the global
residual s = sum_i s_i factorizes as a product of per-site residuals, and
KL(P||Q) <= osc(s) = sum_i osc(s_i).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Certificate(ABC):
    @abstractmethod
    def compose(self, other: "Certificate") -> "Certificate":
        """Return the certificate for the composition of self and other."""
        ...

    @abstractmethod
    def dominates(self, other: "Certificate") -> bool:
        """True iff self.kl_bound() <= other.kl_bound()."""
        ...

    @abstractmethod
    def kl_bound(self) -> float:
        """Upper bound on KL(P||Q). Always >= 0. May be math.inf."""
        ...


@dataclass(frozen=True)
class ExactCertificate(Certificate):
    """Zero-error certificate. Residual is identically zero."""

    def compose(self, other: Certificate) -> Certificate:
        return other

    def dominates(self, other: Certificate) -> bool:
        return True

    def kl_bound(self) -> float:
        return 0.0


@dataclass(frozen=True)
class HilbertIntervalCertificate(Certificate):
    """
    Certificate from Hilbert/order geometry.

    Certifies that s(omega) in [lo, hi] for all omega, where
    s = log(W/W_tilde) is the log-residual.

    KL bound: osc(s) = hi - lo.
    """

    lo: float
    hi: float

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            raise ValueError(
                f"HilbertIntervalCertificate requires lo <= hi, got lo={self.lo}, hi={self.hi}"
            )

    def compose(self, other: Certificate) -> Certificate:
        if isinstance(other, ExactCertificate):
            return self
        if isinstance(other, HilbertIntervalCertificate):
            return HilbertIntervalCertificate(
                lo=self.lo + other.lo,
                hi=self.hi + other.hi,
            )
        if isinstance(other, InfiniteCertificate):
            return other
        raise TypeError(f"Unknown certificate type: {type(other)}")

    def dominates(self, other: Certificate) -> bool:
        return self.kl_bound() <= other.kl_bound()

    def kl_bound(self) -> float:
        return self.hi - self.lo


@dataclass(frozen=True)
class InfiniteCertificate(Certificate):
    """
    Certificate indicating KL is infinite.

    Issued when support fails (approximate law misses exact positive mass)
    or when no sound finite certificate can be constructed.
    """

    reason: str = ""

    def compose(self, other: Certificate) -> Certificate:
        return self

    def dominates(self, other: Certificate) -> bool:
        return isinstance(other, InfiniteCertificate)

    def kl_bound(self) -> float:
        return math.inf


@dataclass(frozen=True)
class FKKLCertificate(Certificate):
    """
    Post-hoc FK-KL secant certificate.

    Produced by running the FK-KL certifier on the executed approximate plan.
    Typically tighter than HilbertIntervalCertificate because it uses the
    log-MGF of the actual residual rather than a worst-case oscillation bound.

    Composition: when an FK-KL site is composed with other sites, we fall back
    to treating the bound additively (sound but conservative).  In practice
    FK-KL is applied as a root-boundary upgrade after the plan is selected, so
    composition with other FK-KL certificates does not arise.
    """

    bound: float               # certified KL upper bound (>= 0)
    active_h: float = 0.0     # secant h that minimized the bound (diagnostic)

    def __post_init__(self) -> None:
        if self.bound < 0:
            raise ValueError(f"FKKLCertificate bound must be >= 0, got {self.bound}")

    def compose(self, other: Certificate) -> Certificate:
        if isinstance(other, ExactCertificate):
            return self
        if isinstance(other, FKKLCertificate):
            return FKKLCertificate(bound=self.bound + other.bound,
                                   active_h=min(self.active_h, other.active_h))
        if isinstance(other, HilbertIntervalCertificate):
            # Degrade to Hilbert when composing with a Hilbert-certified site.
            return HilbertIntervalCertificate(
                lo=-(self.bound / 2) + other.lo,
                hi=(self.bound / 2) + other.hi,
            )
        if isinstance(other, InfiniteCertificate):
            return other
        raise TypeError(f"Unknown certificate type: {type(other)}")

    def dominates(self, other: Certificate) -> bool:
        return self.kl_bound() <= other.kl_bound()

    def kl_bound(self) -> float:
        return self.bound
