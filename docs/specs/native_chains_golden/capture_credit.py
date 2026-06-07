"""Phase 0 golden capture for credit — induction + held-out emit table.

Runs the induction state machine through all ALL_CASES (induction + held-out)
at each induction state version, capturing the case-level emit. The
post-rewrite verification asserts old_emit ↔ new_emit per the §7.2 credit
bijection table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "credit"))

import noethers_turnstile as t  # noqa: E402

from experiment.cases import ALL_CASES  # noqa: E402
from experiment.compiler import compile_case  # noqa: E402
from experiment.induction import run_induction  # noqa: E402


def capture() -> list[dict]:
    rows = []
    # Capture the v0 baseline (pre-induction) for each case.
    from experiment.profile import InductionState
    v0 = InductionState()
    for case in ALL_CASES:
        perm = compile_case(case, v0)
        rows.append({
            "case_id": case["case_id"],
            "state_version": "v0",
            "old_chain_emit": perm.as_str() if hasattr(perm, "as_str") else str(perm),
        })

    # Now run the induction and capture per-step state.
    final_state, _audit = run_induction()
    for case in ALL_CASES:
        perm = compile_case(case, final_state)
        rows.append({
            "case_id": case["case_id"],
            "state_version": final_state.version_str(),
            "old_chain_emit": perm.as_str() if hasattr(perm, "as_str") else str(perm),
        })
    return rows


def main() -> None:
    rows = capture()
    distinct_emits = sorted({r["old_chain_emit"] for r in rows})
    out = {
        "example": "credit",
        "n_rows": len(rows),
        "distinct_emits_seen": distinct_emits,
        "rows": rows,
    }
    out_path = Path(__file__).resolve().parent / "credit.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {out_path}")
    print(f"  rows: {len(rows)}")
    print(f"  distinct old-chain emits: {distinct_emits}")


if __name__ == "__main__":
    main()
