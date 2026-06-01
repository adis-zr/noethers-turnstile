"""MED-IND-001: Empty Taxonomy Experiment — run and report.

Starting from a structural skeleton (v0: approximation_quality + freshness
only), the compiler converges on a multi-gap taxonomy through case-by-case
falsification. No domain knowledge is consulted during induction — the
compiler is the only oracle.

After convergence, the discovered taxonomy is audited against FDA (Jan 2025),
NHS RCR (Nov 2024), and EU AI Act (2024) requirements. This comparison is
done last and is never consulted during induction.

Run:
    python examples/epic/run_induction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_workspace / "python"))          # noethers_turnstile source
sys.path.insert(0, str(Path(__file__).resolve().parent))  # adapter.*, experiment.*

from experiment.induction import (
    run_induction,
    run_convergence_check,
    run_generalization_check,
)
from experiment.fda_nhs_audit import run_audit

_DIV  = "─" * 72
_DIV2 = "═" * 72


def _perm_label(s: str) -> str:
    labels = {
        "DIA": "DIA (document exists)",
        "REV": "REV (expert review only)",
        "AEX": "AEX (experiment authorized)",
        "ALR": "ALR (limited rollout)",
        "AAA": "AAA (full authority)",
        "EXP": "EXP (expired)",
        "OOC": "OOC (out of class)",
    }
    return labels.get(s, s)


def main() -> None:
    print()
    print(_DIV2)
    print("MED-IND-001: Empty Taxonomy Experiment")
    print("Gap Discovery in Medical AI from First Principles")
    print(_DIV2)
    print()
    print("Starting with v0 profile: two structural gaps only.")
    print("  - approximation_quality_gap  (is the model's output meaningful at all?)")
    print("  - freshness_gap              (were the inputs current at inference time?)")
    print()
    print("No domain knowledge consulted. Cases drive discovery.")
    print("FDA / NHS / EU AI Act comparison held until the end.")
    print()

    # ── Phase 1: Induction ────────────────────────────────────────────────────
    print(_DIV2)
    print("PHASE 1: INDUCTION TRACE")
    print(_DIV2)

    state, trace = run_induction()

    for rec in trace:
        if rec["phase"] == "positive_control":
            print(f"\n[POSITIVE CONTROL]  Case {rec['case_id']}  (profile: {rec['profile']})")
            agreed = rec["compiler_output"] == rec["expert_judgment"]
            mark = "✓" if agreed else "✗"
            print(f"  {mark}  compiler={_perm_label(rec['compiler_output'])}  "
                  f"expert={_perm_label(rec['expert_judgment'])}")
            print(f"     {rec['note'][:120]}...")
        else:
            print(f"\n[INDUCTION STEP]  Case {rec['case_id']}  "
                  f"(profile: {rec['profile_before']} → {rec['profile_after']})")
            print(f"  System: {rec['description']}")
            if rec["over_authorized"]:
                print(f"  ✗  OVER-AUTHORIZED: compiler={_perm_label(rec['compiler_output'])}  "
                      f"expert={_perm_label(rec['expert_judgment'])}")
                if rec["gap_induced"]:
                    print(f"     GAP INDUCED: {rec['gap_induced']}")
                    print(f"     Profile advances to {rec['profile_after']}")
            else:
                print(f"  ✓  compiler={_perm_label(rec['compiler_output'])}  "
                      f"expert={_perm_label(rec['expert_judgment'])}")

    print()
    print(f"Induction complete. Converged at profile {state.version_str()}.")
    print(f"Gaps discovered ({len(state.induced_gaps)}):")
    for i, gap in enumerate(state.induced_gaps, 1):
        print(f"  {i}. {gap}")

    # ── Phase 2: Convergence check ────────────────────────────────────────────
    print()
    print(_DIV2)
    print("PHASE 2: CONVERGENCE CHECK (all induction cases against converged taxonomy)")
    print(_DIV2)
    print(f"Profile: {state.version_str()}")
    print("Criterion: compiler no longer over-authorizes on any induction case.")
    print()

    conv_records = run_convergence_check(state)
    all_converged = True
    for rec in conv_records:
        mark = "✓" if rec["converged"] else "✗ STILL OVER-AUTHORIZING"
        print(f"  Case {rec['case_id']:4s}  [{mark}]  "
              f"compiler={rec['compiler_output']:4s}  expert={rec['expert_judgment']}")
        if not rec["converged"]:
            all_converged = False

    print()
    if all_converged:
        print("  CONVERGENCE: PASS — no over-authorization on any induction case.")
    else:
        print("  CONVERGENCE: FAIL — further induction needed.")

    # ── Phase 3: Generalization ───────────────────────────────────────────────
    print()
    print(_DIV2)
    print("PHASE 3: GENERALIZATION (held-out cases not used in induction)")
    print(_DIV2)
    print(f"Profile: {state.version_str()}")
    print()

    gen_records = run_generalization_check(state)
    gen_no_over_auth = all(not r["over_authorized"] for r in gen_records)
    gen_full_agree   = all(r["agreement"] for r in gen_records)

    for rec in gen_records:
        if rec["over_authorized"]:
            mark = "✗ OVER-AUTHORIZED"
        elif rec["agreement"]:
            mark = "✓ AGREE"
        else:
            mark = "~ SAFE (no over-auth; compiler conservative)"
        print(f"  Case {rec['case_id']:4s}  [{mark}]  "
              f"compiler={rec['compiler_output']:4s}  expert={rec['expert_judgment']}")
        print(f"         {rec['description'][:70]}")
        print()

    print()
    if gen_no_over_auth:
        print("  GENERALIZATION: PASS — no over-authorization on held-out cases.")
    else:
        print("  GENERALIZATION: FAIL — over-authorization on held-out cases.")

    # ── Phase 4: FDA / NHS / EU AI Act audit ──────────────────────────────────
    print()
    print(_DIV2)
    print("PHASE 4: POST-HOC REGULATORY AUDIT")
    print("(FDA Jan 2025, NHS RCR Nov 2024, EU AI Act 2024)")
    print("This comparison was NOT consulted during induction.")
    print(_DIV2)
    print()

    audit = run_audit(state)

    print(f"Discovered gaps ({len(audit['discovered_gaps'])}):")
    for g in audit["discovered_gaps"]:
        print(f"  • {g}")
    print()

    last_source = None
    for cov in audit["coverage"]:
        if cov["source"] != last_source:
            print(f"  ── {cov['source']} ──")
            last_source = cov["source"]
        mark = "✓" if cov["covered"] else "✗ NOT COVERED"
        matched = ", ".join(cov["matched_gaps"]) if cov["matched_gaps"] else "—"
        print(f"  [{mark}]  {cov['req_id']:8s} {cov['section']:12s}  matched: {matched}")
        print(f"            {cov['description'][:72]}")
        if cov["notes"]:
            print(f"            NOTE: {cov['notes'][:90]}")
        print()

    if audit["novel_gaps"]:
        print("  Novel gaps (no direct regulatory analog):")
        for g in audit["novel_gaps"]:
            print(f"    • {g}")
        print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(_DIV2)
    print("SUMMARY")
    print(_DIV2)
    print()
    s = audit["summary"]
    print(f"  Induction steps:        {len(state.induced_gaps)}")
    print(f"  Gaps discovered:        {len(state.induced_gaps)}")
    for g in state.induced_gaps:
        print(f"    • {g}")
    print()
    print(f"  Convergence check:      {'PASS' if all_converged else 'FAIL'}")
    print(f"  Generalization:         {'PASS (no over-auth)' if gen_no_over_auth else 'FAIL'}"
          + (f" / full agreement: {'yes' if gen_full_agree else 'partial'}" if gen_no_over_auth else ""))
    print()
    print(f"  Regulatory coverage:    {s['covered']}/{s['total_requirements']} "
          f"requirements ({s['coverage_pct']}%)")
    print(f"  Uncovered requirements: {s['uncovered']}")
    if audit["uncovered_requirements"]:
        for req_id in audit["uncovered_requirements"]:
            print(f"    • {req_id}")
    print(f"  Novel gaps:             {s['novel_gaps']}")
    print()

    if all_converged and gen_no_over_auth:
        print("  RESULT: The compiler-guided induction discovered a taxonomy that:")
        print("    1. Converges — no over-authorization on induction cases after discovery.")
        print("    2. Generalizes — no over-authorization on held-out cases.")
        print(f"   3. Covers {s['coverage_pct']}% of FDA/NHS/EU AI Act requirements")
        print("      — without ever consulting those guidelines during induction.")
        print()
        print("  The taxonomy was discovered purely from compiler feedback on deployment")
        print("  failures. The regulatory alignment is a post-hoc finding, not an input.")
    else:
        if not all_converged:
            print("  RESULT: Taxonomy did not converge — further induction needed.")
        if not gen_no_over_auth:
            failing = [r["case_id"] for r in gen_records if r["over_authorized"]]
            print(f"  RESULT: Over-authorization on held-out cases: {failing}")
    print()


if __name__ == "__main__":
    main()
