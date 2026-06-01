"""CFPB / ECOA blind audit for CRED-IND-001.

Opened AFTER the induction is complete. Compares the induced gap taxonomy
against ECOA 15 U.S.C. § 1691(d), Regulation B 12 CFR § 1002.9, and
CFPB Circular 2022-03 (May 26, 2022).

Protocol: the regulatory text is never consulted during induction.
This module is run last and must not be imported before induction completes.
"""
from __future__ import annotations

from .profile import InductionState

# ── Regulatory requirements ────────────────────────────────────────────────────
# Opened here for the first time, after induction.

CFPB_REQUIREMENTS = [
    {
        "req_id":      "ECOA-1691d",
        "source":      "ECOA / Regulation B / CFPB Circular 2022-03",
        "citation":    "15 U.S.C. § 1691(d)(2); 12 CFR § 1002.9(b)(2); CFPB Circular 2022-03",
        "description": (
            "Creditors must provide applicants against whom adverse action is taken "
            "with a specific, accurate statement of the principal reasons. The "
            "statement must relate to and accurately describe the factors actually "
            "considered or scored. Model complexity is not an excuse for noncompliance."
        ),
        "matched_gaps": ["reason_traceability_gap"],
        "classification": "EXACT",
        "notes": (
            "The compiler induces a requirement for a specific, accurate, individual-level "
            "reason traceable to the model's actual inputs. ECOA and Regulation B require "
            "the same from the regulatory side. CFPB Circular 2022-03 makes explicit that "
            "the reasons must accurately describe the factors actually considered — not an "
            "approximation or post-hoc rationalization. Both sides require the same thing "
            "from different starting points. Classification: EXACT. "
            "Note: the regulation specifies cardinality (2–4 reasons); the compiler's token "
            "is binary (present/absent). The binary token is a simplification of the full "
            "regulatory requirement in one respect, while equivalent in the primary respect "
            "(accuracy and traceability). The EXACT classification holds on the core requirement."
        ),
    },
]

# Requirements the compiler cannot reach from credit deployment failures alone.
# These are COMPILER_PERMISSIVE: real regulatory obligations outside the
# evidence space the induction can access.
COMPILER_PERMISSIVE = [
    {
        "req_id":      "ECOA-disparate-impact",
        "source":      "ECOA / Regulation B",
        "citation":    "12 CFR § 1002.6(a); CFPB Guidance on AI/ML 2022",
        "description": (
            "Prohibition on disparate impact: credit scoring models must not produce "
            "outcomes that disproportionately disadvantage protected classes, even absent "
            "discriminatory intent."
        ),
        "notes": (
            "No induction case failed specifically because of disparate impact — the "
            "failure mode in C02 is reason traceability, not discriminatory outcomes. "
            "Disparate impact is a separate regulatory obligation not forced by the "
            "evidence structure of this induction. COMPILER_PERMISSIVE."
        ),
    },
    {
        "req_id":      "FCRA-accuracy",
        "source":      "Fair Credit Reporting Act",
        "citation":    "15 U.S.C. § 1681e(b)",
        "description": (
            "Consumer reporting agencies must follow reasonable procedures to ensure "
            "maximum possible accuracy of credit report information used in scoring."
        ),
        "notes": (
            "Input data accuracy is upstream of the model; the induction addresses "
            "model evidence, not data pipeline accuracy. COMPILER_PERMISSIVE."
        ),
    },
]


def run_audit(state: InductionState) -> dict:
    discovered = state.induced_gaps
    coverage = []
    covered_count = 0

    for req in CFPB_REQUIREMENTS:
        matched = [g for g in req["matched_gaps"] if g in discovered]
        covered = len(matched) > 0
        if covered:
            covered_count += 1
        coverage.append({
            "req_id":      req["req_id"],
            "source":      req["source"],
            "citation":    req["citation"],
            "description": req["description"],
            "matched_gaps": matched,
            "covered":     covered,
            "classification": req["classification"] if covered else "COMPILER_PERMISSIVE",
            "notes":       req["notes"],
        })

    for req in COMPILER_PERMISSIVE:
        coverage.append({
            "req_id":      req["req_id"],
            "source":      req["source"],
            "citation":    req["citation"],
            "description": req["description"],
            "matched_gaps": [],
            "covered":     False,
            "classification": "COMPILER_PERMISSIVE",
            "notes":       req["notes"],
        })

    total = len(CFPB_REQUIREMENTS) + len(COMPILER_PERMISSIVE)
    uncovered = [r["req_id"] for r in coverage if not r["covered"]]
    novel_gaps = [g for g in discovered if not any(
        g in req["matched_gaps"] for req in CFPB_REQUIREMENTS
    )]

    return {
        "discovered_gaps": discovered,
        "coverage":        coverage,
        "novel_gaps":      novel_gaps,
        "uncovered_requirements": uncovered,
        "summary": {
            "covered":              covered_count,
            "total_requirements":   len(CFPB_REQUIREMENTS),
            "permissive_items":     len(COMPILER_PERMISSIVE),
            "total":                total,
            "coverage_pct":         round(100 * covered_count / len(CFPB_REQUIREMENTS)),
            "uncovered":            len(uncovered) - len(COMPILER_PERMISSIVE),
            "novel_gaps":           len(novel_gaps),
        },
    }
