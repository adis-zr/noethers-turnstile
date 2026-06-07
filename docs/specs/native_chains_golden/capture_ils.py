"""Phase 0 golden capture for ILS — pre-rewrite emit table.

Walks the same sweep grid as run_ils_audit.py and records (sweep, DH, RVR,
f1, f3, f2, permission) per cell. The post-rewrite verification will load
this golden, run the same grid against the new ILS chain, and assert that
old_emit ↔ new_emit per the §7.2 ILS bijection table.

Run from repo root:
    .venv/bin/python docs/specs/native_chains_golden/capture_ils.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "ils"))

import noethers_turnstile as t  # noqa: E402

from geometry import rvr_floor  # noqa: E402
from ils_compiler import compile_approach  # noqa: E402

RVR_MAX_FT = 2400
RVR_STEP_FT = 100
DHS_FT = [50.0, 100.0, 102.0, 150.0, 200.0]  # span CAT III..CAT I and the f2 saturation point


def capture() -> list[dict]:
    rows = []
    for dh in DHS_FT:
        geo = rvr_floor(dh)
        for f3_present in (False, True):
            for rvr_int in range(RVR_MAX_FT, -RVR_STEP_FT, -RVR_STEP_FT):
                rvr_ft = float(rvr_int)
                f2_clear = geo.saturated or (rvr_ft >= geo.rvr_floor_ft)
                judgment = compile_approach(
                    rvr_ft=rvr_ft,
                    dh_ft=dh,
                    f1_clear=True,
                    f3_present=f3_present,
                )
                rows.append({
                    "sweep_dh_ft": dh,
                    "rvr_ft": rvr_ft,
                    "f1_clear": True,
                    "f3_present": f3_present,
                    "f2_clear": f2_clear,
                    "old_chain_emit": judgment.permission_str,
                    "saturated": geo.saturated,
                    "rvr_floor_ft": geo.rvr_floor_ft,
                })
    return rows


def main() -> None:
    rows = capture()
    distinct_emits = sorted({r["old_chain_emit"] for r in rows})
    out = {
        "example": "ils",
        "capture_grid": {
            "dh_ft": DHS_FT,
            "rvr_ft": list(range(RVR_MAX_FT, -RVR_STEP_FT, -RVR_STEP_FT)),
            "f3_states": [False, True],
        },
        "n_rows": len(rows),
        "distinct_emits_seen": distinct_emits,
        "rows": rows,
    }
    out_path = Path(__file__).resolve().parent / "ils.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {out_path}")
    print(f"  rows: {len(rows)}")
    print(f"  distinct old-chain emits: {distinct_emits}")


if __name__ == "__main__":
    main()
