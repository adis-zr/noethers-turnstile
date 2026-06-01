"""Experiment 2: Hidden gap experiments — testing the compiler's blindness property.

Two sub-experiments:

  Experiment 2a — Falsely optimistic statuses (dishonest submitter)
  -----------------------------------------------------------------
  Take each induction case and replace its OPEN blocking gaps with "bounded".
  The compiler now receives falsely optimistic evidence. Does it over-authorize?

  This tests the trust boundary: the compiler enforces structural constraints on
  the shape of evidence (which gaps are present, what the profile requires) but
  cannot verify whether a status claim is truthful. A dishonest submitter who
  marks every gap "bounded" will reach ALR.

  Experiment 2b — Omitted gap entries (genuine blindness)
  -------------------------------------------------------
  Take each induction case and remove the blocking gap entries entirely from the
  gap_statuses dict — don't mark them open, don't mark them bounded, just omit them.
  The compiler bridge defaults absent gaps to "open".

  This tests whether the induction loop's blindness is genuine: when a gap is not
  yet in the taxonomy, the profile cannot require it, so the omission is invisible.
  But once a gap IS in the taxonomy, omitting it from the case causes the compiler
  to treat it as "open" — correctly blocking ALR.

  The two experiments together define the trust boundary precisely:
  - 2a: the compiler breaks when statuses are falsified (dishonest submitter)
  - 2b: the compiler works correctly when gaps are merely absent (honest omission
    of unknown evidence), because absent = open by default
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import noethers_turnstile as t

from ..cases import INDUCTION_CASES
from ..compiler import _perm_str, compile_case
from ..profile import InductionState

# ── Shared converged state ─────────────────────────────────────────────────────

def _converged_state() -> InductionState:
    """Build the converged v6 state by replaying the induction."""
    state = InductionState()
    induced = [
        "clinical_utility_gap",
        "model_specification_gap",
        "distribution_shift_gap",
        "individual_population_gap",
        "blast_radius_gap",
        "authority_gap",
    ]
    for gap in induced:
        state.add_gap(gap)
    return state


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class HiddenGapResult:
    experiment: str          # "2a" or "2b"
    case_id: str
    description: str
    original_output: str     # what the converged compiler normally emits
    expert_judgment: str
    modified_output: str     # what it emits after the modification
    modification: str        # what was changed
    gaps_affected: list[str]
    over_authorized: bool    # did it reach ALR when expert says < ALR?
    finding: str


# ── Experiment 2a: Falsely optimistic statuses ─────────────────────────────────

def run_2a_falsified_statuses() -> list[HiddenGapResult]:
    """Replace OPEN blocking gaps with 'bounded' on each induction case.

    For each case, we:
    1. Record the normal compiler output under the converged v6 state
    2. Replace each OPEN blocking gap with "bounded" (the lie)
    3. Re-compile and record the new output
    4. Check whether the compiler was fooled into ALR
    """
    state = _converged_state()
    results = []

    for case in INDUCTION_CASES:
        if case["case_id"] == "M01":
            continue  # positive control; no blocking gaps to falsify

        # Normal output
        normal_output = _perm_str(compile_case(case, state))

        # Build falsified case: replace blocking gaps with "bounded"
        falsified = copy.deepcopy(case)
        for gap in case["blocking_gaps"]:
            falsified["gap_statuses"][gap] = "bounded"

        # Also fill in any gaps not mentioned in gap_statuses but required by v6
        # (they default to "open" in compile_case — the dishonest submitter would
        # mark them bounded too)
        for gap in state.alr_reqs:
            if gap not in falsified["gap_statuses"]:
                falsified["gap_statuses"][gap] = "bounded"

        falsified_output = _perm_str(compile_case(falsified, state))
        over_auth = (falsified_output == "ALR" and
                     case["expert_judgment"] not in ("ALR", "AAA"))

        results.append(HiddenGapResult(
            experiment="2a",
            case_id=case["case_id"],
            description=case["description"],
            original_output=normal_output,
            expert_judgment=case["expert_judgment"],
            modified_output=falsified_output,
            modification=f"Blocking gaps {case['blocking_gaps']} changed from open → bounded",
            gaps_affected=case["blocking_gaps"],
            over_authorized=over_auth,
            finding=(
                f"BREAKS: falsified statuses reach {falsified_output} "
                f"(expert: {case['expert_judgment']}). "
                "Dishonest submitter bypasses the profile."
                if over_auth else
                f"BLOCKED: even with falsified statuses, compiler emits {falsified_output}. "
                "Other open gaps or structural constraints still block ALR."
            ),
        ))

    return results


# ── Experiment 2b: Omitted gap entries ────────────────────────────────────────

def run_2b_omitted_gaps() -> list[HiddenGapResult]:
    """Remove blocking gap entries entirely from gap_statuses.

    Two scenarios for each induction case:
      (i)  Omit under the converged v6 state: gap absent → treated as open → ALR blocked
      (ii) Omit under the v0 state (gap not yet in taxonomy): gap absent → invisible → ALR emitted

    This directly tests the induction loop's blindness property:
    - Pre-induction: absent gaps ARE invisible (not in taxonomy → not required)
    - Post-induction: absent gaps are open by default (in taxonomy → required → open blocks ALR)
    """
    converged = _converged_state()
    v0_state = InductionState()  # no domain gaps

    results = []

    for case in INDUCTION_CASES:
        if case["case_id"] == "M01":
            continue

        # Under converged v6: omit the blocking gap
        omitted_converged = copy.deepcopy(case)
        for gap in case["blocking_gaps"]:
            omitted_converged["gap_statuses"].pop(gap, None)

        output_v6_omitted = _perm_str(compile_case(omitted_converged, converged))

        # Under v0: omit the blocking gap (it's not in the taxonomy yet)
        omitted_v0 = copy.deepcopy(case)
        for gap in case["blocking_gaps"]:
            omitted_v0["gap_statuses"].pop(gap, None)
        # Also strip any domain gaps from v0's sight — v0 only tracks AQ + freshness
        # Make sure those are bounded so v0 can reach ALR
        omitted_v0["gap_statuses"]["approximation_quality_gap"] = "bounded"
        omitted_v0["gap_statuses"]["freshness_gap"] = "bounded"

        output_v0_omitted = _perm_str(compile_case(omitted_v0, v0_state))

        # Under converged v6: gap absent defaults to "open" → should block ALR
        v6_over_auth = (output_v6_omitted == "ALR" and
                        case["expert_judgment"] not in ("ALR", "AAA"))
        # Under v0: gap absent and not in taxonomy → invisible → v0 should emit ALR
        v0_correct_blindness = output_v0_omitted == "ALR"

        results.append(HiddenGapResult(
            experiment="2b",
            case_id=case["case_id"],
            description=case["description"],
            original_output=_perm_str(compile_case(case, converged)),
            expert_judgment=case["expert_judgment"],
            modified_output=f"v6={output_v6_omitted} / v0={output_v0_omitted}",
            modification=f"Blocking gaps {case['blocking_gaps']} removed from gap_statuses entirely",
            gaps_affected=case["blocking_gaps"],
            over_authorized=v6_over_auth,
            finding=(
                f"v6 omitted: {output_v6_omitted} "
                f"({'BLOCKED — absent gap defaults to open, correctly blocks ALR' if not v6_over_auth else 'BREAKS — absent gap invisible under v6'}). "
                f"v0 omitted: {output_v0_omitted} "
                f"({'CORRECT BLINDNESS — gap not in taxonomy, correctly invisible' if v0_correct_blindness else 'UNEXPECTED — v0 did not reach ALR with absent gap'}). "
            ),
        ))

    return results


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all_hidden_gap_experiments() -> tuple[list[HiddenGapResult], list[HiddenGapResult]]:
    return run_2a_falsified_statuses(), run_2b_omitted_gaps()
