"""Experiment 6 v2 — Two-axis joint convergence (Theorem 4), full matrix.

This is the strengthened version of run_two_axis_convergence.py. The v1
implementation demonstrated joint convergence on two Epic cases (M01, M02).
v2 addresses five gaps identified in review:

  (1) Run all available induction + held-out cases and add a synthetic
      level-ladder (S-REF, S-DIA, S-REV, S-AEX, S-ALR) so the experiment
      covers every reachable permission level.
  (2) Add an active-refinement control: synthetic witness cases (W-currency,
      W-deployment, W-population, W-clinical) in which later splits actively
      shift permission. Inertness on the Epic cases then reads as "no
      remaining active blocker", not "refinement path stopped carrying signal".
  (3) Report the full (path × case × m × n) matrix with per-cell soundness
      and per-axis monotonicity.
  (4) Make the non-resolving (L5) failure global: list every case × k where
      the L5 collapse over-authorizes A(e), then show that monotonicity in m
      breaks exactly when the admissible skeleton is restored.

Semantics

  Composite status (already conservative in v1):
    composite_status = meet of component statuses
      (open ≺ bounded ≺ closed)
    A composite is "open" if any component is open, "closed" only if all
    components are closed, and "bounded" otherwise.

  Composite requirement (NEW in v2):
    composite_requirement(level p) = join of component requirements at level p
      (i.e. the strictest minimum-status required by any component)
    A composite gap demands the strictest status any of its components
    would have demanded individually at that permission level.

  This pair preserves Theorem 2's conservative-coarsening guarantee:
    A^π(π(e)) ≼ A(e)  for every admissible projection π.
  Conservative on the status side; strictest-wins on the requirement side.

Paths

  Resolving:    L4 → L3 → L2 → L1 → L0   (admissible throughout)
  Non-resolving: L5 → L4 → L3 → L2 → L1 → L0   (L5 violates admissibility)

Outputs

  results/two_axis_convergence_v2_matrix.csv
    one row per (path, case, m, n) cell — the full matrix.

  results/two_axis_convergence_v2_summary.csv
    one row per (path, case) — aggregate gate counts and joint-convergence flag.

  results/two_axis_convergence_v2_admissibility.csv
    one row per (path, case, m, k) cell where soundness fails — the global
    over-authorization witness for the L5 collapse.

  Printed:
    - per-case matrix table for representative cases
    - active-refinement witness verification table
    - admissibility violation summary
    - resolving / non-resolving gate summary
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

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

# F4: compile against the paper's 5-level chain (REF < DIA < REV < AEX < ALR),
# not the default 12-level chain. The chain object is canonical for this
# experiment and is what gets stamped into every Judgment.chain_hash.
from chain import CONSERVATION_CHAIN  # noqa: E402

_COMPILE_CHAIN = CONSERVATION_CHAIN

# Cached permission lookups in the conservation chain.
_PERM_REF = _COMPILE_CHAIN.parse("REF")
_PERM_DIA = _COMPILE_CHAIN.parse("DIA")
_PERM_REV = _COMPILE_CHAIN.parse("REV")
_PERM_AEX = _COMPILE_CHAIN.parse("AEX")
_PERM_ALR = _COMPILE_CHAIN.parse("ALR")

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

_NOW = 1_748_736_000.0

# ── Permission alphabet ───────────────────────────────────────────────────────

_PERM_TO_RANK = {"REF": 0, "DIA": 1, "REV": 2, "AEX": 3, "ALR": 4}
_RANK_TO_PERM = {v: k for k, v in _PERM_TO_RANK.items()}
_MAX_RANK = 4


def _rank(p: str) -> int:
    return _PERM_TO_RANK.get(p, 0)


def _norm(p: str) -> float:
    return _rank(p) / _MAX_RANK


# ── Gap-status lattice (for conservative composite status) ────────────────────

_STATUS_RANK = {"open": 0, "bounded": 1, "closed": 2}
_RANK_STATUS = {v: k for k, v in _STATUS_RANK.items()}


def _status_meet(statuses: Iterable[str]) -> str:
    """Conservative meet: composite open if any open, closed only if all closed."""
    return _RANK_STATUS[min(_STATUS_RANK[s] for s in statuses)]


def _status_join(statuses: Iterable[str]) -> str:
    """Strictest-wins for requirements: composite requirement = max."""
    return _RANK_STATUS[max(_STATUS_RANK[s] for s in statuses)]


# ── Projection levels ─────────────────────────────────────────────────────────
#
# Each level is a mapping: composite_id → list of fine gap ids it contains.
# L0 is identity (each fine gap is its own composite). L1–L4 progressively
# merge; L5 is the inadmissible collapse.

_LEVEL_0_GROUPS = {
    "approximation_quality_gap":   ["approximation_quality_gap"],
    "freshness_gap":               ["freshness_gap"],
    "clinical_utility_gap":        ["clinical_utility_gap"],
    "model_specification_gap":     ["model_specification_gap"],
    "distribution_shift_gap":      ["distribution_shift_gap"],
    "individual_population_gap":   ["individual_population_gap"],
    "blast_radius_gap":            ["blast_radius_gap"],
    "authority_gap":               ["authority_gap"],
    "reason_traceability_gap":     ["reason_traceability_gap"],
}

_LEVEL_1_GROUPS = {
    "approximation_quality_gap":   ["approximation_quality_gap"],
    "freshness_gap":               ["freshness_gap"],
    "model_adequacy_gap":          ["clinical_utility_gap", "model_specification_gap"],
    "distribution_shift_gap":      ["distribution_shift_gap"],
    "individual_population_gap":   ["individual_population_gap"],
    "blast_radius_gap":            ["blast_radius_gap"],
    "authority_gap":               ["authority_gap"],
    "reason_traceability_gap":     ["reason_traceability_gap"],
}

_LEVEL_2_GROUPS = {
    "approximation_quality_gap":   ["approximation_quality_gap"],
    "freshness_gap":               ["freshness_gap"],
    "model_adequacy_gap":          ["clinical_utility_gap", "model_specification_gap"],
    "population_scope_gap":        ["distribution_shift_gap", "individual_population_gap"],
    "blast_radius_gap":            ["blast_radius_gap"],
    "authority_gap":               ["authority_gap"],
    "reason_traceability_gap":     ["reason_traceability_gap"],
}

_LEVEL_3_GROUPS = {
    "approximation_quality_gap":   ["approximation_quality_gap"],
    "freshness_gap":               ["freshness_gap"],
    "model_adequacy_gap":          ["clinical_utility_gap", "model_specification_gap"],
    "population_scope_gap":        ["distribution_shift_gap", "individual_population_gap"],
    "deployment_control_gap":      ["blast_radius_gap", "authority_gap"],
    "reason_traceability_gap":     ["reason_traceability_gap"],
}

_LEVEL_4_GROUPS = {
    "approximation_quality_gap":   ["approximation_quality_gap"],
    "evidence_currency_gap":       ["freshness_gap", "reason_traceability_gap"],
    "model_adequacy_gap":          ["clinical_utility_gap", "model_specification_gap"],
    "population_scope_gap":        ["distribution_shift_gap", "individual_population_gap"],
    "deployment_control_gap":      ["blast_radius_gap", "authority_gap"],
}

_LEVEL_5_GROUPS = {
    "approximation_quality_gap":   ["approximation_quality_gap"],
    "generic_validation_gap": [
        "freshness_gap", "clinical_utility_gap", "model_specification_gap",
        "distribution_shift_gap", "individual_population_gap",
        "blast_radius_gap", "authority_gap", "reason_traceability_gap",
    ],
}

# Each path step is (level, name, groups, admissible). On admissible steps
# the projection profile is built with the join rule (Theorem 2 conservative).
# On non-admissible steps the projection profile is built with the v1-style
# flat-bounded shortcut, which violates Theorem 2 and produces the L5
# admissibility failure used as the non-resolving witness.

_RESOLVING_PATH = [
    (4, "L4_evidence_currency",  _LEVEL_4_GROUPS, True),
    (3, "L3_deployment_control", _LEVEL_3_GROUPS, True),
    (2, "L2_population_scope",   _LEVEL_2_GROUPS, True),
    (1, "L1_model_adequacy",     _LEVEL_1_GROUPS, True),
    (0, "L0_full_9_gaps",        _LEVEL_0_GROUPS, True),
]

_NONRESOLVING_PATH = [
    (5, "L5_collapsed_2_gaps_FLAT", _LEVEL_5_GROUPS, False),  # inadmissible: flat-bounded profile
    (4, "L4_evidence_currency",     _LEVEL_4_GROUPS, True),
    (3, "L3_deployment_control",    _LEVEL_3_GROUPS, True),
    (2, "L2_population_scope",      _LEVEL_2_GROUPS, True),
    (1, "L1_model_adequacy",        _LEVEL_1_GROUPS, True),
    (0, "L0_full_9_gaps",           _LEVEL_0_GROUPS, True),
]

K_LEVELS = [4, 8, 16, 32, 64]

# All fine gap ids that may appear in any case
_FINE_GAPS = [
    "approximation_quality_gap",
    "freshness_gap",
    "clinical_utility_gap",
    "model_specification_gap",
    "distribution_shift_gap",
    "individual_population_gap",
    "blast_radius_gap",
    "authority_gap",
    "reason_traceability_gap",
]


# ── Default fine-grained requirements ─────────────────────────────────────────
#
# Standard Epic profile (used for all cases that don't supply their own):
#   AEX requires AQ and freshness bounded.
#   ALR requires every fine gap bounded (uniform-bounded ALR).
#
# Witness cases (W-*) override the ALR requirements per-gap to install a
# strict "closed" demand on the targeted active blocker.

def _default_fine_reqs() -> dict[str, dict[str, str]]:
    """Default fine-grained per-(permission, gap) requirement table.

    Returns nested dict: reqs[permission_name][gap_id] = required_status.
    Only gaps actually present in the case need a requirement; missing entries
    are treated as 'no requirement' (vacuously satisfied).

    AAA mirrors ALR (separate dict copy) so callers may strengthen ALR
    without aliasing into AAA. AAA must be at least as strict as ALR or the
    compiler will satisfy AAA first and the authority ceiling will cap the
    result back to ALR — masking ALR's strict requirements.
    """
    aex_reqs = {
        "approximation_quality_gap": "bounded",
        "freshness_gap":             "bounded",
    }
    alr_reqs = {gid: "bounded" for gid in _FINE_GAPS}
    return {
        "DIA": {},
        "REV": {"approximation_quality_gap": "bounded"},
        "AEX": dict(aex_reqs),
        "ALR": dict(alr_reqs),
        "AAA": dict(alr_reqs),
    }


def _sync_aaa_to_alr(reqs: dict[str, dict[str, str]]) -> None:
    """Make AAA at least as strict as ALR. Mutates in place."""
    reqs["AAA"] = dict(reqs["ALR"])


# ── Evidence projection ───────────────────────────────────────────────────────

def _project_statuses(
    original: dict[str, str],
    groups: dict[str, list[str]],
) -> dict[str, str]:
    """Conservative status meet: composite open if any component open."""
    result = {}
    for composite_id, components in groups.items():
        statuses = [original.get(c, "open") for c in components]
        result[composite_id] = _status_meet(statuses)
    return result


def _project_requirements_join(
    fine_reqs: dict[str, dict[str, str]],
    groups: dict[str, list[str]],
) -> dict[str, dict[str, str]]:
    """Admissible projection: composite requirement = strictest of components.

    For each permission level, the projected requirement on composite C is the
    join (max) over the component requirements c ∈ C. If no component had a
    requirement at that level, the composite has no requirement either.

    This preserves Theorem 2's conservative coarsening guarantee.
    """
    projected: dict[str, dict[str, str]] = {}
    for perm_name, gap_to_req in fine_reqs.items():
        composite_reqs: dict[str, str] = {}
        for composite_id, components in groups.items():
            component_reqs = [
                gap_to_req[c] for c in components if c in gap_to_req
            ]
            if component_reqs:
                composite_reqs[composite_id] = _status_join(component_reqs)
        projected[perm_name] = composite_reqs
    return projected


def _project_requirements_skeleton_truncating(
    fine_reqs: dict[str, dict[str, str]],
    groups: dict[str, list[str]],
) -> dict[str, dict[str, str]]:
    """Inadmissible projection: skeleton-truncating (v1-style shortcut).

    This models the projection-profile builder used in v1 / projection-fidelity:
    when coarsening, the projection profile only carries requirements for
    composites whose *composite ID* is in a hard-coded "permission skeleton"
    list. Composites whose fine components were skeleton members but whose
    composite ID is not recognized are silently dropped from the projected
    profile.

    Concretely: AEX's S2 protection (freshness=bounded) is dropped when
    freshness is merged into a composite whose ID is not in
    {'freshness_gap', 'evidence_currency_gap'}. At L5, freshness is merged
    into 'generic_validation_gap', which is not a recognized S2 ID, so AEX's
    S2 protection vanishes — and AEX becomes reachable on cases where the
    fine A(e) is REV or DIA.

    This is the principled reconstruction of the v1 admissibility violation.
    Use only on a deliberately non-resolving step; it violates Theorem 2.
    """
    # Recognized AEX skeleton IDs: any composite whose ID exactly matches one
    # of these carries its S2-protection requirement. Composites with other
    # IDs lose any S2 component requirements they merged in.
    _RECOGNIZED_S2_IDS = {"freshness_gap", "evidence_currency_gap"}
    _RECOGNIZED_S1_IDS = {"approximation_quality_gap"}

    projected: dict[str, dict[str, str]] = {}
    for perm_name, gap_to_req in fine_reqs.items():
        composite_reqs: dict[str, str] = {}
        for composite_id, components in groups.items():
            # Only emit a requirement on this composite if its ID is recognized
            # as a member of the structural skeleton. Otherwise the projection
            # silently truncates whatever component requirements would have
            # been inherited.
            recognized = (
                composite_id in _RECOGNIZED_S2_IDS
                or composite_id in _RECOGNIZED_S1_IDS
            )
            if not recognized:
                # ALR is uniform-bounded over all composites; this truncation
                # only affects AEX, REV, DIA (where the recognized-skeleton
                # protection lives).
                if perm_name == "ALR" or perm_name == "AAA":
                    # ALR-style: demand bounded on every composite that has any
                    # component requirement.
                    if any(c in gap_to_req for c in components):
                        composite_reqs[composite_id] = "bounded"
                continue
            component_reqs = [
                gap_to_req[c] for c in components if c in gap_to_req
            ]
            if component_reqs:
                composite_reqs[composite_id] = _status_join(component_reqs)
        projected[perm_name] = composite_reqs
    return projected


# Default projection rule: admissible join semantics.
_project_requirements = _project_requirements_join


def _build_profiles_from_reqs(reqs_by_perm: dict[str, dict[str, str]]) -> list[t.Profile]:
    """Build Profile list from a {permission_name: {gap_id: req}} dict.

    All permissions are resolved against the conservation chain (REF, DIA,
    REV, AEX, ALR). The legacy "AAA mirrors ALR" trick from the default-chain
    era is no longer needed: ALR is Top in this chain, so the compiler does
    not need a higher sentinel level.
    """
    # Use only the four positive-permission levels (REF is Bottom and never
    # carries a profile). AAA does not exist in this chain.
    perms_by_name = {
        "DIA": _PERM_DIA,
        "REV": _PERM_REV,
        "AEX": _PERM_AEX,
        "ALR": _PERM_ALR,
    }
    profiles = []
    for name, perm in perms_by_name.items():
        gap_to_req = reqs_by_perm.get(name, {})
        required = [t.GapRequirement(gid, req) for gid, req in gap_to_req.items()]
        profiles.append(t.Profile(perm, required))
    return profiles


def _compile_case(
    gap_statuses: dict[str, str],
    reqs_by_perm: dict[str, dict[str, str]],
    fingerprint: str,
) -> str:
    """Run the compiler on a case with given statuses and profile requirements,
    against the paper's 5-level conservation chain."""
    profiles = _build_profiles_from_reqs(reqs_by_perm)
    gap_records = [
        t.GapRecord(gid, gid, status=status)
        for gid, status in gap_statuses.items()
    ]
    ctx = t.ProofContext(
        claim_id=f"claim-{fingerprint}",
        candidate_id=f"system-{fingerprint}",
        context_id=f"ctx-{fingerprint}",
        allowed_use="clinical_alert",
        membership=t.Membership.InClass,
        authority_ceiling=_PERM_ALR,
        expiry=t.Expiry.never(),
        gaps=gap_records,
        profiles=profiles,
        tokens=[],
        context_fingerprint=fingerprint,
    )
    judgment = t.compile(ctx, chain=_COMPILE_CHAIN)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=fingerprint)
    try:
        perm = judgment.permission(rt)
    except t.ExpiredError:
        # ExpiryFloor on the conservation chain is REF (collapsed Bottom).
        perm = _PERM_REF
    return str(perm)


