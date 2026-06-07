"""CRED-IND-001: Credit Adverse Action Experiment — run and report.

Starting from a structural skeleton (v0: approximation_quality + freshness),
the compiler converges on a gap taxonomy through case-by-case falsification.
No regulatory knowledge is consulted during induction — the compiler is the
only oracle. CFPB / ECOA comparison is held until the end.

Run from the repository root:
    python examples/credit/run_credit_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))          # noethers_turnstile
sys.path.insert(0, str(Path(__file__).resolve().parent))  # experiment.*

from experiment.induction import (
    run_induction,
    run_convergence_check,
    run_generalization_check,
)
from experiment.cfpb_audit import run_audit

_DIV  = "─" * 72
_DIV2 = "═" * 72


def _perm_label(s: str) -> str:
    # Labels in both the native credit chain and the historical default-chain
    # names — accepts either, since reports and traces may stringify either
    # form depending on the field.
    labels = {
        # Native credit chain
        "REFUSE":                "REFUSE (no authorization)",
        "MODEL_EXISTS":          "MODEL_EXISTS (output produced, nothing else known)",
        "EXPERT_REVIEW":         "EXPERT_REVIEW (approximation quality bounded)",
        "EXPERIMENT_AUTHORIZED": "EXPERIMENT_AUTHORIZED (structural skeleton OK)",
        "LIMITED_ROLLOUT":       "LIMITED_ROLLOUT (induced gaps bounded)",
        "FULL_AUTHORITY":        "FULL_AUTHORITY",
        # Historical default-chain names (still appear in case library's
        # expert_judgment strings).
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
    print("CRED-IND-001: Credit Adverse Action Experiment")
    print("Blind Recovery of reason_traceability_gap from ECOA Failure Patterns")
    print(_DIV2)
    print()
    print("Starting with v0 profile: two structural gaps only.")
    print("  - approximation_quality_gap  (is the model's output meaningful at all?)")
    print("  - freshness_gap              (were the inputs current at inference time?)")
    print()
    print("No regulatory knowledge consulted during induction.")
    print("CFPB / ECOA comparison held until Phase 4.")
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
    print("PHASE 2: CONVERGENCE CHECK")
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
        print("  CONVERGENCE: PASS")
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

    if gen_no_over_auth:
        print("  GENERALIZATION: PASS — no over-authorization on held-out cases.")
    else:
        print("  GENERALIZATION: FAIL")

    # ── Phase 4: CFPB / ECOA blind audit ─────────────────────────────────────
    print()
    print(_DIV2)
    print("PHASE 4: CFPB / ECOA BLIND AUDIT")
    print("(ECOA § 1691(d), Regulation B § 1002.9, CFPB Circular 2022-03)")
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
        covered_mark = "✓" if cov["covered"] else "○"
        matched = ", ".join(cov["matched_gaps"]) if cov["matched_gaps"] else "—"
        cls = cov["classification"]
        print(f"  [{covered_mark}]  {cov['req_id']:20s}  [{cls}]  matched: {matched}")
        print(f"       {cov['description'][:72]}")
        if cov["notes"]:
            # Print notes wrapped at 70 chars
            words = cov["notes"].split()
            line = "       NOTE: "
            for w in words:
                if len(line) + len(w) + 1 > 80:
                    print(line)
                    line = "             " + w
                else:
                    line += (" " if line.strip() != "NOTE:" else "") + w
            if line.strip():
                print(line)
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
    print(f"  Generalization:         {'PASS (no over-auth)' if gen_no_over_auth else 'FAIL'}")
    print()
    print(f"  CFPB/ECOA requirements matched:  {s['covered']}/{s['total_requirements']} "
          f"({s['coverage_pct']}%)")
    print(f"  COMPILER_PERMISSIVE items:        {s['permissive_items']}")
    print(f"    (real regulatory obligations outside the evidence induction can reach)")
    print()

    if all_converged and gen_no_over_auth:
        print("  RESULT: The compiler-guided induction:")
        print("    1. Converges — no over-authorization on induction cases after discovery.")
        print("    2. Generalizes — no over-authorization on held-out cases.")
        print(f"   3. Recovers {s['coverage_pct']}% of CFPB/ECOA requirements without")
        print("      consulting those guidelines during induction.")
        print()
        print("  The regulatory alignment is a post-hoc finding, not an input.")
        print("  The compiler induced reason_traceability_gap from the evidence")
        print("  structure alone. ECOA named the same requirement independently.")
    print()


if __name__ == "__main__":
    main()
