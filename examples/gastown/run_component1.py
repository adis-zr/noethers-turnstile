"""Run Component 1 synthetic corpus through the adapter and evaluator.

Produces aggregate statistics for pre-registration derivation.

Usage:
    python run_component1.py

Output:
    - corpus/component1/results.json   (machine-readable aggregate)
    - Printed summary table
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────

_GASTOWN = Path(__file__).resolve().parent
sys.path.insert(0, str(_GASTOWN))
sys.path.insert(0, str(_GASTOWN.parents[1] / "python"))

# ── Imports ────────────────────────────────────────────────────────────────────

from corpus.generator.skeleton import generate_component1_corpus, CORPUS_TARGETS
from adapter.otel_adapter import process_trace
from harness.evaluator import classify_verdict, detect_compiler_bug, PERM_ORDINAL

_NOW = time.time()

# ── Label → evaluator expected dict ───────────────────────────────────────────

def _label_to_expected(lbl) -> dict:
    return {
        "permission": lbl.expected_permission,
        "max_acceptable_permission": lbl.max_acceptable_permission,
        "ceiling_blocked_permission": lbl.ceiling_blocked_permission,
        "control_outcome_acceptable": lbl.control_outcome_acceptable,
        "ground_truth_label": "SOUND" if lbl.ground_truth_sound else "UNSOUND",
    }


# ── Run ────────────────────────────────────────────────────────────────────────

def run_component1():
    print("Generating Component 1 corpus...")
    corpus = generate_component1_corpus(base_ts=_NOW - 7200)
    print(f"  {len(corpus)} traces generated")

    # Accumulators
    verdict_counts: dict[str, int] = defaultdict(int)
    perm_counts: dict[str, int] = defaultdict(int)
    gap_status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    gap_by_family: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    perm_by_family: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures: list[dict] = []
    total_judgments = 0

    for lt in corpus:
        family = lt.label.pattern_family
        judgments = process_trace(
            lt.trace,
            now_unix=_NOW,
            bead_type=lt.bead_type,
            token_registry=lt.token_registry,
        )

        if not judgments:
            verdict_counts["ADAPTER_FAILURE"] += 1
            failures.append({"family": family, "reason": "no judgments"})
            continue

        for j in judgments:
            total_judgments += 1
            emitted = str(j.permission)
            perm_counts[emitted] += 1
            perm_by_family[family][emitted] += 1

            # Gap status
            for gap_id, status in j.gap_states.items():
                gap_status[gap_id][status] += 1
                gap_by_family[family][gap_id][status] += 1

            # Compiler bug check
            bug = detect_compiler_bug(
                emitted_perm=emitted,
                gap_states=j.gap_states,
                raised_exception=None,
                authority_ceiling=None,
            )

            result = classify_verdict(
                emitted_perm=emitted,
                expected=_label_to_expected(lt.label),
                compiler_bug_detected=(bug is not None),
                wrong_mechanism=False,
                track="C1",
                gap_states=j.gap_states,
            )
            verdict_counts[result["verdict"]] += 1

            if result["verdict"] in ("UNSOUND_MISSED", "COMPILER_BUG", "ADAPTER_FAILURE"):
                failures.append({
                    "family": family,
                    "verdict": result["verdict"],
                    "emitted": emitted,
                    "expected": lt.label.expected_permission,
                })

    # ── CLEAN family statistics (the Monte Carlo prior) ──────────────────────

    clean_perms = perm_by_family.get("CLEAN", {})
    clean_total = sum(clean_perms.values())

    clean_gap_stats: dict[str, dict[str, float]] = {}
    for gap_id, statuses in gap_by_family.get("CLEAN", {}).items():
        gtotal = sum(statuses.values())
        clean_gap_stats[gap_id] = {
            s: round(c / gtotal * 100, 1) for s, c in statuses.items()
        } if gtotal else {}

    # ── Full corpus gap statistics ────────────────────────────────────────────

    all_gap_pct: dict[str, dict[str, float]] = {}
    for gap_id, statuses in gap_status.items():
        gtotal = sum(statuses.values())
        all_gap_pct[gap_id] = {
            s: round(c / gtotal * 100, 1) for s, c in statuses.items()
        } if gtotal else {}

    # ── Assemble output ───────────────────────────────────────────────────────

    results = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_traces": len(corpus),
        "total_judgments": total_judgments,
        "verdicts": dict(verdict_counts),
        "permission_distribution": dict(perm_counts),
        "permission_by_family": {f: dict(p) for f, p in perm_by_family.items()},
        "gap_status_distribution": {g: dict(s) for g, s in gap_status.items()},
        "gap_status_pct": all_gap_pct,
        "clean_family": {
            "total_judgments": clean_total,
            "permission_distribution": clean_perms,
            "permission_pct": {
                p: round(c / clean_total * 100, 1) for p, c in clean_perms.items()
            } if clean_total else {},
            "gap_status_pct": clean_gap_stats,
        },
        "failures": failures,
    }

    # ── Write ─────────────────────────────────────────────────────────────────

    out_path = _GASTOWN / "corpus" / "component1" / "results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path.relative_to(_GASTOWN.parent.parent)}")

    # ── Print summary ─────────────────────────────────────────────────────────

    _print_summary(results)
    return results


def _print_summary(r: dict):
    total = r["total_judgments"]

    print("\n" + "═" * 70)
    print("COMPONENT 1 RESULTS")
    print("═" * 70)
    print(f"  Traces: {r['total_traces']}   Judgments: {total}")

    print("\n── Verdict counts ──────────────────────────────────────────────────")
    for v in ["SOUND_CORRECT", "SOUND_MISSED", "UNSOUND_CAUGHT", "UNSOUND_MISSED",
              "TAXONOMY_GAP", "COMPILER_BUG", "ORDERING_VIOLATION", "ADAPTER_FAILURE"]:
        n = r["verdicts"].get(v, 0)
        bar = "█" * n if n <= 60 else "█" * 60 + f" …+{n-60}"
        print(f"  {v:<22} {n:4d}  {bar}")

    falsifications = r["verdicts"].get("UNSOUND_MISSED", 0) + r["verdicts"].get("COMPILER_BUG", 0)
    print(f"\n  Falsifications (target 0): {falsifications}")

    print("\n── Permission distribution (all judgments) ─────────────────────────")
    for perm in ["AAA", "ALR", "AEX", "ROL", "ESC", "ETA", "REV", "DIA", "UNS", "REF", "EXP", "OOC"]:
        n = r["permission_distribution"].get(perm, 0)
        if n:
            pct = round(n / total * 100, 1)
            bar = "█" * int(pct / 2)
            print(f"  {perm:<6} {n:4d}  ({pct:5.1f}%)  {bar}")

    cf = r["clean_family"]
    ct = cf["total_judgments"]
    if ct:
        print(f"\n── CLEAN family ({ct} judgments) — Monte Carlo prior ────────────────")
        for perm in ["AAA", "ALR", "AEX", "ROL", "ESC", "ETA", "REV", "DIA", "REF"]:
            n = cf["permission_distribution"].get(perm, 0)
            if n:
                pct = round(n / ct * 100, 1)
                bar = "█" * int(pct / 2)
                print(f"  {perm:<6} {n:4d}  ({pct:5.1f}%)  {bar}")

        print(f"\n── CLEAN gap status rates ──────────────────────────────────────────")
        for gap in ["context_integrity_gap", "delegation_authority_gap",
                    "completion_evidence_gap", "escalation_validity_gap",
                    "merge_safety_gap", "authority_chain_gap"]:
            short = gap.replace("_gap", "").replace("_", " ")[:26]
            statuses = cf["gap_status_pct"].get(gap, {})
            s = "  ".join(f"{k}={v:.0f}%" for k, v in sorted(statuses.items()))
            print(f"  {short:<28} {s}")

    if r["failures"]:
        print(f"\n── Failures ({len(r['failures'])}) ──────────────────────────────────────────")
        for f in r["failures"][:20]:
            print(f"  {f}")
        if len(r["failures"]) > 20:
            print(f"  ... and {len(r['failures']) - 20} more")

    print("\n── Permission by family ────────────────────────────────────────────")
    families = ["CLEAN", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8",
                "A1", "A2", "A3", "A4", "A5", "DIA", "AEX", "ROL"]
    print(f"  {'Family':<8} {'n':>4}  Permissions")
    for fam in families:
        perms = r["permission_by_family"].get(fam, {})
        n = sum(perms.values())
        if n:
            perm_str = "  ".join(f"{p}×{c}" for p, c in
                                  sorted(perms.items(), key=lambda x: -x[1]))
            print(f"  {fam:<8} {n:4d}  {perm_str}")

    print("═" * 70)


if __name__ == "__main__":
    run_component1()
