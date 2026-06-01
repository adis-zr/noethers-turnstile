"""MED-001 Profile Comparison: V1 vs V2 vs V3.

Runs the same oracle cases under all three profiles and prints a side-by-side
comparison table. Shows where V1 fails, where V2 corrects it, and where V3
adds further requirements derived from FDA+NHS strict standards.

Profile sources:
  V1: naive deployment profile (AUC + calibration only)
  V2: corrected profile (adds clinical_utility + distribution_shift)
  V3: FDA+NHS strict profile (adds shadow_mode_validation + post_market_monitoring)
      Sources: NHS RCR AI Deployment Fundamentals 2024 §4.21-4.22, §2.13
               FDA Draft Guidance Jan 2025 Appendix C, §XI

Run:
  python3.10 run_profile_comparison.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noethers_turnstile as t
from acs.compiler import compile_context

from adapter.proof_context import (
    CaseInputs, build_proof_context,
    GAP_APPROXIMATION_QUALITY, GAP_MODEL_SPECIFICATION,
    GAP_CLINICAL_UTILITY, GAP_DISTRIBUTION_SHIFT,
    GAP_CALIBRATION, GAP_BLAST_RADIUS, GAP_FRESHNESS,
    GAP_SHADOW_MODE_VALIDATION, GAP_POST_MARKET_MONITORING,
)

_CLAIM   = "claim-med001-comparison"
_CAND    = "candidate-comparison"
_CTX_A   = "context-med001|challenge2019_setA|v1"
_USE     = "clinical_alert"
_NOW     = 1_748_736_000.0


def _compile(gap_statuses: dict, profile: str, ctx: str = _CTX_A) -> t.Permission:
    inputs = CaseInputs(
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=ctx,
        allowed_use=_USE,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        gap_statuses=gap_statuses,
        profile_version=profile,
    )
    ctx_obj = build_proof_context(inputs)
    judgment = compile_context(ctx_obj)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=inputs.context_id)
    try:
        return judgment.permission(rt)
    except t.ExpiredError:
        return t.Permission.EXP


# ── Gap status bundles ────────────────────────────────────────────────────────

def _core_only() -> dict:
    """V1-satisfying: AUC + spec + cal + br + fr bounded. No utility, no shift, no v3 gaps."""
    return {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }


def _plus_utility_shift() -> dict:
    """V2-satisfying: adds clinical_utility + distribution_shift."""
    return {**_core_only(),
        GAP_CLINICAL_UTILITY:   "bounded",
        GAP_DISTRIBUTION_SHIFT: "bounded",
    }


def _fully_evidenced() -> dict:
    """V3-satisfying: adds shadow_mode_validation + post_market_monitoring."""
    return {**_plus_utility_shift(),
        GAP_SHADOW_MODE_VALIDATION: "bounded",
        GAP_POST_MARKET_MONITORING: "bounded",
    }


def _no_utility() -> dict:
    """clinical_utility open (the Epic failure pattern)."""
    return _core_only()


def _no_shadow() -> dict:
    """V2-satisfying but missing shadow mode (passes V2, fails V3)."""
    return _plus_utility_shift()


def _no_postmarket() -> dict:
    """Has shadow mode but no monitoring plan (passes V2, fails V3)."""
    return {**_plus_utility_shift(),
        GAP_SHADOW_MODE_VALIDATION: "bounded",
    }


# ── Cases ─────────────────────────────────────────────────────────────────────

CASES = [
    # id, description, gap_statuses
    ("P1",
     "Core evidence only (AUC+spec+cal+br+fr) — Epic pattern",
     _core_only()),
    ("P2",
     "Adds clinical_utility + distribution_shift — V2 complete",
     _plus_utility_shift()),
    ("P3",
     "Adds shadow_mode + post_market_monitoring — V3 complete",
     _fully_evidenced()),
    ("P4",
     "Missing clinical_utility only",
     {**_core_only(), GAP_DISTRIBUTION_SHIFT: "bounded",
      GAP_SHADOW_MODE_VALIDATION: "bounded", GAP_POST_MARKET_MONITORING: "bounded"}),
    ("P5",
     "Missing distribution_shift only",
     {**_core_only(), GAP_CLINICAL_UTILITY: "bounded",
      GAP_SHADOW_MODE_VALIDATION: "bounded", GAP_POST_MARKET_MONITORING: "bounded"}),
    ("P6",
     "Missing shadow_mode_validation only",
     {**_plus_utility_shift(), GAP_POST_MARKET_MONITORING: "bounded"}),
    ("P7",
     "Missing post_market_monitoring only",
     {**_plus_utility_shift(), GAP_SHADOW_MODE_VALIDATION: "bounded"}),
    ("P8",
     "Missing both V3 gaps (shadow + monitoring) — V2 ceiling",
     _plus_utility_shift()),
]


def _perm_str(p: t.Permission) -> str:
    return str(p)


def _diff(v1: t.Permission, v2: t.Permission, v3: t.Permission) -> str:
    parts = []
    if v1 != v2:
        parts.append(f"v1→v2: {v1}→{v2}")
    if v2 != v3:
        parts.append(f"v2→v3: {v2}→{v3}")
    return "; ".join(parts) if parts else "—"


def main() -> None:
    print("MED-001 Profile Comparison: V1 vs V2 vs V3")
    print("=" * 90)
    print(f"\nProfile sources:")
    print(f"  V1: Naive — AUC + model spec + calibration + blast radius + freshness")
    print(f"  V2: Corrected — adds clinical_utility_gap + distribution_shift_gap")
    print(f"      (encodes what Wong et al. 2021 shows was missing from Epic deployment)")
    print(f"  V3: FDA+NHS strict — adds shadow_mode_validation_gap + post_market_monitoring_gap")
    print(f"      (NHS RCR AI Deployment Fundamentals 2024 §4.21-4.22, §2.13;")
    print(f"       FDA Draft Guidance Jan 2025 Appendix C, §XI)")
    print()

    col_w = 7
    desc_w = 52
    header = f"{'ID':<4} {'Description':<{desc_w}} {'V1':^{col_w}} {'V2':^{col_w}} {'V3':^{col_w}}  Changes"
    print(header)
    print("-" * len(header))

    for case_id, desc, statuses in CASES:
        v1 = _compile(statuses, "v1")
        v2 = _compile(statuses, "v2")
        v3 = _compile(statuses, "v3")
        diff = _diff(v1, v2, v3)
        print(f"{case_id:<4} {desc:<{desc_w}} {_perm_str(v1):^{col_w}} {_perm_str(v2):^{col_w}} {_perm_str(v3):^{col_w}}  {diff}")

    print()
    print("Key observations:")
    print()

    # Compute the headline numbers
    epic_v1 = _compile(_core_only(), "v1")
    epic_v2 = _compile(_core_only(), "v2")
    epic_v3 = _compile(_core_only(), "v3")
    full_v1 = _compile(_fully_evidenced(), "v1")
    full_v2 = _compile(_fully_evidenced(), "v2")
    full_v3 = _compile(_fully_evidenced(), "v3")
    shadow_missing_v2 = _compile(_plus_utility_shift(), "v2")
    shadow_missing_v3 = _compile(_plus_utility_shift(), "v3")

    print(f"  Epic pattern (core evidence only):")
    print(f"    V1: {epic_v1} — authorizes rollout  ← the documented harm")
    print(f"    V2: {epic_v2} — refuses rollout  ← clinical utility required")
    print(f"    V3: {epic_v3} — refuses rollout  ← same refusal, plus two more gaps open")
    print()
    print(f"  Fully evidenced (all gaps bounded):")
    print(f"    V1: {full_v1}")
    print(f"    V2: {full_v2}")
    print(f"    V3: {full_v3}  ← V3 does not over-refuse when evidence is complete")
    print()
    print(f"  V2-complete but missing V3 gaps (no shadow mode, no monitoring plan):")
    print(f"    V2: {shadow_missing_v2} — authorizes rollout")
    print(f"    V3: {shadow_missing_v3} — refuses rollout  ← NHS/FDA deployment phase required")
    print()
    print("Regulatory basis for V3 additions:")
    print("  shadow_mode_validation_gap:")
    print("    NHS RCR AI Deployment Fundamentals (2024) §4.21:")
    print("    'Evaluate AI in shadow mode as a standard deployment model for AI.'")
    print("    §4.22: enriched local population test required before go-live.")
    print("  post_market_monitoring_gap:")
    print("    NHS RCR §2.13: 'Ongoing post-implementation evaluation is essential")
    print("    and requires a robust plan prior to deployment.'")
    print("    FDA Draft Guidance Jan 2025 §XI: monitoring plan may be condition")
    print("    of approval for De Novo / PMA devices.")
    print()
    print("Note on V2 completeness:")
    print("  V2 encodes the pre-clearance evidence standard (FDA Appendix C) plus")
    print("  the distribution-shift obligation. It does not encode the deployment-phase")
    print("  obligations (shadow mode, monitoring plan) that NHS RCR treats as minimum")
    print("  standards for any hospital deploying a cleared AI tool. V3 fills that gap.")


if __name__ == "__main__":
    main()
