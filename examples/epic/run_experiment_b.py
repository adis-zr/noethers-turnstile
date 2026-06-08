"""Pre-Registration Experiment B — Held-out generalization.

Procedure (mirrors prereg_three_gaps.md §B):
  1. Run induction to convergence to get the frozen taxonomy.
  2. Score the three pre-registered held-out cases (H02 Boeing MCAS,
     H03 COVID-19 ML models, H04 Amazon recruiting) against the frozen taxonomy.
  3. Apply the B.0 rubric to independent assessment → permission level.
  4. Compare compiler output to independent-assessment level.
  5. Apply B.4 decision rule.

Independent assessment → permission level (B.0 rubric, fixed before run):
  H02 Boeing MCAS:
    FAA AD 2020-24-02 + House Transportation Committee report: MCAS was not
    authorized for autonomous action at its deployed authority level.
    → REV (system required human oversight that was absent; below ALR).
  H03 COVID-19 ML (Roberts et al. 2021):
    Systematic review: none of the ~300 models fit for clinical use.
    → DIA (no model met the threshold for deployment; REFUSE-equivalent).
  H04 Amazon recruiting:
    Reuters/Dastin 2018 + Amazon discontinuation: system not fit for action taken.
    → REV (deployment required human oversight; below ALR).

Decision rule (B.4):
  GENERALIZES: zero permissive disagreements AND agreements >= 2 of 3.
  BOUNDED: any permissive disagreement OR agreements < 2 of 3.
  Permissive disagreement = compiler level > independent assessment level.

Run:
    python examples/epic/run_experiment_b.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_workspace / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noethers_turnstile as t
from experiment.induction import run_induction
from experiment.compiler import compile_case

_DIV  = "─" * 72
_DIV2 = "═" * 72

# Permission total order (ascending) for comparison
_PERM_ORDER = ["OOC", "EXP", "REF", "UNS", "ETA", "ESC", "ROL", "DIA", "REV",
               "AEX", "ALR", "AAA"]

def _perm_rank(p: str) -> int:
    try:
        return _PERM_ORDER.index(p)
    except ValueError:
        return -1


# Pre-registered independent-assessment permission levels (B.0 rubric, fixed)
_INDEPENDENT_ASSESSMENT: dict[str, str] = {
    "H02": "REV",   # FAA AD 2020-24-02; House Committee report
    "H03": "DIA",   # Roberts et al. 2021 — none fit for clinical use
    "H04": "REV",   # Dastin 2018 + Amazon discontinuation
}

_CASE_SOURCES: dict[str, str] = {
    "H02": "FAA AD 2020-24-02; House Transportation Committee (Sept 2020); JATR (Oct 2019)",
    "H03": "Roberts et al. (2021), Nature Machine Intelligence — systematic review of ~300 models",
    "H04": "Dastin (2018), Reuters; Amazon discontinuation (internal confirmation)",
}


def main() -> None:
    print()
    print(_DIV2)
    print("PRE-REGISTRATION EXPERIMENT B — Held-out Generalization")
    print("prereg_three_gaps.md §B")
    print(_DIV2)
    print()
    print("Step 1: Run induction to convergence (frozen taxonomy).")
    print()

    state, _ = run_induction()

    print(f"Induction complete. Frozen taxonomy: {state.version_str()}")
    print(f"Gaps in taxonomy ({len(state.induced_gaps)}):")
    for g in state.induced_gaps:
        print(f"  • {g}")
    print()
    print("Taxonomy is now FROZEN. No gap may be added during this experiment.")
    print()

    # ── Held-out cases: filter to the three pre-registered cases ─────────────
    from experiment.cases import HELD_OUT_CASES
    target_ids = {"H02", "H03", "H04"}
    held_out = [c for c in HELD_OUT_CASES if c["case_id"] in target_ids]
    assert len(held_out) == 3, f"Expected 3 held-out cases, got {len(held_out)}"

    print(_DIV)
    print("Step 2: Score held-out cases against frozen taxonomy.")
    print(_DIV)
    print()

    results = []
    for case in held_out:
        cid = case["case_id"]
        compiler_out = str(compile_case(case, state))
        independent  = _INDEPENDENT_ASSESSMENT[cid]
        source       = _CASE_SOURCES[cid]

        compiler_rank    = _perm_rank(compiler_out)
        independent_rank = _perm_rank(independent)

        if compiler_rank == independent_rank:
            kind = "AGREEMENT"
        elif compiler_rank < independent_rank:
            kind = "CONSERVATIVE"  # compiler refuses more than assessor; safe direction
        else:
            kind = "PERMISSIVE"    # compiler allows more than assessor; dangerous

        results.append({
            "case_id":        cid,
            "description":    case["description"],
            "compiler":       compiler_out,
            "independent":    independent,
            "source":         source,
            "kind":           kind,
        })

        mark = {"AGREEMENT": "✓ AGREE", "CONSERVATIVE": "~ CONSERVATIVE", "PERMISSIVE": "✗ PERMISSIVE"}[kind]
        print(f"  Case {cid}  [{mark}]")
        print(f"    System:      {case['description']}")
        print(f"    Compiler:    {compiler_out}")
        print(f"    Independent: {independent}  ({source})")
        print()

    # ── Apply B.4 decision rule ───────────────────────────────────────────────
    print(_DIV)
    print("Step 3: Apply B.4 decision rule.")
    print(_DIV)
    print()

    agreements   = sum(1 for r in results if r["kind"] == "AGREEMENT")
    conservative = sum(1 for r in results if r["kind"] == "CONSERVATIVE")
    permissive   = sum(1 for r in results if r["kind"] == "PERMISSIVE")

    print(f"  Agreements:            {agreements} / 3")
    print(f"  Conservative disagree: {conservative}")
    print(f"  Permissive disagree:   {permissive}   ← must be 0 for GENERALIZES")
    print()

    if permissive == 0 and agreements >= 2:
        outcome = "GENERALIZES"
    else:
        outcome = "BOUNDED"

    print(f"  DECISION RULE OUTPUT:  {outcome}")
    print()

    # ── Outcome paragraph (pre-written, selected by decision rule) ────────────
    print(_DIV2)
    print(f"OUTCOME PARAGRAPH ({outcome})")
    print(_DIV2)
    print()

    if outcome == "GENERALIZES":
        print(f"> On 3 held-out cases not used in induction — Boeing 737 MAX MCAS,")
        print(f"> COVID-19 ML models (Roberts et al. 2021), and the Amazon recruiting")
        print(f"> algorithm — evaluated against pre-existing independent regulatory and")
        print(f"> investigative assessments (FAA AD 2020-24-02; Roberts et al.; Dastin 2018),")
        print(f"> the compiler agreed on {agreements} of 3 and never over-authorized: all")
        print(f"> disagreements were conservative, with the compiler refusing permissions")
        print(f"> the independent assessment would have allowed. The taxonomy was frozen")
        print(f"> during this evaluation; no gap was added. Three held-out cases with zero")
        print(f"> permissive disagreements is consistent with generalization beyond the")
        print(f"> induction set, but n = 3 is a bound on the strength of this claim: it")
        print(f"> rules out systematic over-authorization and confirms the taxonomy does")
        print(f"> not break on cases outside its induction domain, but does not establish")
        print(f"> generalization in the sense a larger held-out evaluation would.")
    else:
        permissive_cases = [r for r in results if r["kind"] == "PERMISSIVE"]
        case_names = "; ".join(f"{r['case_id']} ({r['description'][:40]})" for r in permissive_cases)
        mechanisms = "; ".join(
            f"{r['case_id']}: compiler={r['compiler']} > independent={r['independent']}"
            for r in permissive_cases
        )
        print(f"> The held-out evaluation locates a boundary of the taxonomy rather than")
        print(f"> confirming open-ended generalization. On 3 held-out cases evaluated")
        print(f"> against pre-existing independent assessments, the compiler agreed on")
        print(f"> {agreements}; produced {permissive} permissive disagreement(s).")
        print(f"> The permissive case(s) — {case_names} — failed through")
        print(f"> {mechanisms}, which no induced gap covers.")
        print(f"> The taxonomy therefore generalizes within the failure modes its induction")
        print(f"> set spans and stops at failure modes outside that span.")

    print()
    print(_DIV)
    print("Execution log fields (paste into prereg_three_gaps.md §B.6):")
    print(_DIV)
    print(f"  Gate decision:    Source 1 (pre-existing independent assessments)")
    print(f"  Held-out cases:   Boeing MCAS (H02), COVID-19 ML (H03), Amazon (H04)")
    print(f"  Source used:      FAA AD 2020-24-02; Roberts et al. 2021; Dastin 2018")
    print(f"  Agreements:       {agreements}")
    print(f"  Conservative:     {conservative}")
    print(f"  Permissive:       {permissive}")
    print(f"  Decision rule:    {outcome}")
    print(f"  Paragraph pasted: B.5-{outcome}")
    print(f"  Taxonomy version: {state.version_str()} (frozen, no changes during B)")
    per_case = "  |  ".join(
        f"{r['case_id']} compiler={r['compiler']} indep={r['independent']} [{r['kind']}]"
        for r in results
    )
    print(f"  Per-case:         {per_case}")
    print()


if __name__ == "__main__":
    main()