def _grid_output(perm_str: str, k: int) -> float:
    """Map categorical permission to k-level numeric grid output ∈ [0, 1]."""
    p = _norm(perm_str)
    thresholds = np.linspace(1.0 / k, 1.0, k)
    n_satisfied = int(np.sum(p >= thresholds))
    return n_satisfied / k


# ── Case construction ────────────────────────────────────────────────────────

def _make_case(
    case_id: str,
    description: str,
    gap_statuses: dict[str, str],
    family: str,
    expert_judgment: str = "",
    fine_reqs: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Standardized case record. fine_reqs defaults to the uniform-bounded ALR."""
    full_statuses = {g: gap_statuses.get(g, "open") for g in _FINE_GAPS}
    return {
        "case_id": case_id,
        "description": description,
        "gap_statuses": full_statuses,
        "family": family,
        "expert_judgment": expert_judgment,
        "fine_reqs": fine_reqs if fine_reqs is not None else _default_fine_reqs(),
    }


def _get_epic_cases() -> list[dict]:
    from epic.experiment.cases import INDUCTION_CASES, HELD_OUT_CASES
    out = []
    for c in INDUCTION_CASES + HELD_OUT_CASES:
        # Map the cases' implicit "open" default to explicit open for all 9 gaps
        out.append(_make_case(
            case_id=c["case_id"],
            description=c.get("description", ""),
            gap_statuses=c["gap_statuses"],
            family="induction" if c["case_id"].startswith("M") else "held_out",
            expert_judgment=c.get("expert_judgment", ""),
        ))
    return out


def _make_level_ladder_cases() -> list[dict]:
    """Synthetic cases spanning REF, DIA, REV, AEX, ALR at fine resolution.

    These cover any permission levels the Epic corpus doesn't naturally reach.
    """
    all_bounded = {g: "bounded" for g in _FINE_GAPS}

    # S-ALR: every gap bounded → ALR.
    s_alr = dict(all_bounded)

    # S-AEX: AQ + freshness bounded, one ALR-required gap open.
    s_aex = dict(all_bounded)
    s_aex["model_specification_gap"] = "open"

    # S-REV: AQ bounded, freshness open → AEX blocked, REV reachable.
    s_rev = dict(all_bounded)
    s_rev["freshness_gap"] = "open"

    # S-DIA: AQ open → REV blocked. With no other profile between DIA and REV
    # gated on AQ, the compiler falls back to DIA.
    s_dia = {g: "bounded" for g in _FINE_GAPS}
    s_dia["approximation_quality_gap"] = "open"
    s_dia["freshness_gap"] = "open"

    # S-REF: synthetic — every gap open. The compiler returns the bottom permission.
    # (REF is the structural floor; under uniform-bounded ALR profiles with no
    # strict-closed demands, REF is reached only when even DIA's empty requirement
    # is "blocked" — which can't happen unless we explicitly demand something at DIA.
    # We construct S-REF by demanding the impossible at DIA via a strict requirement
    # on a gap that is open.)
    s_ref_reqs = _default_fine_reqs()
    s_ref_reqs["DIA"] = {"approximation_quality_gap": "closed"}
    s_ref_reqs["REV"] = {"approximation_quality_gap": "closed"}
    s_ref_reqs["AEX"] = {"approximation_quality_gap": "closed"}
    s_ref_reqs["ALR"] = {"approximation_quality_gap": "closed"}
    _sync_aaa_to_alr(s_ref_reqs)
    s_ref = {g: "bounded" for g in _FINE_GAPS}
    s_ref["approximation_quality_gap"] = "open"

    return [
        _make_case("S-REF", "Synthetic floor: AQ open + every level demands closed AQ", s_ref,
                   "synthetic_ladder", expert_judgment="REF", fine_reqs=s_ref_reqs),
        _make_case("S-DIA", "Synthetic: AQ open → REV blocked",
                   s_dia, "synthetic_ladder", expert_judgment="DIA"),
        _make_case("S-REV", "Synthetic: freshness open → AEX blocked",
                   s_rev, "synthetic_ladder", expert_judgment="REV"),
        _make_case("S-AEX", "Synthetic: one ALR-required fine gap open",
                   s_aex, "synthetic_ladder", expert_judgment="AEX"),
        _make_case("S-ALR", "Synthetic: every fine gap bounded",
                   s_alr, "synthetic_ladder", expert_judgment="ALR"),
    ]


def _make_witness_cases() -> list[dict]:
    """Active-refinement witnesses.

    Each witness installs a strict 'closed' fine-grained ALR requirement on
    one component of one composite, paired with a 'bounded' requirement on
    its sibling. Both component statuses are 'bounded' in the case. At every
    projection level coarser than the relevant split, the composite carries
    the strict 'closed' requirement (via the join semantics), but its
    composite status is 'bounded' (via the meet semantics) — so ALR is blocked
    and the compiler emits AEX. After the split, the strict 'closed' demand
    falls only on the genuinely-closed component, ALR clears.

    Each witness should rise AEX → ALR at exactly its target split.

    Construction notes:
      • All AQ and freshness must be bounded so AEX is reachable at all levels.
      • The non-target ALR fine requirements must all be satisfied at level 0
        so ALR clears once the target split occurs.
      • For the target composite, one component is 'closed' (satisfies the
        strict req) and one is 'bounded' (paired loose req); the composite
        status meet is 'bounded', so the projected composite requirement
        (which is 'closed' under the join rule) fails until the split.
    """
    # Base statuses: every gap bounded, then upgrade one to closed per witness.
    base_statuses = {g: "bounded" for g in _FINE_GAPS}

    # --- W-currency: target split is L4 → L3 (evidence_currency = freshness + reason_traceability)
    w_currency_statuses = dict(base_statuses)
    w_currency_statuses["freshness_gap"] = "closed"          # the strict-required component
    w_currency_statuses["reason_traceability_gap"] = "bounded"  # the loose-required sibling
    w_currency_reqs = _default_fine_reqs()
    w_currency_reqs["ALR"]["freshness_gap"] = "closed"
    w_currency_reqs["ALR"]["reason_traceability_gap"] = "bounded"
    _sync_aaa_to_alr(w_currency_reqs)

    # --- W-deployment: target split is L3 → L2 (deployment_control = blast_radius + authority)
    w_deployment_statuses = dict(base_statuses)
    w_deployment_statuses["blast_radius_gap"] = "closed"
    w_deployment_statuses["authority_gap"] = "bounded"
    w_deployment_reqs = _default_fine_reqs()
    w_deployment_reqs["ALR"]["blast_radius_gap"] = "closed"
    w_deployment_reqs["ALR"]["authority_gap"] = "bounded"
    _sync_aaa_to_alr(w_deployment_reqs)

    # --- W-population: target split is L2 → L1 (population_scope = distribution_shift + individual_population)
    w_population_statuses = dict(base_statuses)
    w_population_statuses["distribution_shift_gap"] = "closed"
    w_population_statuses["individual_population_gap"] = "bounded"
    w_population_reqs = _default_fine_reqs()
    w_population_reqs["ALR"]["distribution_shift_gap"] = "closed"
    w_population_reqs["ALR"]["individual_population_gap"] = "bounded"
    _sync_aaa_to_alr(w_population_reqs)

    # --- W-clinical: target split is L1 → L0 (model_adequacy = clinical_utility + model_specification)
    w_clinical_statuses = dict(base_statuses)
    w_clinical_statuses["clinical_utility_gap"] = "closed"
    w_clinical_statuses["model_specification_gap"] = "bounded"
    w_clinical_reqs = _default_fine_reqs()
    w_clinical_reqs["ALR"]["clinical_utility_gap"] = "closed"
    w_clinical_reqs["ALR"]["model_specification_gap"] = "bounded"
    _sync_aaa_to_alr(w_clinical_reqs)

    return [
        _make_case("W-currency", "Active witness: split G7+S2 reveals closed freshness",
                   w_currency_statuses, "active_witness",
                   expert_judgment="ALR", fine_reqs=w_currency_reqs),
        _make_case("W-deployment", "Active witness: split G5+G6 reveals closed blast_radius",
                   w_deployment_statuses, "active_witness",
                   expert_judgment="ALR", fine_reqs=w_deployment_reqs),
        _make_case("W-population", "Active witness: split G3+G4 reveals closed distribution_shift",
                   w_population_statuses, "active_witness",
                   expert_judgment="ALR", fine_reqs=w_population_reqs),
        _make_case("W-clinical", "Active witness: split G1+G2 reveals closed clinical_utility",
                   w_clinical_statuses, "active_witness",
                   expert_judgment="ALR", fine_reqs=w_clinical_reqs),
    ]


def _all_cases() -> list[dict]:
    """Full case corpus: induction + held-out + synthetic ladder + witnesses."""
    return _get_epic_cases() + _make_level_ladder_cases() + _make_witness_cases()


# ── Core sweep ───────────────────────────────────────────────────────────────

def _run_case_level(
    case: dict,
    level: int,
    groups: dict[str, list[str]],
    admissible: bool = True,
) -> str:
    """Compile a case under one projection level.

    admissible=True uses the join-of-component-requirements rule (Theorem 2
    conservative). admissible=False uses the v1 flat-bounded shortcut that
    violates Theorem 2 and produces the L5 over-authorization witness.
    """
    proj_statuses = _project_statuses(case["gap_statuses"], groups)
    if admissible:
        proj_reqs = _project_requirements_join(case["fine_reqs"], groups)
    else:
        proj_reqs = _project_requirements_skeleton_truncating(case["fine_reqs"], groups)
    return _compile_case(proj_statuses, proj_reqs, f"{case['case_id']}-L{level}-{'adm' if admissible else 'flat'}")


_FIELDNAMES_MATRIX = [
    "path", "case_id", "family", "expert_judgment",
    "level", "level_name", "n_gaps", "admissible",
    "k",
    "perm_m", "C_mn", "A_e", "gap",
    "sound", "monotone_m", "monotone_n",
]


def main() -> None:
    print(f"\n{'='*100}")
    print("  Experiment 6 v2 — Two-Axis Joint Convergence, Full Matrix")
    print("  Path × Case × Projection level (m) × Permission grid (k)")
    print(f"{'='*100}")

    cases = _all_cases()
    print(f"\n  {len(cases)} cases:")
    family_counts: dict[str, int] = {}
    for c in cases:
        family_counts[c["family"]] = family_counts.get(c["family"], 0) + 1
        print(f"    {c['case_id']:>12}  [{c['family']:>16}]  expert={c['expert_judgment']:>4}  — {c['description']}")
    print(f"\n  Counts: {family_counts}")

    # Fine-resolution reference: compute A(e) = C_{0, k_max}(e) for every case.
    # The reference is always computed under the admissible (join) rule —
    # this is the semantic ceiling A(e), not the inadmissible projection's
    # implemented value.
    print(f"\n  Computing reference A(e) at L0, k={max(K_LEVELS)}...")
    ref_perms: dict[str, str] = {}
    ref_norms: dict[str, float] = {}
    for case in cases:
        perm = _run_case_level(case, 0, _LEVEL_0_GROUPS, admissible=True)
        ref_perms[case["case_id"]] = perm
        ref_norms[case["case_id"]] = _grid_output(perm, max(K_LEVELS))
    print(f"  {'case':>12}  {'A(e) perm':>10}  {'A(e) norm':>10}")
    for case in cases:
        cid = case["case_id"]
        print(f"  {cid:>12}  {ref_perms[cid]:>10}  {ref_norms[cid]:>10.4f}")

    # Run the full matrix
    rows: list[dict] = []

    for path_name, path in [("resolving", _RESOLVING_PATH), ("nonresolving", _NONRESOLVING_PATH)]:
        # Track previous (case, k) → C_mn for monotone-in-m check
        prev_by_level_k: dict[tuple[str, int], float] = {}

        for step_idx, (level, level_name, groups, admissible) in enumerate(path):
            n_gaps = len(groups)
            for case in cases:
                cid = case["case_id"]
                perm_m = _run_case_level(case, level, groups, admissible=admissible)
                ae = ref_norms[cid]
                prev_k_C: float | None = None
                for k in K_LEVELS:
                    c_mn = _grid_output(perm_m, k)
                    gap = ae - c_mn
                    sound = int(c_mn <= ae + 1e-9)

                    prev_m_val = prev_by_level_k.get((cid, k))
                    if step_idx == 0:
                        mon_m = 1  # first level — vacuously monotone
                    else:
                        mon_m = int(c_mn >= prev_m_val - 1e-9) if prev_m_val is not None else 1

                    mon_n = int(c_mn >= (prev_k_C or 0.0) - 1e-9) if prev_k_C is not None else 1

                    rows.append({
                        "path": path_name,
                        "case_id": cid,
                        "family": case["family"],
                        "expert_judgment": case["expert_judgment"],
                        "level": level,
                        "level_name": level_name,
                        "n_gaps": n_gaps,
                        "admissible": int(admissible),
                        "k": k,
                        "perm_m": perm_m,
                        "C_mn": round(c_mn, 6),
                        "A_e": round(ae, 6),
                        "gap": round(gap, 6),
                        "sound": sound,
                        "monotone_m": mon_m,
                        "monotone_n": mon_n,
                    })

                    prev_k_C = c_mn

                # Update prev_by_level_k after the full k-sweep for this (path, case, level)
                for k in K_LEVELS:
                    c_mn_k = next(
                        r["C_mn"] for r in rows
                        if r["path"] == path_name and r["case_id"] == cid
                        and r["level"] == level and r["k"] == k
                    )
                    prev_by_level_k[(cid, k)] = c_mn_k

    # ── CSV outputs ───────────────────────────────────────────────────────────
    matrix_path = RESULTS_DIR / "two_axis_convergence_v2_matrix.csv"
    with open(matrix_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES_MATRIX)
        writer.writeheader()
        writer.writerows(rows)

    # Admissibility violations: where soundness fails
    violations = [r for r in rows if r["sound"] == 0]
    viol_path = RESULTS_DIR / "two_axis_convergence_v2_admissibility.csv"
    with open(viol_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES_MATRIX)
        writer.writeheader()
        writer.writerows(violations)

    # Per-(path, case) summary
    summary_rows = []
    for path_name in ["resolving", "nonresolving"]:
        for case in cases:
            cid = case["case_id"]
            case_rows = [r for r in rows if r["path"] == path_name and r["case_id"] == cid]
            n_cells = len(case_rows)
            n_sound = sum(r["sound"] for r in case_rows)
            n_mon_m = sum(r["monotone_m"] for r in case_rows)
            n_mon_n = sum(r["monotone_n"] for r in case_rows)
            finest_max_k_row = next(
                (r for r in case_rows if r["level"] == 0 and r["k"] == max(K_LEVELS)),
                None,
            )
            joint_converged = (
                finest_max_k_row is not None
                and abs(finest_max_k_row["gap"]) < 1e-9
            )
            summary_rows.append({
                "path": path_name,
                "case_id": cid,
                "family": case["family"],
                "expert_judgment": case["expert_judgment"],
                "A_e_perm": ref_perms[cid],
                "n_cells": n_cells,
                "n_sound": n_sound,
                "n_mon_m": n_mon_m,
                "n_mon_n": n_mon_n,
                "joint_converged": int(joint_converged),
            })
    summary_path = RESULTS_DIR / "two_axis_convergence_v2_summary.csv"
    summary_fields = [
        "path", "case_id", "family", "expert_judgment", "A_e_perm",
        "n_cells", "n_sound", "n_mon_m", "n_mon_n", "joint_converged",
    ]
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    # ── Reports ───────────────────────────────────────────────────────────────

    # Active-refinement witness verification
    print(f"\n{'─'*100}")
    print(f"  ACTIVE-REFINEMENT WITNESS VERIFICATION (resolving path, k={max(K_LEVELS)})")
    print(f"{'─'*100}")
    print(f"  Each witness should rise AEX → ALR at exactly its target split.")
    print(f"  {'witness':>12}  {'target split':>20}  "
          f"{'L4':>6}  {'L3':>6}  {'L2':>6}  {'L1':>6}  {'L0':>6}  result")
    witness_targets = {
        "W-currency":    ("L4→L3", 4, 3),
        "W-deployment":  ("L3→L2", 3, 2),
        "W-population":  ("L2→L1", 2, 1),
        "W-clinical":    ("L1→L0", 1, 0),
    }
    for witness_id, (target_name, m_before, m_after) in witness_targets.items():
        perms_by_level = {}
        for level in [4, 3, 2, 1, 0]:
            r = next(
                r for r in rows
                if r["path"] == "resolving" and r["case_id"] == witness_id
                and r["level"] == level and r["k"] == max(K_LEVELS)
            )
            perms_by_level[level] = r["perm_m"]
        before = perms_by_level[m_before]
        after = perms_by_level[m_after]
        active = (before == "AEX" and after == "ALR")
        result_str = "✓ active step" if active else f"⚠ {before}→{after}"
        print(f"  {witness_id:>12}  {target_name:>20}  "
              f"{perms_by_level[4]:>6}  {perms_by_level[3]:>6}  "
              f"{perms_by_level[2]:>6}  {perms_by_level[1]:>6}  "
              f"{perms_by_level[0]:>6}  {result_str}")

    # Admissibility violations table
    print(f"\n{'─'*100}")
    print(f"  ADMISSIBILITY VIOLATIONS — every (case, m, k) where C_mn > A(e)")
    print(f"  (non-resolving path only; L5 uses the skeleton-truncating projection)")
    print(f"{'─'*100}")
    if not violations:
        print("  (none)")
    else:
        from collections import defaultdict
        by_pcl: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
        for v in violations:
            by_pcl[(v["path"], v["case_id"], v["level"])].append(v)

        print(f"  {'path':>13}  {'case':>12}  {'family':>16}  {'level':>5}  "
              f"{'A(e)':>5}  {'L5 perm':>7}  {'k values where unsound':>26}")
        for (path_n, cid, lvl), vs in sorted(by_pcl.items()):
            ks = sorted({v["k"] for v in vs})
            ks_str = ",".join(str(k) for k in ks)
            family = vs[0]["family"]
            l5_perm = vs[0]["perm_m"]
            ae_perm_for_case = ref_perms[cid]
            print(f"  {path_n:>13}  {cid:>12}  {family:>16}  {lvl:>5}  "
                  f"{ae_perm_for_case:>5}  {l5_perm:>7}  {ks_str:>26}")

    # Monotonicity break vs admissibility restoration
    print(f"\n{'─'*100}")
    print(f"  MONOTONICITY BREAK COINCIDES WITH ADMISSIBILITY RESTORATION")
    print(f"  (non-resolving path: L5 → L4 transition)")
    print(f"{'─'*100}")
    print(f"  For each case, compare L5 (inadmissible flat) vs L4 (admissible join):")
    print(f"  {'case':>12}  {'family':>16}  {'A(e)':>5}  {'L5 perm':>7}  "
          f"{'L4 perm':>7}  {'mon_m at L4':>12}  {'L5 was unsound':>15}")
    for case in cases:
        cid = case["case_id"]
        l5_row = next(
            (r for r in rows if r["path"] == "nonresolving"
             and r["case_id"] == cid and r["level"] == 5 and r["k"] == max(K_LEVELS)),
            None,
        )
        l4_row = next(
            (r for r in rows if r["path"] == "nonresolving"
             and r["case_id"] == cid and r["level"] == 4 and r["k"] == max(K_LEVELS)),
            None,
        )
        if l5_row is None or l4_row is None:
            continue
        broke = "✗ broke" if l4_row["monotone_m"] == 0 else "✓ held"
        was_unsound = "✗ unsound" if l5_row["sound"] == 0 else "  sound"
        print(f"  {cid:>12}  {case['family']:>16}  {ref_perms[cid]:>5}  "
              f"{l5_row['perm_m']:>7}  {l4_row['perm_m']:>7}  "
              f"{broke:>12}  {was_unsound:>15}")

    # Resolving / non-resolving gate summary
    print(f"\n{'─'*100}")
    print(f"  GATE SUMMARY")
    print(f"{'─'*100}")
    for path_name in ["resolving", "nonresolving"]:
        path_rows = [r for r in rows if r["path"] == path_name]
        n_total = len(path_rows)
        n_sound = sum(r["sound"] for r in path_rows)
        n_mon_m = sum(r["monotone_m"] for r in path_rows)
        n_mon_n = sum(r["monotone_n"] for r in path_rows)
        n_cases = len(cases)
        n_finest = sum(1 for r in path_rows
                       if r["level"] == 0 and r["k"] == max(K_LEVELS))
        n_converged = sum(
            1 for r in path_rows
            if r["level"] == 0 and r["k"] == max(K_LEVELS) and abs(r["gap"]) < 1e-9
        )

        print(f"\n  {path_name.upper()} path:")
        print(f"    Total (path × case × m × n) cells:    {n_total}")
        print(f"    Soundness  (C_mn ≤ A(e)):             {n_sound}/{n_total}"
              f"  ({'PASS' if n_sound == n_total else 'FAIL (expected for non-resolving)'})")
        print(f"    Monotone in m (finer → stronger):     {n_mon_m}/{n_total}"
              f"  ({'PASS' if n_mon_m == n_total else 'FAIL (expected at non-resolving step)'})")
        print(f"    Monotone in n (denser → stronger):    {n_mon_n}/{n_total}"
              f"  ({'PASS' if n_mon_n == n_total else 'NOTE: non-monotone n is rare'})")
        print(f"    Joint convergence at (m=0, k={max(K_LEVELS)}):     "
              f"{n_converged}/{n_finest} cases  "
              f"({'PASS' if n_converged == n_finest else 'FAIL'})")

    print(f"\n  Outputs:")
    print(f"    Full matrix:        {matrix_path}")
    print(f"    Summary:            {summary_path}")
    print(f"    Admissibility log:  {viol_path}")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
