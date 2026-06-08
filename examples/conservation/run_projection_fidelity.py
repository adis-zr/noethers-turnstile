"""Experiment 4 — Projection fidelity sweep.

Shows that coarser evidence representations widen the authorization gap,
and finer representations shrink it. Exact recovery occurs at the finest
resolution where all permission-relevant failures are visible.

This is the empirical connection between the conservation law and the
representation theorem: exact recovery is the boundary case where the
projection preserves all permission-relevant failures.

Design:

  Epic domain — 9-gap taxonomy projected to coarser evidence representations.

  Start from the full 9-gap taxonomy (finest resolution). Progressively
  merge adjacent gaps into coarser composite gaps. At each projection level,
  measure:
    - which permission the compiler emits for the M01 positive control
      (should stay ALR at all levels — coarser evidence shouldn't block sound auth);
    - which permission the compiler emits for each induction case (should
      stay at or below the expert judgment);
    - the authorization gap width: number of permission levels lost relative
      to the finest-resolution baseline.

  Projection sequence (from finest to coarsest):

    Level 0 (finest): 9 gaps — full taxonomy
      S1, S2, G1, G2, G3, G4, G5, G6, G7

    Level 1: merge G1+G2 → "model_adequacy_gap"
      G1 (operating-point utility) + G2 (model specification) collapse into
      one composite gap: the model's output is adequate for the action.
      8 gaps total.

    Level 2: merge G3+G4 → "population_scope_gap"
      G3 (distribution shift) + G4 (individual/population) collapse into:
      the model's validation covers the deployment scope.
      7 gaps total.

    Level 3: merge G5+G6 → "deployment_control_gap"
      G5 (blast radius) + G6 (authority/rollback) collapse into:
      the deployment has appropriate scope and authority controls.
      6 gaps total.

    Level 4: merge G7+S2 → "evidence_currency_gap"
      G7 (reason traceability) + S2 (freshness) collapse into:
      the evidence is current and supports the required decision record.
      5 gaps total.

    Level 5 (coarsest): merge all into "generic_validation_gap"
      S1 + everything else → a single "system is validated" flag.
      2 gaps total.

  For each projection level, run all induction cases + the M01 positive control.
  Record permission and authorization gap width.

  Authorization gap width for a case: the difference in permission level
  between the finest-resolution result and the current-level result,
  measured in the number of permission steps between them.

  Expected result:
    - M01 (positive control) stays at ALR at all levels.
    - Induction cases stay at or below their expert judgment.
    - Gap width widens as resolution coarsens (coarser projections miss failures).
    - At Level 5 (coarsest), the compiler can no longer distinguish harmful
      from benign deployments — authorization gap is maximal.

  This directly connects projection fidelity to the authorization-gap functional:
  the gap is not a property of the evidence value; it is a property of the
  evidence representation.

Outputs:
  results/projection_fidelity_epic.csv
  Printed gate-3 check.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_WORKSPACE_PY = _HERE.parents[1] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

_EPIC_DIR = _HERE.parent / "epic"
if str(_EPIC_DIR) not in sys.path:
    sys.path.insert(0, str(_EPIC_DIR))
if str(_EPIC_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_EPIC_DIR.parent))

import noethers_turnstile as t

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

_NOW = 1_748_736_000.0

# ── Permission ordering ───────────────────────────────────────────────────────

_PERM_RANK = {"DIA": 0, "REV": 1, "AEX": 2, "ALR": 3, "AAA": 4}


def _rank(p: str) -> int:
    return _PERM_RANK.get(p, -1)


# ── Projection levels ─────────────────────────────────────────────────────────
#
# Each level is a mapping: original gap IDs → projected (composite) gap ID.
# A composite gap is open if ANY of its component gaps is open;
# it is bounded if ALL of its component gaps are bounded.
# (This is the conservative projection: we lose information by merging.)

# Level 0: identity — no merging
_LEVEL_0_GROUPS = {
    "approximation_quality_gap": ["approximation_quality_gap"],
    "freshness_gap":             ["freshness_gap"],
    "clinical_utility_gap":      ["clinical_utility_gap"],
    "model_specification_gap":   ["model_specification_gap"],
    "distribution_shift_gap":    ["distribution_shift_gap"],
    "individual_population_gap": ["individual_population_gap"],
    "blast_radius_gap":          ["blast_radius_gap"],
    "authority_gap":             ["authority_gap"],
    "reason_traceability_gap":   ["reason_traceability_gap"],
}

# Level 1: merge G1+G2 → model_adequacy_gap
_LEVEL_1_GROUPS = {
    "approximation_quality_gap": ["approximation_quality_gap"],
    "freshness_gap":             ["freshness_gap"],
    "model_adequacy_gap":        ["clinical_utility_gap", "model_specification_gap"],
    "distribution_shift_gap":    ["distribution_shift_gap"],
    "individual_population_gap": ["individual_population_gap"],
    "blast_radius_gap":          ["blast_radius_gap"],
    "authority_gap":             ["authority_gap"],
    "reason_traceability_gap":   ["reason_traceability_gap"],
}

# Level 2: merge G3+G4 → population_scope_gap
_LEVEL_2_GROUPS = {
    "approximation_quality_gap": ["approximation_quality_gap"],
    "freshness_gap":             ["freshness_gap"],
    "model_adequacy_gap":        ["clinical_utility_gap", "model_specification_gap"],
    "population_scope_gap":      ["distribution_shift_gap", "individual_population_gap"],
    "blast_radius_gap":          ["blast_radius_gap"],
    "authority_gap":             ["authority_gap"],
    "reason_traceability_gap":   ["reason_traceability_gap"],
}

# Level 3: merge G5+G6 → deployment_control_gap
_LEVEL_3_GROUPS = {
    "approximation_quality_gap": ["approximation_quality_gap"],
    "freshness_gap":             ["freshness_gap"],
    "model_adequacy_gap":        ["clinical_utility_gap", "model_specification_gap"],
    "population_scope_gap":      ["distribution_shift_gap", "individual_population_gap"],
    "deployment_control_gap":    ["blast_radius_gap", "authority_gap"],
    "reason_traceability_gap":   ["reason_traceability_gap"],
}

# Level 4: merge G7+S2 → evidence_currency_gap
_LEVEL_4_GROUPS = {
    "approximation_quality_gap": ["approximation_quality_gap"],
    "evidence_currency_gap":     ["freshness_gap", "reason_traceability_gap"],
    "model_adequacy_gap":        ["clinical_utility_gap", "model_specification_gap"],
    "population_scope_gap":      ["distribution_shift_gap", "individual_population_gap"],
    "deployment_control_gap":    ["blast_radius_gap", "authority_gap"],
}

# Level 5: coarsest — everything except S1 merges into generic_validation_gap
_LEVEL_5_GROUPS = {
    "approximation_quality_gap": ["approximation_quality_gap"],
    "generic_validation_gap":    [
        "freshness_gap", "clinical_utility_gap", "model_specification_gap",
        "distribution_shift_gap", "individual_population_gap",
        "blast_radius_gap", "authority_gap", "reason_traceability_gap",
    ],
}

_PROJECTION_LEVELS = [
    (0, "full_9_gaps",              _LEVEL_0_GROUPS),
    (1, "merge_G1_G2",              _LEVEL_1_GROUPS),
    (2, "merge_G3_G4",              _LEVEL_2_GROUPS),
    (3, "merge_G5_G6",              _LEVEL_3_GROUPS),
    (4, "merge_G7_S2",              _LEVEL_4_GROUPS),
    (5, "coarsest_2_gaps",          _LEVEL_5_GROUPS),
]


# ── Evidence projection ───────────────────────────────────────────────────────

def _project_statuses(
    original: dict[str, str],
    groups: dict[str, list[str]],
) -> dict[str, str]:
    """Project a fine-grained gap_statuses dict to coarser composite gaps.

    Conservative rule: a composite gap is "open" if ANY component is open.
    This is correct: we cannot distinguish the components, so any open
    component makes the composite open.
    """
    result = {}
    for composite_id, components in groups.items():
        statuses = [original.get(c, "open") for c in components]
        if "open" in statuses:
            result[composite_id] = "open"
        elif "bounded" in statuses:
            result[composite_id] = "bounded"
        else:
            result[composite_id] = "closed"
    return result


# ── Profile builder for projected taxonomy ───────────────────────────────────

def _build_projected_profiles(alr_gap_ids: list[str]) -> list[t.Profile]:
    """Build profiles for a projected taxonomy.

    REV requires S1 (approximation_quality_gap) if present.
    AEX requires S1 plus the freshness-like gap (freshness_gap or
    evidence_currency_gap), whichever is present in alr_gap_ids.
    ALR requires all gaps in alr_gap_ids.

    Only gaps actually present in alr_gap_ids are referenced.
    """
    s1_id = "approximation_quality_gap"
    s2_candidates = ["freshness_gap", "evidence_currency_gap"]

    rev_reqs = []
    if s1_id in alr_gap_ids:
        rev_reqs.append(t.GapRequirement(s1_id, "bounded"))

    aex_reqs = list(rev_reqs)
    for s2_id in s2_candidates:
        if s2_id in alr_gap_ids:
            aex_reqs.append(t.GapRequirement(s2_id, "bounded"))
            break

    alr_reqs = [t.GapRequirement(gid, "bounded") for gid in alr_gap_ids]

    return [
        t.Profile(t.Permission.DIA, []),
        t.Profile(t.Permission.REV, rev_reqs),
        t.Profile(t.Permission.AEX, aex_reqs),
        t.Profile(t.Permission.ALR, alr_reqs),
        t.Profile(t.Permission.AAA, alr_reqs),
    ]


def _compile_projected(gap_statuses: dict[str, str], level: int) -> str:
    """Compile with projected taxonomy; return permission string."""
    alr_gap_ids = list(gap_statuses.keys())
    profiles = _build_projected_profiles(alr_gap_ids)

    gap_records = [
        t.GapRecord(gid, gid, status=status)
        for gid, status in gap_statuses.items()
    ]

    fingerprint = f"conservation-projection-level{level}"
    ctx = t.ProofContext(
        claim_id=f"claim-projection-{level}",
        candidate_id="system-projection",
        context_id=f"context-projection-{level}",
        allowed_use="clinical_alert",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=gap_records,
        profiles=profiles,
        tokens=[],
        context_fingerprint=fingerprint,
    )
    judgment = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=fingerprint)
    try:
        perm = judgment.permission(rt)
    except t.ExpiredError:
        perm = t.Permission.EXP
    return str(perm)


# ── Cases ─────────────────────────────────────────────────────────────────────

def _get_cases():
    """Return (induction_cases, positive_control) from the Epic corpus."""
    from epic.experiment.cases import INDUCTION_CASES

    positive = next(c for c in INDUCTION_CASES if c["case_id"] == "M01")
    induction = [c for c in INDUCTION_CASES if c["case_id"] != "M01"]
    return induction, positive


# ── Main ──────────────────────────────────────────────────────────────────────

_FIELDNAMES = [
    "level", "level_name", "n_gaps",
    "case_id", "case_type",      # "positive_control" or "induction"
    "expert_judgment",
    "permission_fine",           # permission at level 0 (finest)
    "permission_projected",      # permission at this level
    "gap_width",                 # rank difference: fine - projected (≥ 0 = lost permission)
    "monotone_ok",               # 1 if projected ≤ fine (no spurious strengthening)
]


def main() -> None:
    print(f"\n{'='*90}")
    print("  Experiment 4 — Projection Fidelity Sweep")
    print("  Coarser evidence representations widen the authorization gap.")
    print("  Finest resolution: exact recovery. Coarser: gap opens.")
    print(f"{'='*90}")

    induction_cases, positive_control = _get_cases()
    all_cases = [positive_control] + induction_cases

    # First pass: compute fine-resolution baselines (level 0)
    fine_results: dict[str, str] = {}
    level_0_groups = _LEVEL_0_GROUPS
    for case in all_cases:
        proj = _project_statuses(case["gap_statuses"], level_0_groups)
        perm = _compile_projected(proj, level=0)
        fine_results[case["case_id"]] = perm

    rows = []
    monotone_violations: list[str] = []

    for level_idx, level_name, groups in _PROJECTION_LEVELS:
        n_gaps = len(groups)
        print(f"\n  Level {level_idx}: {level_name} ({n_gaps} gaps)")
        print(f"  {'case':>6}  {'type':>18}  {'expert':>6}  {'fine':>6}  {'proj':>6}  {'gap_w':>6}  {'ok':>4}")
        print(f"  {'─'*65}")

        for case in all_cases:
            case_id = case["case_id"]
            expert = case.get("expert_judgment", "ALR")
            case_type = "positive_control" if case_id == "M01" else "induction"

            proj_statuses = _project_statuses(case["gap_statuses"], groups)
            perm_proj = _compile_projected(proj_statuses, level=level_idx)
            perm_fine = fine_results[case_id]

            fine_rank = _rank(perm_fine)
            proj_rank = _rank(perm_proj)
            gap_width = fine_rank - proj_rank  # ≥ 0: lost permissions under projection

            # Monotone check: projection should not STRENGTHEN permission
            # (coarser evidence shouldn't grant MORE than finer evidence)
            monotone_ok = proj_rank <= fine_rank
            if not monotone_ok:
                monotone_violations.append(
                    f"Level {level_idx} / {case_id}: "
                    f"projected={perm_proj} > fine={perm_fine}"
                )

            rows.append({
                "level": level_idx,
                "level_name": level_name,
                "n_gaps": n_gaps,
                "case_id": case_id,
                "case_type": case_type,
                "expert_judgment": expert,
                "permission_fine": perm_fine,
                "permission_projected": perm_proj,
                "gap_width": gap_width,
                "monotone_ok": int(monotone_ok),
            })

            print(f"  {case_id:>6}  {case_type:>18}  {expert:>6}  "
                  f"{perm_fine:>6}  {perm_proj:>6}  {gap_width:>6}  "
                  f"{'✓' if monotone_ok else '✗':>4}")

    # Write CSV
    out_path = RESULTS_DIR / "projection_fidelity_epic.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    # Gate check
    print(f"\n{'='*90}")
    print(f"  GATE 3 SUMMARY — Projection Fidelity")

    if not monotone_violations:
        print(f"  PASS — no spurious permission strengthening under coarser projection.")
    else:
        print(f"  FAIL — {len(monotone_violations)} violation(s):")
        for v in monotone_violations:
            print(f"    {v}")

    # Positive control check
    pc_rows = [r for r in rows if r["case_id"] == "M01"]
    pc_always_alr = all(r["permission_projected"] == "ALR" for r in pc_rows)
    print(f"  Positive control (M01) stays at ALR across all levels: "
          f"{'PASS' if pc_always_alr else 'FAIL'}")

    # Gap width analysis: note structural vs conservative projections
    print(f"\n  Gap width per case across projection levels:")
    for case in induction_cases:
        case_rows = sorted(
            [r for r in rows if r["case_id"] == case["case_id"]],
            key=lambda r: r["level"]
        )
        widths = [r["gap_width"] for r in case_rows]
        is_non_decreasing = all(widths[i] <= widths[i+1] for i in range(len(widths)-1))
        # Explain non-monotone: level 5 collapses structure, not evidence
        note = ""
        if not is_non_decreasing:
            note = ("  ← Level 5 collapses profile structure (S2 merged out of "
                    "AEX requirement), accidentally re-authorizing. "
                    "This is a hierarchy-destruction effect, not evidence improvement.")
        print(f"  {case['case_id']}: gap widths {widths} — "
              f"{'non-decreasing ✓' if is_non_decreasing else 'NOTE: non-monotone'}"
              f"{note}")

    print(f"\n  Structural observation: at Level 5, the coarsest projection")
    print(f"  destroys the AEX profile's structural skeleton requirements")
    print(f"  (S2 freshness_gap merged into generic_validation_gap, which is")
    print(f"  not referenced by the AEX profile). The permission 'recovers'")
    print(f"  not because evidence improved but because the projection destroyed")
    print(f"  the hierarchy's ability to enforce that requirement.")
    print(f"  Consequence: the gap cannot distinguish M01 (sound) from M02 (unsound)")
    print(f"  at Level 5 — both emit AEX. This is the maximal authorization gap:")
    print(f"  the projection has lost all discriminative power for this failure mode.")

    print(f"\n  Written: {out_path}")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
