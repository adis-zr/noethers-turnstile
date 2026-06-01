"""MED-STR-001: Stress tests — adversarial attacks, TCB corruption, tamper resistance.

Experiment 1 (A1–A10): Adversarial synthetic cases
  Ten attack vectors against the converged v6 profile. BREAKS or BLOCKED.

Experiment 2 (2a/2b): Hidden gap / blindness tests
  2a: Falsified statuses — dishonest submitter replaces OPEN with 'bounded'.
  2b: Omitted gaps — absent under v6 = open = blocked; absent under v0 = invisible.
  Confirms the induction loop's blindness is genuine.

Experiment 3 (T1–T6): TCB corruption surface
  What the compiler accepts on faith. Maps the epistemological boundary.

Experiment 4 (R1–R6): Tamper resistance under composition
  Composed laundering, profile version rollback, cross-context replay,
  coordinated multi-field attacks. Tests structural properties under adversarial
  composition inputs.

Run:
    python examples/epic/run_stress.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_workspace / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from experiment.stress.adversarial       import run_all_attacks
from experiment.stress.hidden_gaps       import run_all_hidden_gap_experiments
from experiment.stress.tcb_corruption    import run_all_tcb_experiments
from experiment.stress.tamper_resistance import run_all_tamper_experiments

_DIV  = "─" * 72
_DIV2 = "═" * 72


def main() -> None:
    print()
    print(_DIV2)
    print("MED-STR-001: Stress Tests")
    print("Adversarial Attacks and Hidden Gap Experiments")
    print(_DIV2)

    # ── Experiment 1: Adversarial attacks ─────────────────────────────────────
    print()
    print(_DIV2)
    print("EXPERIMENT 1: ADVERSARIAL ATTACKS")
    print("Ten attack vectors against the converged v6 profile.")
    print(_DIV2)

    attacks = run_all_attacks()

    breaks_count = sum(1 for a in attacks if a.breaks)
    blocked_count = sum(1 for a in attacks if not a.breaks)

    for a in attacks:
        mark = "✗ BREAKS " if a.breaks else "✓ BLOCKED"
        print(f"\n[{a.attack_id}] {a.description}")
        print(f"  Strategy:   {a.strategy}")
        print(f"  Result:     [{mark}]  compiler={a.compiler_output}  "
              f"expected_if_defended={a.expected_if_defended}")
        print(f"  Mechanism:  {a.mechanism}")
        print(f"  Verdict:    {a.verdict}")

    print()
    print(_DIV)
    print(f"  ATTACKS THAT BREAK THE COMPILER:  {breaks_count}/{len(attacks)}")
    print(f"  ATTACKS BLOCKED BY THE COMPILER:  {blocked_count}/{len(attacks)}")
    print()

    breaking = [a for a in attacks if a.breaks]
    if breaking:
        print("  BREAK SURFACE:")
        for a in breaking:
            print(f"    [{a.attack_id}] {a.description}")
            print(f"           {a.mechanism}")
    print()
    blocked = [a for a in attacks if not a.breaks]
    if blocked:
        print("  DEFENDED SURFACE:")
        for a in blocked:
            print(f"    [{a.attack_id}] {a.description}")
            print(f"           {a.mechanism}")

    # ── Experiment 2a: Falsified statuses ─────────────────────────────────────
    print()
    print(_DIV2)
    print("EXPERIMENT 2a: FALSELY OPTIMISTIC STATUSES (dishonest submitter)")
    print("Replace each case's OPEN blocking gaps with 'bounded'.")
    print("Does the compiler over-authorize when given dishonest inputs?")
    print(_DIV2)

    results_2a, results_2b = run_all_hidden_gap_experiments()

    breaks_2a = sum(1 for r in results_2a if r.over_authorized)
    blocked_2a = sum(1 for r in results_2a if not r.over_authorized)

    for r in results_2a:
        mark = "✗ BREAKS " if r.over_authorized else "✓ BLOCKED"
        print(f"\n  Case {r.case_id}: {r.description[:60]}")
        print(f"  Normal output: {r.original_output}  →  After falsification: {r.modified_output}")
        print(f"  [{mark}]  Expert: {r.expert_judgment}")
        print(f"  {r.modification}")
        print(f"  Finding: {r.finding[:120]}")

    print()
    print(_DIV)
    print(f"  CASES WHERE FALSIFICATION BREAKS COMPILER:   {breaks_2a}/{len(results_2a)}")
    print(f"  CASES WHERE COMPILER STILL BLOCKED:          {blocked_2a}/{len(results_2a)}")

    # ── Experiment 2b: Omitted gaps ───────────────────────────────────────────
    print()
    print(_DIV2)
    print("EXPERIMENT 2b: OMITTED GAP ENTRIES (genuine blindness test)")
    print("Remove blocking gap entries entirely from gap_statuses.")
    print("v6 state: absent → defaults to open → correctly blocks ALR")
    print("v0 state: absent → not in taxonomy → invisible → ALR correctly emitted")
    print(_DIV2)

    for r in results_2b:
        print(f"\n  Case {r.case_id}: {r.description[:60]}")
        print(f"  Normal (v6): {r.original_output}  |  {r.modification}")
        print(f"  {r.finding}")

    print()
    print(_DIV)

    # ── Experiment 3: TCB corruption ──────────────────────────────────────────
    print()
    print(_DIV2)
    print("EXPERIMENT 3: TCB CORRUPTION SURFACE (T1–T6)")
    print("What the compiler accepts on faith — the epistemological boundary.")
    print(_DIV2)

    tcb_results = run_all_tcb_experiments()

    for r in tcb_results:
        mark = "✓ DETECTED  " if r.detected else "✗ UNDETECTED"
        print(f"\n[{r.vector_id}] {r.description}")
        print(f"  Corruption:   {r.corruption[:90]}")
        print(f"  [{mark}]  output={r.compiler_output}")
        print(f"  TCB surface:  {r.tcb_surface[:90]}")
        print(f"  Finding:      {r.finding[:100]}")
        print(f"  Implication:  {r.implication[:100]}")

    n_detected   = sum(1 for r in tcb_results if r.detected)
    n_undetected = sum(1 for r in tcb_results if not r.detected)
    print()
    print(_DIV)
    print(f"  DETECTED by compiler:        {n_detected}/{len(tcb_results)}")
    print(f"  UNDETECTED (accepted faith): {n_undetected}/{len(tcb_results)}")

    # ── Experiment 4: Tamper resistance ───────────────────────────────────────
    print()
    print(_DIV2)
    print("EXPERIMENT 4: TAMPER RESISTANCE UNDER COMPOSITION (R1–R6)")
    print("Composed laundering, profile rollback, cross-context replay,")
    print("coordinated multi-field attacks.")
    print(_DIV2)

    tamper_results = run_all_tamper_experiments()

    for r in tamper_results:
        mark = "✓ HOLDS   " if r.theorem_holds else "✗ GAP     "
        print(f"\n[{r.attack_id}] {r.description}")
        print(f"  Strategy:   {r.strategy[:80]}")
        print(f"  Predicted:  {r.predicted[:80]}")
        print(f"  [{mark}]  output={r.compiler_output[:60]}")
        print(f"  Finding:    {r.finding[:100]}")
        print(f"  Governance: {r.governance_implication[:100]}")

    n_holds = sum(1 for r in tamper_results if r.theorem_holds)
    n_gaps  = sum(1 for r in tamper_results if not r.theorem_holds)
    print()
    print(_DIV)
    print(f"  Structural properties hold: {n_holds}/{len(tamper_results)}")
    print(f"  Governance gaps (not theorem violations): {n_gaps}/{len(tamper_results)}")

    # ── Overall boundary map ──────────────────────────────────────────────────
    print()
    print(_DIV2)
    print("COMPILER BOUNDARY MAP")
    print(_DIV2)
    print()
    print("  ENFORCED BY CONSTRUCTION (compiler cannot be bypassed):")
    print("    • Provenance hash — token valid only for exact (claim, candidate, context, use)")
    print("    • Token status — invalid tokens ignored regardless of claims")
    print("    • Expiry — expired tokens floor judgment to EXP")
    print("    • Authority ceiling — meet(ceiling, judgment); unforgeable")
    print("    • Non-promotion under composition — composed ≤ min(components)")
    print("    • Empty profile floor — no profiles → OOC regardless of gap statuses")
    print("    • Absent gap default — gap absent from context → treated as open")
    print()
    print("  ACCEPTED ON FAITH (TCB — requires governance outside the compiler):")
    print("    • Gap status truthfulness — status strings are caller-asserted")
    print("    • Numerical bound values — stored but not compared against floors at profile level")
    print("    • Token type / gap compatibility — any valid token can close any gap")
    print("    • Scientific validity — correct form ≠ correct science")
    print("    • Membership classification — InClass/OutOfClass is caller-asserted")
    print("    • Schema version binding — deprecated contracts accepted")
    print("    • Profile version — caller chooses which profile to apply; no version registry")
    print("    • Context_id versioning — fingerprint change alone does not invalidate tokens")
    print()
    print("  GOVERNANCE OBLIGATIONS (outside compiler, required for system integrity):")
    print("    • Certifiers must produce tokens; bridge authors must not hand-write statuses")
    print("    • Detail contract registry should enforce token type / gap compatibility")
    print("    • Profile version registry must reject deprecated profiles at context construction")
    print("    • Context_id must change when evidence-invalidating deployment changes occur")
    print("    • Sample size, population independence, pre-registration: certifier obligations")
    print()


if __name__ == "__main__":
    main()
