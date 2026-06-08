"""k → ∞ probe across all paper domains.

Two complementary experiments:

  PART A — Continuous-axis k saturation
    For Turbo, Ising, FAA: extend k far beyond the existing 256-cap.
    Question: does breakpoint count saturate at a finite k*?
    Predicts:
      Turbo (smooth) — keeps growing, possibly log-like, no saturation.
      Ising (single step) — constant at 1 for all k.
      FAA (kink) — saturates at finite k* tied to the resolved smooth-region
                   structure above the saturation height.

  PART B — Categorical chain-length probe (the "domain-bridge" question)
    For ILS and Epic: vary the *permission chain length* by interpolating
    additional named permission levels between the existing chain. The
    requirement map can be extended in two regimes:

      B1 — Empty interpolation:
        New permission levels carry the SAME requirements as the existing
        level immediately above. The compiler can satisfy the new level
        whenever it satisfies the next existing level, so emits are
        unchanged. Tests: are empty-chain extensions inert?

      B2 — Refined interpolation:
        New levels carry a PARTIAL requirement subset of the next existing
        level. The compiler emits the new intermediate level for cases that
        satisfy the partial requirements but not the full ones. Tests:
        does the compiler emit the new levels exactly when the partial
        requirements are met?

This is the user's "permission-chain vs domain-bridge" question. The chain
is the named lattice; the domain bridge is the requirement map (which gaps
gate which level). Adding levels without adding requirements is inert;
adding levels with new requirements changes the emit set.

Outputs:
  results/k_probe_A_continuous.csv     part A row-level data
  results/k_probe_A_summary.json       saturation k* per domain
  results/k_probe_B_categorical.csv    part B per-case emit per chain
  results/k_probe_B_summary.json       chain-length effect on emit counts
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_WORKSPACE_PY = _HERE.parents[1] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

_TURBO_DIR = _HERE.parent / "inference" / "register2" / "turbo"
if str(_TURBO_DIR) not in sys.path:
    sys.path.insert(0, str(_TURBO_DIR))
_ISING_DIR = _HERE.parent / "inference" / "ising"
if str(_ISING_DIR) not in sys.path:
    sys.path.insert(0, str(_ISING_DIR))
_ILS_DIR = _HERE.parent / "ils"
if str(_ILS_DIR) not in sys.path:
    sys.path.insert(0, str(_ILS_DIR))
_EPIC_DIR = _HERE.parent / "epic"
if str(_EPIC_DIR) not in sys.path:
    sys.path.insert(0, str(_EPIC_DIR))
if str(_EPIC_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_EPIC_DIR.parent))

import noethers_turnstile as t

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ── Part A — continuous-axis k saturation ────────────────────────────────────

# Extended grid: more than 4x the existing cap.
K_LEVELS_EXTENDED = [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]


def _permission_k(error: float, thresholds_desc: np.ndarray) -> float:
    return float(np.sum(error <= thresholds_desc)) / len(thresholds_desc)


def _count_breakpoints(values: list[float]) -> int:
    return sum(1 for i in range(1, len(values)) if values[i] != values[i-1])


def run_turbo_kprobe() -> dict:
    """Turbo extended k probe."""
    from ber_bler_curves import bler_at_snr, ber_at_snr  # type: ignore

    snr_grid = np.round(np.arange(-1.0, 5.01, 0.1), 2)
    bler_lo, bler_hi = 1e-4, 1.0
    bps_by_k: dict[int, int] = {}
    rows = []
    for k in K_LEVELS_EXTENDED:
        thresholds = np.logspace(np.log10(bler_hi), np.log10(bler_lo), k)
        permissions = []
        for snr in snr_grid:
            bler = bler_at_snr(float(snr))
            permissions.append(_permission_k(bler, thresholds))
        bps = _count_breakpoints(permissions)
        bps_by_k[k] = bps
        rows.append({"domain": "turbo", "k": k, "n_axis_points": len(snr_grid),
                     "breakpoints": bps})
    return {"breakpoints_by_k": bps_by_k, "rows": rows,
            "n_axis_points": len(snr_grid)}


def run_ising_kprobe() -> dict:
    """Ising extended k probe."""
    from generate_ising import make_ising_grid_with_field as make_ising_grid  # type: ignore
    from run_exact import compute_exact_marginals  # type: ignore
    from run_bp import run_loopy_bp  # type: ignore
    from compiler import tv_distance, tv_distance_max  # type: ignore

    g = make_ising_grid(6, 0.44)
    exact = compute_exact_marginals(g)
    result = run_loopy_bp(g)
    tv_max_val = tv_distance_max(result["marginals"], exact)
    TV_MAX = 0.3338  # canonical value from the paper

    bps_by_k: dict[int, int] = {}
    loc_err_by_k: dict[int, float] = {}
    rows = []
    for k in K_LEVELS_EXTENDED:
        # Uniform tau grid over [0, 0.50] with k points
        thresholds = np.linspace(0.0, 0.50, k + 1)[1:]
        permissions = [1.0 if tau >= tv_max_val else 0.0 for tau in thresholds]
        bps = _count_breakpoints(permissions)
        # Location error: first tau where perm flips to 1
        step_taus = [thresholds[i] for i in range(len(thresholds)) if permissions[i] >= 1.0 - 1e-9]
        step_tau = step_taus[0] if step_taus else float("nan")
        loc_err = abs(step_tau - tv_max_val) if step_taus else float("nan")
        bps_by_k[k] = bps
        loc_err_by_k[k] = loc_err
        spacing = 0.50 / k
        rows.append({"domain": "ising", "k": k, "n_axis_points": k,
                     "breakpoints": bps, "step_tau": float(step_tau),
                     "location_error": float(loc_err), "grid_spacing": spacing,
                     "err_over_spacing": loc_err / spacing if spacing > 0 else 0.0})
    return {"breakpoints_by_k": bps_by_k,
            "location_error_by_k": loc_err_by_k,
            "rows": rows,
            "tv_max_used": float(tv_max_val)}


def run_faa_kprobe() -> dict:
    """FAA extended k probe."""
    from geometry import rvr_floor  # type: ignore

    dh_grid = np.round(np.arange(300.0, 48.0, -2.0), 1)
    rvr_lo, rvr_hi = 0.0, 2400.0
    bps_by_k: dict[int, int] = {}
    rows = []
    for k in K_LEVELS_EXTENDED:
        thresholds = np.linspace(rvr_lo, rvr_hi, k)
        permissions = []
        for dh in dh_grid:
            geo = rvr_floor(float(dh))
            rvr_f = geo.rvr_floor_ft
            permissions.append(_permission_k(rvr_f, thresholds[::-1]))
        bps = _count_breakpoints(permissions)
        bps_by_k[k] = bps
        rows.append({"domain": "faa", "k": k, "n_axis_points": len(dh_grid),
                     "breakpoints": bps})
    return {"breakpoints_by_k": bps_by_k, "rows": rows,
            "n_axis_points": len(dh_grid)}


def _detect_saturation_k_star(bps_by_k: dict[int, int]) -> int | None:
    """Find smallest k such that bps stays constant for all larger tested k.
    Returns None if no saturation observed in the tested range.
    """
    ks = sorted(bps_by_k.keys())
    if len(ks) < 3:
        return None
    final_bp = bps_by_k[ks[-1]]
    # Walk back: smallest k where bps == final_bp and bps stays == final_bp.
    saturation_k = None
    for i in range(len(ks) - 1, -1, -1):
        if bps_by_k[ks[i]] == final_bp:
            saturation_k = ks[i]
        else:
            break
    if saturation_k is None or saturation_k == ks[-1]:
        return None
    return saturation_k


def _detect_growth_rate(bps_by_k: dict[int, int]) -> dict:
    """Fit log_2(k) growth to bps to identify slow-growth (log) vs linear."""
    ks = np.array(sorted(bps_by_k.keys()), dtype=float)
    bps = np.array([bps_by_k[int(k)] for k in ks], dtype=float)
    if len(ks) < 3:
        return {"slope_linear": None, "slope_log2": None, "linear_r2": None, "log2_r2": None}
    # Linear fit bps ~ a * k + b
    a_lin, b_lin = np.polyfit(ks, bps, 1)
    pred_lin = a_lin * ks + b_lin
    ss_res_lin = float(np.sum((bps - pred_lin) ** 2))
    ss_tot = float(np.sum((bps - bps.mean()) ** 2))
    r2_lin = 1 - ss_res_lin / ss_tot if ss_tot > 0 else float("nan")
    # Log-2 fit bps ~ a * log2(k) + b
    log2k = np.log2(ks)
    a_log, b_log = np.polyfit(log2k, bps, 1)
    pred_log = a_log * log2k + b_log
    ss_res_log = float(np.sum((bps - pred_log) ** 2))
    r2_log = 1 - ss_res_log / ss_tot if ss_tot > 0 else float("nan")
    return {
        "slope_linear": float(a_lin), "linear_intercept": float(b_lin),
        "linear_r2": float(r2_lin),
        "slope_log2": float(a_log), "log2_intercept": float(b_log),
        "log2_r2": float(r2_log),
    }


# ── Part B — categorical chain-length probe ──────────────────────────────────
#
# The compiler's underlying alphabet has 12 levels:
#   OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
# The paper uses 5 named levels for the categorical experiments:
#   REF < DIA < REV < AEX < ALR
# We can interpolate by adding ROL (between REF and DIA) and exploring whether
# adding it (with various requirement maps) changes the emit set.
#
# Two regimes:
#   B1: ROL has the SAME requirements as DIA. Empty-chain interpolation.
#   B2: ROL has a STRICTER subset of DIA's requirements (impossible at DIA
#       level; weaker than DIA). Or: ROL has a refined intermediate requirement
#       between REF (no reqs) and DIA's reqs. Refined interpolation.
#
# For Epic (5 levels: REF DIA REV AEX ALR), we extend to 6 by adding ROL.
# For ILS (4 levels: REF DIA REV ALR), we extend to 5 by adding ROL.

_PERM_ORDER = ["OOC", "EXP", "REF", "UNS", "ETA", "ESC", "ROL", "DIA",
               "REV", "AEX", "ALR", "AAA"]
_PERM_RANK = {p: i for i, p in enumerate(_PERM_ORDER)}


def _perm_obj(name: str):
    return getattr(t.Permission, name)


def _build_profile_chain(
    chain_name_to_reqs: dict[str, dict[str, str]],
    sentinel_for_missing: bool = True,
) -> list[t.Profile]:
    """Build the full 12-permission profile list. Levels not in the chain
    are blocked by a sentinel-closed requirement so the compiler cannot
    satisfy them via vacuous requirements.
    """
    SENTINEL = "__chain_sentinel__"
    profiles = []
    for perm_name in _PERM_ORDER:
        if perm_name in chain_name_to_reqs:
            reqs = chain_name_to_reqs[perm_name]
            required = [t.GapRequirement(gid, r) for gid, r in reqs.items()]
        elif sentinel_for_missing:
            required = [t.GapRequirement(SENTINEL, "closed")]
        else:
            required = []
        profiles.append(t.Profile(_perm_obj(perm_name), required))
    return profiles


def _compile_with_chain(
    gap_statuses: dict[str, str],
    chain: dict[str, dict[str, str]],
    fingerprint: str,
) -> str:
    """Compile under a chain with optional intermediate levels."""
    profiles = _build_profile_chain(chain)
    SENTINEL = "__chain_sentinel__"
    gap_records = [t.GapRecord(gid, gid, status=s) for gid, s in gap_statuses.items()]
    gap_records.append(t.GapRecord(SENTINEL, SENTINEL, status="open"))
    ctx = t.ProofContext(
        claim_id=f"claim-{fingerprint}",
        candidate_id=f"system-{fingerprint}",
        context_id=f"ctx-{fingerprint}",
        allowed_use="kprobe",
        membership=t.Membership.InClass,
        authority_ceiling=_perm_obj("AAA"),
        expiry=t.Expiry.never(),
        gaps=gap_records, profiles=profiles, tokens=[],
        context_fingerprint=fingerprint,
    )
    judgment = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=1_748_736_000.0, context_fingerprint=fingerprint)
    try:
        return str(judgment.permission(rt))
    except t.ExpiredError:
        return "REF"


# ── ILS chain experiments ──────────────────────────────────────────────────────

_ILS_GAPS = ["ils_signal_integrity", "visual_reference", "sub_cat1_authorization"]

# Standard ILS chain (paper):
#   ALR: all three closed
#   REV: signal closed, visual closed, auth open
#   DIA: signal closed, visual open, auth open
#   REF: all open
_ILS_STANDARD_CHAIN = {
    "REF": {},
    "DIA": {"ils_signal_integrity": "closed"},
    "REV": {"ils_signal_integrity": "closed", "visual_reference": "closed"},
    "ALR": {"ils_signal_integrity": "closed", "visual_reference": "closed",
            "sub_cat1_authorization": "closed"},
}

# B1 empty interpolation: add ROL = same as DIA. Should be inert.
_ILS_B1_CHAIN = {
    "REF": {},
    "ROL": {"ils_signal_integrity": "closed"},  # same as DIA
    "DIA": {"ils_signal_integrity": "closed"},
    "REV": {"ils_signal_integrity": "closed", "visual_reference": "closed"},
    "ALR": {"ils_signal_integrity": "closed", "visual_reference": "closed",
            "sub_cat1_authorization": "closed"},
}

# B2 refined interpolation: add ROL with a *weaker* signal requirement.
# ROL: signal bounded (not closed). DIA: signal closed.
# This refines the signal axis: a fiber with signal=bounded reaches ROL but
# not DIA, and one with signal=closed reaches DIA.
_ILS_B2_CHAIN = {
    "REF": {},
    "ROL": {"ils_signal_integrity": "bounded"},
    "DIA": {"ils_signal_integrity": "closed"},
    "REV": {"ils_signal_integrity": "closed", "visual_reference": "closed"},
    "ALR": {"ils_signal_integrity": "closed", "visual_reference": "closed",
            "sub_cat1_authorization": "closed"},
}


def _ils_test_cases():
    """ILS evidence cases spanning the gap-status grid."""
    return [
        ("all_open",    {"ils_signal_integrity": "open",    "visual_reference": "open",    "sub_cat1_authorization": "open"}),
        ("sig_bounded", {"ils_signal_integrity": "bounded", "visual_reference": "open",    "sub_cat1_authorization": "open"}),
        ("sig_closed",  {"ils_signal_integrity": "closed",  "visual_reference": "open",    "sub_cat1_authorization": "open"}),
        ("sig_vis",     {"ils_signal_integrity": "closed",  "visual_reference": "closed",  "sub_cat1_authorization": "open"}),
        ("all_closed",  {"ils_signal_integrity": "closed",  "visual_reference": "closed",  "sub_cat1_authorization": "closed"}),
    ]


def run_ils_chain_probe() -> list[dict]:
    rows = []
    cases = _ils_test_cases()
    for case_name, statuses in cases:
        for chain_name, chain in [
            ("standard_4lvl", _ILS_STANDARD_CHAIN),
            ("B1_empty_5lvl", _ILS_B1_CHAIN),
            ("B2_refined_5lvl", _ILS_B2_CHAIN),
        ]:
            emit = _compile_with_chain(statuses, chain, f"ils-{chain_name}-{case_name}")
            rows.append({
                "domain": "ils", "case": case_name, "chain": chain_name,
                "chain_length": len(chain),
                "emit": emit,
                "emit_rank": _PERM_RANK[emit],
            })
    return rows


# ── Epic chain experiments ─────────────────────────────────────────────────────

_EPIC_GAPS = [
    "approximation_quality_gap", "freshness_gap",
    "clinical_utility_gap", "model_specification_gap",
    "distribution_shift_gap", "individual_population_gap",
    "blast_radius_gap", "authority_gap", "reason_traceability_gap",
]


def _epic_standard_chain():
    """5-level Epic chain matching the paper hierarchy."""
    return {
        "REF": {},
        "DIA": {},  # in the paper, DIA has no reqs (structural floor)
        "REV": {"approximation_quality_gap": "bounded"},
        "AEX": {"approximation_quality_gap": "bounded",
                "freshness_gap": "bounded"},
        "ALR": {g: "bounded" for g in _EPIC_GAPS},
    }


def _epic_B1_empty_chain():
    """6-level chain: ROL between REF and DIA, ROL's reqs = DIA's reqs.
    Empty-chain extension: ROL should be inert (compiler never emits ROL
    that it wouldn't have emitted DIA, but the order means ROL ≺ DIA in
    the underlying lattice, so satisfying both = emit DIA)."""
    return {
        "REF": {},
        "ROL": {},  # same as DIA's reqs (both empty)
        "DIA": {},
        "REV": {"approximation_quality_gap": "bounded"},
        "AEX": {"approximation_quality_gap": "bounded",
                "freshness_gap": "bounded"},
        "ALR": {g: "bounded" for g in _EPIC_GAPS},
    }


def _epic_B2_refined_chain():
    """6-level chain: ROL refines the gap between DIA and REV.
    ROL requires approximation_quality_gap to be 'open' (vacuous — same as DIA)
    but adds freshness ≥ bounded. Wait — that crosses REV's domain.

    Better refinement: split the AEX requirement.
      AEX in paper requires: AQ bounded + freshness bounded.
      New intermediate level (place ROL above REV but below AEX): require
      AQ bounded only (same as REV). That makes ROL = REV in behavior.
    The only useful place to refine is to split a multi-gap requirement
    across two levels.

    Concrete refinement: split AEX into ROL-AEX where ROL requires AQ bounded
    + freshness 'open' (vacuous), and AEX requires AQ bounded + freshness
    bounded. ROL is then equivalent to REV.

    The cleanest refined interpolation in Epic: take ALR's 9-gap conjunction
    and split it. Add a new level "ALR-partial" that requires AQ + freshness
    + clinical_utility bounded (3 of 9). Place it between AEX and ALR.
    Underlying alphabet doesn't have a slot between AEX and ALR... actually
    it doesn't. AEX < ALR are adjacent in the canonical chain.

    So I'll add ROL between REF and DIA with a non-vacuous requirement
    (the freshness gap bounded), demonstrating: an intermediate level only
    fires when its specific requirement is met but DIA's (empty) is not — but
    DIA's is always met. So ROL can only fire if I also strengthen DIA. I
    therefore strengthen DIA to also require freshness bounded, and place
    ROL with no requirements as the "ROL only" level — but ROL ≺ DIA, so
    ROL fires when DIA's strengthened reqs fail.

    Final design:
      REF: {}
      ROL: {}                                              # empty reqs
      DIA: {freshness_gap: 'bounded'}                       # NEW DIA req
      REV: {AQ: 'bounded'}
      AEX: {AQ: 'bounded', freshness: 'bounded'}
      ALR: full 9-gap

    Then: a case with freshness open + AQ open emits ROL (not DIA).
          A case with freshness bounded + AQ open emits DIA.
          A case with AQ bounded + freshness open emits REV (passes AQ but
            DIA's freshness requirement fails because DIA needs freshness bounded
            … and AEX needs both).
    """
    return {
        "REF": {},
        "ROL": {},                                                  # empty reqs (always satisfied)
        "DIA": {"freshness_gap": "bounded"},                        # strengthened DIA
        "REV": {"approximation_quality_gap": "bounded"},
        "AEX": {"approximation_quality_gap": "bounded",
                "freshness_gap": "bounded"},
        "ALR": {g: "bounded" for g in _EPIC_GAPS},
    }


def _epic_test_cases():
    """A spectrum of Epic evidence states from S-REF up through S-ALR."""
    all_bounded = {g: "bounded" for g in _EPIC_GAPS}
    return [
        ("all_open", {g: "open" for g in _EPIC_GAPS}),
        ("freshness_bounded_only",
         {**{g: "open" for g in _EPIC_GAPS}, "freshness_gap": "bounded"}),
        ("AQ_bounded_only",
         {**{g: "open" for g in _EPIC_GAPS}, "approximation_quality_gap": "bounded"}),
        ("AQ_and_freshness",
         {**{g: "open" for g in _EPIC_GAPS},
          "approximation_quality_gap": "bounded", "freshness_gap": "bounded"}),
        ("all_bounded", all_bounded),
    ]


def run_epic_chain_probe() -> list[dict]:
    rows = []
    cases = _epic_test_cases()
    for case_name, statuses in cases:
        for chain_name, chain_fn in [
            ("standard_5lvl", _epic_standard_chain),
            ("B1_empty_6lvl", _epic_B1_empty_chain),
            ("B2_refined_6lvl", _epic_B2_refined_chain),
        ]:
            emit = _compile_with_chain(statuses, chain_fn(), f"epic-{chain_name}-{case_name}")
            rows.append({
                "domain": "epic", "case": case_name, "chain": chain_name,
                "chain_length": len(chain_fn()),
                "emit": emit,
                "emit_rank": _PERM_RANK[emit],
            })
    return rows


# ── Driver ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 100)
    print(" k-probe across paper domains")
    print(" Part A — continuous-axis saturation (turbo, ising, faa)")
    print(" Part B — categorical chain-length probe (ils, epic)")
    print("=" * 100)

    # Part A
    print("\n— Part A: continuous-axis k saturation —")
    print(f"  k grid: {K_LEVELS_EXTENDED}")

    turbo = run_turbo_kprobe()
    ising = run_ising_kprobe()
    faa = run_faa_kprobe()

    a_summary = {}
    for name, dat in [("turbo", turbo), ("ising", ising), ("faa", faa)]:
        bps = dat["breakpoints_by_k"]
        k_star = _detect_saturation_k_star(bps)
        growth = _detect_growth_rate(bps)
        a_summary[name] = {
            "breakpoints_by_k": bps,
            "k_star_saturation": k_star,
            "saturation_observed": k_star is not None,
            "growth_fit": growth,
        }
        if name == "ising":
            a_summary[name]["location_error_by_k"] = ising["location_error_by_k"]

    print(f"\n  Turbo bps by k:  {turbo['breakpoints_by_k']}")
    print(f"     -> k* saturation: {a_summary['turbo']['k_star_saturation']}")
    print(f"     -> linear fit R^2={a_summary['turbo']['growth_fit']['linear_r2']:.4f}, "
          f"log2 fit R^2={a_summary['turbo']['growth_fit']['log2_r2']:.4f}, "
          f"log2 slope={a_summary['turbo']['growth_fit']['slope_log2']:.3f}")
    print(f"\n  Ising bps by k:  {ising['breakpoints_by_k']}")
    print(f"     -> k* saturation: {a_summary['ising']['k_star_saturation']}")
    print(f"     -> Location error final: {min(ising['location_error_by_k'].values()):.6f}")
    print(f"\n  FAA bps by k:    {faa['breakpoints_by_k']}")
    print(f"     -> k* saturation: {a_summary['faa']['k_star_saturation']}")
    print(f"     -> linear fit R^2={a_summary['faa']['growth_fit']['linear_r2']:.4f}, "
          f"linear slope={a_summary['faa']['growth_fit']['slope_linear']:.3f}")

    # Write part A CSV
    all_A_rows = turbo["rows"] + ising["rows"] + faa["rows"]
    # union of keys
    keyset = set()
    for r in all_A_rows:
        keyset.update(r.keys())
    fields = ["domain", "k", "n_axis_points", "breakpoints",
              "step_tau", "location_error", "grid_spacing", "err_over_spacing"]
    with open(RESULTS_DIR / "k_probe_A_continuous.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in all_A_rows:
            full = {k: r.get(k, "") for k in fields}
            writer.writerow(full)

    with open(RESULTS_DIR / "k_probe_A_summary.json", "w") as f:
        json.dump(a_summary, f, indent=2)

    # Part B
    print("\n— Part B: categorical chain-length probe —")
    ils_rows = run_ils_chain_probe()
    epic_rows = run_epic_chain_probe()

    print("\n  ILS chain probe (4-level standard vs 5-level B1 empty vs 5-level B2 refined):")
    print(f"  {'case':>14}  {'chain':>20}  {'len':>3}  {'emit':>5}")
    for r in ils_rows:
        print(f"  {r['case']:>14}  {r['chain']:>20}  {r['chain_length']:>3}  {r['emit']:>5}")

    print("\n  Epic chain probe (5-level standard vs 6-level B1 empty vs 6-level B2 refined):")
    print(f"  {'case':>26}  {'chain':>20}  {'len':>3}  {'emit':>5}")
    for r in epic_rows:
        print(f"  {r['case']:>26}  {r['chain']:>20}  {r['chain_length']:>3}  {r['emit']:>5}")

    # Write part B CSV
    all_B_rows = ils_rows + epic_rows
    fields_B = ["domain", "case", "chain", "chain_length", "emit", "emit_rank"]
    with open(RESULTS_DIR / "k_probe_B_categorical.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_B)
        writer.writeheader()
        writer.writerows(all_B_rows)

    # Part B summary: chain effect
    print("\n— Chain-length effect summary —")
    from collections import defaultdict
    for domain in ["ils", "epic"]:
        d_rows = [r for r in all_B_rows if r["domain"] == domain]
        cases = sorted({r["case"] for r in d_rows})
        chains = sorted({r["chain"] for r in d_rows})
        # Per chain, count distinct emits
        per_chain = {}
        for c in chains:
            sub = [r for r in d_rows if r["chain"] == c]
            emits = [r["emit"] for r in sub]
            per_chain[c] = {
                "n_cases": len(sub),
                "distinct_emits": sorted(set(emits), key=lambda p: _PERM_RANK[p]),
                "n_distinct_emits": len(set(emits)),
            }
        # Compare standard vs B1 vs B2
        std_emits = [r["emit"] for r in d_rows if "standard" in r["chain"]]
        b1_emits = [r["emit"] for r in d_rows if "B1" in r["chain"]]
        b2_emits = [r["emit"] for r in d_rows if "B2" in r["chain"]]
        # Pair each case across chains
        std_by_case = {r["case"]: r["emit"] for r in d_rows if "standard" in r["chain"]}
        b1_by_case = {r["case"]: r["emit"] for r in d_rows if "B1" in r["chain"]}
        b2_by_case = {r["case"]: r["emit"] for r in d_rows if "B2" in r["chain"]}
        b1_same_as_std = sum(1 for c in cases if std_by_case[c] == b1_by_case[c])
        b2_same_as_std = sum(1 for c in cases if std_by_case[c] == b2_by_case[c])
        b2_uses_new_lvl = sum(1 for c in cases if b2_by_case[c] == "ROL")
        print(f"  {domain}: {len(cases)} cases, chains tested: {chains}")
        for c, d in per_chain.items():
            print(f"     {c}: distinct emits = {d['distinct_emits']}")
        print(f"     B1 (empty) matches standard on {b1_same_as_std}/{len(cases)} cases")
        print(f"     B2 (refined) matches standard on {b2_same_as_std}/{len(cases)} cases")
        print(f"     B2 emits the NEW level (ROL) on {b2_uses_new_lvl}/{len(cases)} cases")

    print("\n  Wrote: results/k_probe_A_continuous.csv")
    print("         results/k_probe_A_summary.json")
    print("         results/k_probe_B_categorical.csv")


if __name__ == "__main__":
    main()
