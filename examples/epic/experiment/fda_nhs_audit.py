"""Post-hoc audit: does the compiler-discovered taxonomy match FDA and NHS guidelines?

This module is run AFTER induction completes. It is never consulted during the
induction loop — the compiler has no access to this knowledge.

The audit compares the discovered gap set against requirements drawn from:

  FDA (Jan 2025) Draft Guidance:
    "Artificial Intelligence-Enabled Device Software Functions"
    Appendix C: operating-point metrics with 95% CIs required
    §5: transparency requirements for training/validation populations
    §6: real-world performance monitoring plan

  NHS Royal College of Radiologists (Nov 2024):
    "AI Deployment Fundamentals for Medical Imaging"
    §4.21: shadow mode mandatory before go-live
    §4.22: enriched local population test set required
    §2.13: post-implementation evaluation plan required before deployment

  EU AI Act (2024), High-Risk AI Systems (Annex III):
    Article 9: risk management system — continuous identification of known risks
    Article 10: training, validation, testing data governance
    Article 13: transparency and provision of information to deployers
    Article 14: human oversight — ability to override/stop system

Each regulatory requirement is mapped to zero, one, or more of the
compiler-discovered gaps. The audit shows which gaps correspond to which
regulatory obligations — and flags any regulatory obligations that have
no corresponding gap (coverage gaps in the taxonomy) or any discovered
gaps with no regulatory analog (novel discoveries).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .profile import InductionState


@dataclass
class RegulatoryRequirement:
    """One requirement from FDA, NHS, or EU AI Act."""
    req_id: str
    source: str          # "FDA-2025", "NHS-RCR-2024", "EU-AI-Act-2024"
    section: str         # e.g. "Appendix C", "§4.21"
    description: str
    corresponding_gaps: list[str] = field(default_factory=list)
    notes: str = ""


# ── Regulatory requirement corpus ─────────────────────────────────────────────
# These are the requirements an independent regulator would list.
# The audit checks whether the compiler discovered a gap for each.

FDA_2025_REQUIREMENTS: list[RegulatoryRequirement] = [
    RegulatoryRequirement(
        req_id="FDA-C1",
        source="FDA-2025",
        section="Appendix C",
        description=(
            "Operating-point metrics (sensitivity, specificity, PPV, NPV) with 95% "
            "confidence intervals must be reported at the clinically intended threshold, "
            "not just summary AUC."
        ),
        corresponding_gaps=["clinical_utility_gap"],
        notes=(
            "AUC is an aggregate measure. FDA requires threshold-specific metrics because "
            "a model with AUC=0.80 can have PPV=0.10 at the operating threshold. "
            "The compiler discovers clinical_utility_gap for exactly this reason: "
            "M02 (Epic) shows AUC-bounded but PPV=0.12 at threshold."
        ),
    ),
    RegulatoryRequirement(
        req_id="FDA-C2",
        source="FDA-2025",
        section="§5 / Appendix C",
        description=(
            "Training and validation population characteristics must be disclosed, "
            "including demographic breakdowns and site-specific validation results."
        ),
        corresponding_gaps=["distribution_shift_gap", "model_specification_gap"],
        notes=(
            "FDA requires disclosure of who the model was trained on and whether it "
            "performs consistently across subpopulations. The compiler discovers "
            "distribution_shift_gap (M04) and model_specification_gap (M03) from the "
            "same underlying failure: a model validated on one population may fail "
            "systematically on another."
        ),
    ),
    RegulatoryRequirement(
        req_id="FDA-C3",
        source="FDA-2025",
        section="§6 / PMA conditions",
        description=(
            "Real-world performance monitoring plan required before deployment. "
            "For PMA-class devices, post-market monitoring may be a condition of approval."
        ),
        corresponding_gaps=["authority_gap"],
        notes=(
            "FDA's monitoring requirement is a form of ongoing authority constraint: "
            "the deployer must maintain oversight mechanisms after go-live. "
            "The compiler discovers authority_gap (M07) which captures the requirement "
            "that autonomous action must be bounded with oversight contracts."
        ),
    ),
    RegulatoryRequirement(
        req_id="FDA-C4",
        source="FDA-2025",
        section="§4 intended use",
        description=(
            "Intended use statement must clearly specify the clinical action the output "
            "supports, not just the prediction task."
        ),
        corresponding_gaps=["model_specification_gap"],
        notes=(
            "FDA distinguishes prediction task from clinical action. A model that "
            "predicts cost is not validated for care allocation decisions. "
            "The compiler discovers model_specification_gap (M03) from the same "
            "distinction: training target must match action target."
        ),
    ),
]

NHS_RCR_2024_REQUIREMENTS: list[RegulatoryRequirement] = [
    RegulatoryRequirement(
        req_id="NHS-4.21",
        source="NHS-RCR-2024",
        section="§4.21",
        description=(
            "Shadow mode deployment mandatory before go-live: system must run in "
            "parallel with existing practice without affecting clinical decisions, "
            "with local performance data collected."
        ),
        corresponding_gaps=["distribution_shift_gap"],
        notes=(
            "Shadow mode is NHS's mechanism for closing the distribution_shift_gap: "
            "it measures performance on the local deployment population before the "
            "model has any authority over clinical decisions. "
            "The compiler discovers distribution_shift_gap (M04) as the gap that "
            "training-population validation cannot close."
        ),
    ),
    RegulatoryRequirement(
        req_id="NHS-4.22",
        source="NHS-RCR-2024",
        section="§4.22",
        description=(
            "Enriched local population test set required: a test set drawn from the "
            "local deployment population, not just the training population."
        ),
        corresponding_gaps=["distribution_shift_gap", "individual_population_gap"],
        notes=(
            "§4.22 addresses both distribution shift (local vs. training population) "
            "and the individual/population distinction: a local test set validates "
            "performance on the specific patient population the model will act on."
        ),
    ),
    RegulatoryRequirement(
        req_id="NHS-2.13",
        source="NHS-RCR-2024",
        section="§2.13",
        description=(
            "Post-implementation evaluation plan required before deployment. "
            "Must specify performance metrics, review frequency, and criteria "
            "for suspension of deployment."
        ),
        corresponding_gaps=["authority_gap"],
        notes=(
            "NHS §2.13 is operationally equivalent to FDA's monitoring requirement: "
            "a post-deployment oversight contract is required before go-live. "
            "The compiler discovers authority_gap (M07) as the gap that captures "
            "this class of requirement: autonomous action must be bounded with "
            "ongoing oversight contracts."
        ),
    ),
    RegulatoryRequirement(
        req_id="NHS-3.1",
        source="NHS-RCR-2024",
        section="§3.1",
        description=(
            "Clinical utility must be demonstrated: the system must show benefit "
            "in clinical outcomes, not just performance on a held-out test set."
        ),
        corresponding_gaps=["clinical_utility_gap"],
        notes=(
            "NHS §3.1 is precisely clinical_utility_gap: AUC on a test set is not "
            "sufficient evidence of clinical benefit. The gap requires sensitivity, "
            "PPV, and downstream outcome data at the operating threshold."
        ),
    ),
]

EU_AI_ACT_2024_REQUIREMENTS: list[RegulatoryRequirement] = [
    RegulatoryRequirement(
        req_id="EU-9",
        source="EU-AI-Act-2024",
        section="Article 9",
        description=(
            "Risk management system: providers must identify, estimate, evaluate, "
            "and adopt risk control measures for known and foreseeable risks throughout "
            "the system lifecycle."
        ),
        corresponding_gaps=["blast_radius_gap", "authority_gap"],
        notes=(
            "Article 9 maps to blast_radius_gap (scope of downstream action must be "
            "bounded — that is the risk estimate) and authority_gap (control measures "
            "must be adopted — that is the oversight contract). "
            "The compiler discovers both (M06, M07) from concrete deployment failures."
        ),
    ),
    RegulatoryRequirement(
        req_id="EU-10",
        source="EU-AI-Act-2024",
        section="Article 10",
        description=(
            "Data governance: training and validation data must be relevant, "
            "representative, and free from errors and biases that lead to prohibited "
            "outcomes."
        ),
        corresponding_gaps=["model_specification_gap", "distribution_shift_gap"],
        notes=(
            "Article 10 maps to model_specification_gap (training data must represent "
            "the action target, not just a proxy) and distribution_shift_gap (validation "
            "data must represent the deployment population)."
        ),
    ),
    RegulatoryRequirement(
        req_id="EU-13",
        source="EU-AI-Act-2024",
        section="Article 13",
        description=(
            "Transparency: deployers must be provided with instructions for use "
            "including performance on different subpopulations, known limitations, "
            "and conditions under which the system should not be used."
        ),
        corresponding_gaps=["individual_population_gap", "distribution_shift_gap"],
        notes=(
            "Article 13 transparency requirements map directly to individual_population_gap "
            "(deployers must be told when population scores are not valid for individual "
            "decisions) and distribution_shift_gap (deployers must be told for which "
            "populations the system is validated)."
        ),
    ),
    RegulatoryRequirement(
        req_id="EU-14",
        source="EU-AI-Act-2024",
        section="Article 14",
        description=(
            "Human oversight: high-risk AI systems must be designed to allow effective "
            "oversight by natural persons, including ability to override, stop, or "
            "disregard outputs."
        ),
        corresponding_gaps=["authority_gap"],
        notes=(
            "Article 14 is authority_gap: the system must not exercise autonomous "
            "authority beyond what is bounded by an oversight contract. The compiler "
            "discovers this (M07) from the Dutch childcare case, where automated demands "
            "with no override or explanation mechanism led to 26,000 wrongful accusations."
        ),
    ),
]

ALL_REQUIREMENTS = FDA_2025_REQUIREMENTS + NHS_RCR_2024_REQUIREMENTS + EU_AI_ACT_2024_REQUIREMENTS


def run_audit(state: InductionState) -> dict:
    """Compare the compiler-discovered taxonomy against regulatory requirements.

    Returns a dict with:
      - discovered_gaps: list of gaps the compiler induced
      - coverage: for each regulatory requirement, which discovered gaps cover it
      - uncovered_requirements: requirements with no discovered gap
      - novel_gaps: discovered gaps with no regulatory analog
      - summary: coverage statistics
    """
    discovered = set(state.induced_gaps)

    coverage = []
    uncovered = []
    for req in ALL_REQUIREMENTS:
        matched = [g for g in req.corresponding_gaps if g in discovered]
        coverage.append({
            "req_id": req.req_id,
            "source": req.source,
            "section": req.section,
            "description": req.description,
            "corresponding_gaps": req.corresponding_gaps,
            "matched_gaps": matched,
            "covered": len(matched) > 0,
            "notes": req.notes,
        })
        if not matched:
            uncovered.append(req.req_id)

    # Regulatory gaps that map to any discovered gap
    all_regulatory_gaps: set[str] = set()
    for req in ALL_REQUIREMENTS:
        all_regulatory_gaps.update(req.corresponding_gaps)

    novel = [g for g in state.induced_gaps if g not in all_regulatory_gaps]

    n_covered = sum(1 for c in coverage if c["covered"])
    return {
        "discovered_gaps": list(state.induced_gaps),
        "taxonomy_version": state.version_str(),
        "coverage": coverage,
        "uncovered_requirements": uncovered,
        "novel_gaps": novel,
        "summary": {
            "total_requirements": len(ALL_REQUIREMENTS),
            "covered": n_covered,
            "uncovered": len(uncovered),
            "coverage_pct": round(100 * n_covered / len(ALL_REQUIREMENTS), 1),
            "novel_gaps": len(novel),
        },
    }
