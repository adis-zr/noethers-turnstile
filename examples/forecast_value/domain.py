"""§2 Framework primitives instantiated for the frost-protection domain.

Reuses the noethers_turnstile compiler. New: the evidence map q, fiber
assembly, world-level a(w) (the soundness mapping), the meet A(e), the
permission skeleton requirement map, and the naive-coarse compiler.

Conceptual separation (preserving spec §2):

  a(w)    — strongest action sound in world w. A direct function of world
            properties (L_real, frost-event severity). Does NOT consult the
            compiler. This is ground-truth soundness, not what evidence
            permits.

  q(w) → e — the evidence map. Records what the evidence vocabulary
            preserves about the world. Worlds with the same q(w) form a
            fiber F(e).

  fiber gap statuses — for each gap in the fine vocabulary, the status
            computed by aggregating across all worlds in F(e). E.g. the
            duration_gap is "bounded" iff the fiber's max-dwell among
            frost-event worlds is below the bounded threshold.

  A(e) = meet over F(e) of a(w) — the latent authorization. Computed
            directly from a(w), not from gap statuses.

  C_compiler(e) — the compiler's emit on the fiber gap statuses + a
            requirement map. The HONEST compiler at L0 satisfies
            C_compiler(e) ≼ A(e) (admissibility). The NAIVE-COARSE compiler
            at L3 violates this because the inadmissible projection has
            dropped the duration and vulnerability obligations.

The permission skeleton (the requirement map):

  REF : base
  DIA : exceedance reported
  REV : exceedance bounded
  AEX : exceedance bounded + (duration OR vulnerability bounded)
  ALR : exceedance bounded + duration bounded + vulnerability bounded

The AEX disjunction is encoded explicitly via two AEX-variant profiles
(AEX_dur and AEX_vul); the compiler emits AEX iff either is satisfied.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

_HERE = Path(__file__).resolve().parent
_WORKSPACE_PY = _HERE.parents[1] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t  # noqa: E402

# ── Native forecast chain ────────────────────────────────────────────────────
#
# Levels are the frost-protection deployment phases declared by name. The
# AEX-disjunction (duration OR vulnerability bounded) can in principle use
# the Phase 1b GapRequirement.any_of, but the existing compile_honest
# implementation already encodes it via a two-pass compile + join. We keep
# that machinery here and translate level names through the bijection so
# the numerical results (verdict, Ae_monotone, manufactured_permission)
# are preserved bit-for-bit.

_FORECAST_LEVELS = [
    "NO_ACTION",                  # REF analogue (refusal / no permission)
    "REPORT_EXCEEDANCE",          # DIA analogue (output exists, nothing else)
    "BOUND_EXCEEDANCE",           # REV analogue (exceedance bounded)
    "ACT_ON_PARTIAL_EVIDENCE",    # AEX analogue (exceedance + duration OR vulnerability)
    "ACT_ON_FULL_EVIDENCE",       # ALR analogue (all three bounded)
    "FULL_AUTHORITY",             # AAA analogue (ceiling)
]

FORECAST_CHAIN = t.PermissionChain.new(
    levels=_FORECAST_LEVELS,
    roles={
        t.ChainRole.Bottom: 0,
        t.ChainRole.ExpiryFloor: 0,
        t.ChainRole.Refused: 0,
        t.ChainRole.Unsatisfied: 0,
        t.ChainRole.DisallowedUsesCeiling: 0,
        t.ChainRole.BlockerThreshold: 1,
        t.ChainRole.Top: 5,
    },
)

# Bijection between default-chain emits and the native chain.
BIJECTION = {
    "OOC": "NO_ACTION",
    "EXP": "NO_ACTION",
    "REF": "NO_ACTION",
    "UNS": "NO_ACTION",
    "DIA": "REPORT_EXCEEDANCE",
    "REV": "BOUND_EXCEEDANCE",
    "AEX": "ACT_ON_PARTIAL_EVIDENCE",
    "ALR": "ACT_ON_FULL_EVIDENCE",
    "AAA": "FULL_AUTHORITY",
}

from worldgen import (  # noqa: E402
    World, DAMAGE_THRESHOLD_C, L_MAX, COST_C,
)

_NOW = 1_748_736_000.0

# ── Permission lattice ────────────────────────────────────────────────────────

_PERM_TO_RANK = {"REF": 0, "DIA": 1, "REV": 2, "AEX": 3, "ALR": 4}
_RANK_TO_PERM = {v: k for k, v in _PERM_TO_RANK.items()}


def perm_rank(p: str) -> int:
    return _PERM_TO_RANK.get(p, 0)


def perm_meet(perms: Iterable[str]) -> str:
    ranks = [perm_rank(p) for p in perms]
    return _RANK_TO_PERM[min(ranks)] if ranks else "REF"


def perm_join(perms: Iterable[str]) -> str:
    ranks = [perm_rank(p) for p in perms]
    return _RANK_TO_PERM[max(ranks)] if ranks else "REF"


# ── World-level authorization a(w) ────────────────────────────────────────────
#
# a(w) is a direct function of world soundness. It does NOT consult the
# compiler. Damaging worlds justify autonomous action (ALR). Benign worlds
# justify escalation to a human (REV) rather than autonomous action — because
# committing cost C for ~0 averted loss is unsound. Marginal worlds (some
# damage expected, but not catastrophic) sit at AEX.

# Soundness thresholds on L_real (placeholders).
L_ALR_THRESHOLD = 0.30        # L_real ≥ 0.30 → ALR sound
L_AEX_THRESHOLD = 0.10        # L_real ≥ 0.10 → AEX sound
L_REV_THRESHOLD = 0.0         # any L_real > 0 → REV (escalate)
# L_real == 0 in a benign world: REV is still the strongest sound action
# (escalate to operator for awareness), per spec §2.4.


def world_authorization(w: World) -> str:
    """a(w) — strongest action sound in world w.

    Damaging worlds (L_real ≥ L_ALR_THRESHOLD): ALR sound.
    Marginal worlds (L_AEX_THRESHOLD ≤ L_real < L_ALR_THRESHOLD): AEX sound.
    Benign-leaning worlds (0 < L_real < L_AEX_THRESHOLD): REV sound.
    No-frost worlds (L_real == 0): REV sound — escalate (forecast surfaced
        the possibility; operator can confirm conditions).
    """
    if w.l_real >= L_ALR_THRESHOLD:
        return "ALR"
    elif w.l_real >= L_AEX_THRESHOLD:
        return "AEX"
    else:
        return "REV"


# ── Evidence map q(w) and fibers ──────────────────────────────────────────────
#
# Fine vocabulary L0:    (p_hat_bin, regime, phenology_band)
# Mid  vocabulary L1:    (p_hat_bin_coarse, regime, phenology_band)
# Mid  vocabulary L2:    (p_hat_bin_coarse, combined_regime_pheno)
# Inadmissible L3:       (p_hat_bin only)        — drops regime + phenology
#
# The p_hat bin width controls fiber granularity.

P_HAT_BIN_WIDTH = 0.05
P_HAT_BIN_WIDTH_COARSE = 0.10


def _p_hat(w: World) -> float:
    from worldgen import forecast_probability
    return forecast_probability(w.forecast_t_min)


def _phenology_band(phenology: str) -> str:
    return "hardy" if phenology in {"dormant", "swollen"} else "vulnerable"


# T_min binning: evidence resolves T_min to a coarse band, not the exact value.
# Without this, the fiber at a given p_hat ranges over very wide T_min values
# (because p_hat alone underdetermines T_min), forcing the meet down to REV
# via any single warm-night realization. Binning by forecast_t_min separates
# "cold-night forecast" fibers from "ambiguous" fibers cleanly.
T_MIN_BIN_WIDTH = 1.0  # °C


def _t_min_bin(forecast_t_min: float) -> float:
    return round(forecast_t_min / T_MIN_BIN_WIDTH) * T_MIN_BIN_WIDTH


def evidence_L0(w: World) -> tuple:
    """L0 — full fine vocabulary: (binned forecast T_min, regime, phenology band).

    The forecast resolves T_min to a band (e.g. 1°C). Within a band, only the
    realization noise + dwell + phenology are unresolved by the evidence.
    """
    return (_t_min_bin(w.forecast_t_min), w.regime, _phenology_band(w.phenology))


T_MIN_BIN_WIDTH_COARSE = 2.0  # °C


def evidence_L1(w: World) -> tuple:
    """L1 — coarsen T_min bins. Admissible: still resolves regime+phenology."""
    t_bin = round(w.forecast_t_min / T_MIN_BIN_WIDTH_COARSE) * T_MIN_BIN_WIDTH_COARSE
    return (t_bin, w.regime, _phenology_band(w.phenology))


def evidence_L2(w: World) -> tuple:
    """L2 — merge regime and phenology into a single composite. Admissible."""
    t_bin = round(w.forecast_t_min / T_MIN_BIN_WIDTH_COARSE) * T_MIN_BIN_WIDTH_COARSE
    composite = f"{w.regime}-{_phenology_band(w.phenology)}"
    return (t_bin, composite)


def evidence_L3(w: World) -> tuple:
    """L3 — drop regime + phenology entirely. Inadmissible coarsening."""
    t_bin = round(w.forecast_t_min / T_MIN_BIN_WIDTH_COARSE) * T_MIN_BIN_WIDTH_COARSE
    return (t_bin,)


EVIDENCE_LEVELS = {
    "L0": evidence_L0,
    "L1": evidence_L1,
    "L2": evidence_L2,
    "L3": evidence_L3,
}


def assemble_fibers(worlds: list[World], evidence_fn) -> dict[tuple, list[World]]:
    """Group worlds by their evidence state."""
    fibers: dict[tuple, list[World]] = {}
    for w in worlds:
        key = evidence_fn(w)
        fibers.setdefault(key, []).append(w)
    return fibers


# ── A(e) — latent authorization ───────────────────────────────────────────────

def latent_authorization(fiber: list[World]) -> tuple[str, World | None]:
    """A(e) = meet over F(e) of a(w). Returns (permission, pinning world)."""
    if not fiber:
        return ("REF", None)
    per_world = [(world_authorization(w), w) for w in fiber]
    pinning = min(per_world, key=lambda pw: perm_rank(pw[0]))
    return (pinning[0], pinning[1])


# ── Gap statuses (computed from the FIBER, not from individual worlds) ───────
#
# The fiber's gap statuses describe what the evidence map resolves about the
# fiber's worlds. These feed the COMPILER as the implementation of A(e)
# under the permission-skeleton requirement map.

GAP_EXCEEDANCE    = "exceedance_gap"
GAP_DURATION      = "duration_gap"
GAP_VULNERABILITY = "vulnerability_gap"

# Thresholds for fiber-level gap statuses
DURATION_BOUNDED_MAX_DWELL = 90.0     # fiber duration_gap = bounded iff max dwell ≤ 90 min on frost worlds
DURATION_CLOSED_MAX_DWELL = 30.0      # iff max dwell ≤ 30 min on frost worlds
# Vulnerability bounded iff all worlds in fiber are NOT in vulnerable stages
# (the fiber-level resolution: did the evidence vocabulary tell us the
# phenology band? If yes and band=hardy → bounded/closed; if band=vulnerable
# → open).


def fiber_gap_statuses(fiber: list[World], evidence_key: tuple,
                        evidence_level: str) -> dict[str, str]:
    """Compute gap statuses for a fiber under a given evidence level.

    At L0, L1, L2: the evidence includes regime and phenology, so duration
      and vulnerability gaps are derivable from the fiber. Their statuses
      ARE included in the returned dict.

    At L3: the evidence does NOT include regime or phenology. The fine
      duration_gap and vulnerability_gap obligations are NOT EXPRESSIBLE
      in the L3 vocabulary — they are dropped from the returned dict
      entirely. This is the inadmissible coarsening: the projection
      vocabulary cannot speak to those obligations at all. The naive-coarse
      compiler, which builds its requirement map from whatever gaps are in
      the dict, will therefore have NO duration/vulnerability requirements
      and will manufacture permission.
    """
    # Exceedance gap: always bounded (forecast is calibrated by construction)
    statuses: dict[str, str] = {GAP_EXCEEDANCE: "bounded"}

    if evidence_level in ("L0", "L1"):
        regime = evidence_key[1]
        pheno_band = evidence_key[2]
    elif evidence_level == "L2":
        composite = evidence_key[1]
        regime, pheno_band = composite.split("-")
    elif evidence_level == "L3":
        # L3 drops regime + phenology — the gaps are not expressible.
        return statuses
    else:
        raise ValueError(f"Unknown evidence level {evidence_level}")

    # Duration gap from the fiber
    if regime == "advective":
        duration = "closed"
    else:
        frost_dwells = [w.dwell_minutes for w in fiber if w.frost_event]
        if not frost_dwells:
            duration = "closed"
        else:
            max_dwell = max(frost_dwells)
            if max_dwell <= DURATION_CLOSED_MAX_DWELL:
                duration = "closed"
            elif max_dwell <= DURATION_BOUNDED_MAX_DWELL:
                duration = "bounded"
            else:
                duration = "open"

    # Vulnerability gap from the fiber
    if pheno_band == "hardy":
        vulnerability = "closed"
    else:  # vulnerable
        vulnerability = "open"

    statuses[GAP_DURATION] = duration
    statuses[GAP_VULNERABILITY] = vulnerability
    return statuses


# ── Requirement map — the permission skeleton ────────────────────────────────

# AEX is the disjunction (duration_bounded OR vulnerability_bounded). The
# compiler does not directly express disjunction in requirements, so we use
# two AEX-variant profile names internally and post-hoc combine.
#
# Standard reqs:
DEFAULT_REQUIREMENTS: dict[str, dict[str, str]] = {
    "DIA": {},
    "REV": {GAP_EXCEEDANCE: "bounded"},
    # We will compile twice: once with AEX requiring duration, once with AEX
    # requiring vulnerability. Then AEX is the OR. See compile_honest below.
    "AEX_dur": {GAP_EXCEEDANCE: "bounded", GAP_DURATION: "bounded"},
    "AEX_vul": {GAP_EXCEEDANCE: "bounded", GAP_VULNERABILITY: "bounded"},
    "ALR": {GAP_EXCEEDANCE: "bounded",
            GAP_DURATION: "bounded",
            GAP_VULNERABILITY: "bounded"},
}


def _build_profiles(reqs_subset: dict[str, dict[str, str]]) -> list[t.Profile]:
    """Build noethers_turnstile profiles from a (perm_name -> reqs) dict.

    Only emits a profile for a permission level if the dict contains an entry
    for that level (even an empty {}). A permission level NOT in the dict is
    treated as 'not expressible' and gets no profile — the compiler will not
    emit that permission.

    To prevent the compiler defaulting to a higher level via missing-profile
    fallback, we always emit a sentinel profile for AAA that demands an
    impossible status if AAA is not in the input dict — this forces the
    output to be capped at the strongest non-AAA profile that IS present.
    """
    perms = [t.Permission.DIA, t.Permission.REV, t.Permission.AEX,
             t.Permission.ALR, t.Permission.AAA]
    profiles = []
    _SENTINEL_BLOCK_GAP = "__sentinel_block__"
    for perm in perms:
        name = str(perm)
        if name in reqs_subset:
            gap_to_req = reqs_subset[name]
            required = [t.GapRequirement(gid, r) for gid, r in gap_to_req.items()]
        else:
            # Profile NOT expressible at this level. Install a sentinel
            # requirement on a gap that won't be present in any case, so the
            # compiler cannot satisfy this profile.
            required = [t.GapRequirement(_SENTINEL_BLOCK_GAP, "closed")]
        profiles.append(t.Profile(perm, required))
    return profiles


_SENTINEL_BLOCK_GAP = "__sentinel_block__"


def _compile_single_profile_set(
    statuses: dict[str, str],
    reqs: dict[str, dict[str, str]],
    fingerprint: str,
) -> str:
    profiles = _build_profiles(reqs)
    gap_records = [t.GapRecord(gid, gid, status=s) for gid, s in statuses.items()]
    # Add the sentinel gap as a GapRecord with status=open so it can never
    # satisfy a 'closed' requirement. This is the mechanism by which missing
    # permission profiles are blocked.
    gap_records.append(t.GapRecord(_SENTINEL_BLOCK_GAP, _SENTINEL_BLOCK_GAP, status="open"))
    ctx = t.ProofContext(
        claim_id=f"claim-{fingerprint}",
        candidate_id=f"system-{fingerprint}",
        context_id=f"ctx-{fingerprint}",
        allowed_use="frost_protection",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=gap_records, profiles=profiles, tokens=[],
        context_fingerprint=fingerprint,
    )
    j = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=fingerprint)
    try:
        return str(j.permission(rt))
    except t.ExpiredError:
        return "REF"


def _filter_reqs_to_available_gaps(
    reqs: dict[str, dict[str, str]],
    available_gaps: set[str],
) -> dict[str, dict[str, str]]:
    """Honest filter: drop a profile entirely if it references any gap not in
    the available_gaps set. The semantic meaning: that permission is not
    expressible in the current vocabulary, so the compiler cannot reach it.
    DIA always remains (no requirements).
    """
    filtered: dict[str, dict[str, str]] = {}
    for perm_name, gap_to_req in reqs.items():
        if perm_name == "DIA":
            filtered[perm_name] = gap_to_req
            continue
        if all(gid in available_gaps for gid in gap_to_req.keys()):
            filtered[perm_name] = gap_to_req
        # else: drop the profile entirely
    return filtered


def compile_honest(statuses: dict[str, str], fingerprint: str) -> str:
    """Honest compile under the full permission skeleton.

    Profiles that reference gaps not present in the statuses dict are dropped
    entirely: that permission level is NOT expressible under this evidence
    vocabulary. At L3 with only exceedance_gap available, AEX and ALR are
    dropped, and the strongest reachable level is REV.

    Compiles twice to encode the disjunctive AEX (duration OR vulnerability),
    then takes the join. AAA mirrors ALR so the compiler doesn't satisfy AAA
    via vacuous requirements.
    """
    available = set(statuses.keys())
    full_alr = DEFAULT_REQUIREMENTS["ALR"]
    base_reqs = {
        "DIA": {},
        "REV": DEFAULT_REQUIREMENTS["REV"],
        "AEX": {GAP_EXCEEDANCE: "bounded", GAP_DURATION: "bounded"},
        "ALR": full_alr,
        "AAA": full_alr,
    }
    aex_vul_reqs = {
        "DIA": {},
        "REV": DEFAULT_REQUIREMENTS["REV"],
        "AEX": {GAP_EXCEEDANCE: "bounded", GAP_VULNERABILITY: "bounded"},
        "ALR": full_alr,
        "AAA": full_alr,
    }
    base_filtered = _filter_reqs_to_available_gaps(base_reqs, available)
    vul_filtered = _filter_reqs_to_available_gaps(aex_vul_reqs, available)
    p1 = _compile_single_profile_set(statuses, base_filtered, fingerprint + "-dur")
    p2 = _compile_single_profile_set(statuses, vul_filtered, fingerprint + "-vul")
    return perm_join([p1, p2])


def compile_naive_coarse(statuses: dict[str, str], fingerprint: str) -> str:
    """Naive-coarse compiler.

    At L3, the inadmissible coarsening drops duration + vulnerability handles.
    A naive practitioner re-derives the requirement map from the coarse
    vocabulary: since the coarse statuses dict only contains exceedance_gap,
    the naive ALR requires only exceedance bounded. This MANUFACTURES
    permission compared to the honest A(e).

    For other levels, naive-coarse uses whatever gaps are in the statuses dict
    with a uniform-bounded ALR (no closed-strict requirements). At L0/L1/L2
    this still references duration + vulnerability, so the result coincides
    with the honest compile.

    AAA mirrors ALR — same fix as compile_honest.
    """
    available_gaps = set(statuses.keys())
    naive_alr_reqs: dict[str, str] = {gap: "bounded" for gap in available_gaps}
    naive_aex_reqs: dict[str, str] = {GAP_EXCEEDANCE: "bounded"}
    if GAP_DURATION in available_gaps:
        naive_aex_reqs[GAP_DURATION] = "bounded"
    elif GAP_VULNERABILITY in available_gaps:
        naive_aex_reqs[GAP_VULNERABILITY] = "bounded"
    reqs = {
        "DIA": {},
        "REV": {GAP_EXCEEDANCE: "bounded"},
        "AEX": naive_aex_reqs,
        "ALR": naive_alr_reqs,
        "AAA": naive_alr_reqs,
    }
    return _compile_single_profile_set(statuses, reqs, fingerprint + "-naive")
