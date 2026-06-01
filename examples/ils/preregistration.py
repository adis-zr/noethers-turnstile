"""Write and seal the pre-registration file before any FAA document is opened.

The pre-registration records:
  - All geometric derivations (from geometry.py constants only)
  - Predicted compiler classifications for each FAA category
  - The RVR transition boundary predicted from geometry

This file must be written BEFORE faa_comparison.py is run.
The seal is a SHA-256 hash of the file contents, written to a .seal file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

from geometry import preregistration_values

PREREG_FILE  = Path(__file__).parent / "preregistration.json"
SEAL_FILE    = Path(__file__).parent / "preregistration.seal"


def build_record() -> dict:
    geo = preregistration_values()
    return {
        "protocol": "ils-blind-audit-v1",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "geometry": geo,
        "predicted_classifications": {
            "cat_i": {
                "description": "Standard ILS approach, DH=200 ft",
                "predicted": geo["predicted_cat1_classification"],
                "rationale": (
                    "f2 floor from geometry equals RVR 1800 ft (at DH ~197 ft); "
                    "compiler boundary expected to coincide with FAA CAT I minimum. "
                    "If EXACT: compiler recovered the boundary from geometry alone."
                ),
            },
            "cat_ii": {
                "description": "Precision approach, DH=100 ft",
                "predicted": geo["predicted_cat2_classification"],
                "rationale": (
                    "DH=100 ft is below saturation (~102 ft); f2 saturates (roll bar "
                    "already passed at DH). Compiler has no visual evidence axis to "
                    "constrain RVR. FAA CAT II RVR minimum is on a different axis "
                    "(human factors / reaction time at 4.3 sec to threshold), not "
                    "derivable from the physical geometry available to the compiler."
                ),
            },
            "cat_iiia": {
                "description": "Autoland, DH ≤ 100 ft",
                "predicted": geo["predicted_cat3a_classification"],
                "rationale": (
                    "Autoland certification evidence is structurally orthogonal to "
                    "RVR measurements. The compiler's evidence space (gap tokens) "
                    "cannot speak to autoland reliability. Compiler will be permissive "
                    "relative to any positive RVR minimum FAA imposes."
                ),
            },
            "cat_iiib": {
                "description": "Autoland, no DH, reduced RVR",
                "predicted": geo["predicted_cat3b_classification"],
                "rationale": (
                    "Same as CAT IIIa: autoland certification is orthogonal evidence. "
                    "Compiler has no basis for any positive RVR floor."
                ),
            },
            "cat_iiic": {
                "description": "Zero-zero, no DH, no RVR minimum",
                "predicted": geo["predicted_cat3c_classification"],
                "rationale": (
                    "Zero-zero: FAA imposes no RVR minimum. Compiler also imposes none "
                    "(f2 saturated, no visual evidence axis). COMPILER_PERMISSIVE in "
                    "the sense that the boundary is structurally absent on both sides."
                ),
            },
        },
        "sweep_predictions": {
            "sweep_a_f3_absent": {
                "description": "f3 absent — sub-CAT-I authorization not present",
                "predicted_transition_rvr_ft": geo["predicted_sweep_a_transition_rvr_ft"],
                "predicted_sub_boundaries": geo["predicted_sweep_b_sub_boundaries"],
                "explanation": (
                    "Sweep A: f3 absent. At RVR >= ~1800 ft (geometric floor at DH ~197 ft), "
                    "f2 clears and compiler grants LAND_MANUAL. Below that, drops to "
                    "DESCEND_TO_DH. The precise transition RVR is the geometric floor "
                    "at DH=200 ft, computed before any FAA document is opened."
                ),
            },
            "sweep_b_f3_present": {
                "description": "f3 present — sub-CAT-I authorization token provided",
                "explanation": (
                    "Sweep B: f3 present. With f3, compiler can reach LAND_ASSISTED "
                    "and LAND_ZERO_ZERO (f2 not required for those profiles). "
                    "The permission chain collapses differently: LAND_ZERO_ZERO "
                    "available from the top of the sweep, since f1+f3 suffice. "
                    "No RVR-dependent transition expected in Sweep B — compiler "
                    "holds at LAND_ZERO_ZERO regardless of RVR, because f2 is "
                    "not required for that profile."
                ),
            },
        },
        "architectural_claim": (
            "The ILS framework is architecturally different from 3GPP. "
            "In 3GPP, the compiler recovered all boundaries from a single evidence axis "
            "(mean-like SNR vs worst-case error floor). "
            "In ILS, the compiler recovers the CAT I physical floor (EXACT) but cannot "
            "recover CAT II/III boundaries — those require evidence types orthogonal to "
            "RVR geometry (human factors certification, autoland qualification). "
            "This is a COMPILER_PERMISSIVE failure, not an OFFSET: the evidence axis "
            "is wrong, not merely the threshold on a shared axis. "
            "Predicted before any FAA document is consulted."
        ),
    }


def seal(record: dict) -> str:
    content = json.dumps(record, indent=2, sort_keys=True)
    digest = hashlib.sha256(content.encode()).hexdigest()
    return digest


def write_preregistration() -> Path:
    if PREREG_FILE.exists():
        raise FileExistsError(
            f"{PREREG_FILE} already exists. "
            "Delete it explicitly if you intend to re-run pre-registration."
        )
    if SEAL_FILE.exists():
        raise FileExistsError(
            f"{SEAL_FILE} already exists."
        )

    record = build_record()
    content = json.dumps(record, indent=2, sort_keys=True)
    digest = hashlib.sha256(content.encode()).hexdigest()

    PREREG_FILE.write_text(content)
    SEAL_FILE.write_text(f"{digest}  preregistration.json\n")

    return PREREG_FILE


def verify_seal() -> bool:
    if not PREREG_FILE.exists() or not SEAL_FILE.exists():
        return False
    content = PREREG_FILE.read_text()
    digest = hashlib.sha256(content.encode()).hexdigest()
    seal_line = SEAL_FILE.read_text().strip()
    expected = seal_line.split()[0]
    return digest == expected


if __name__ == "__main__":
    try:
        path = write_preregistration()
        print(f"Pre-registration sealed: {path}")
        print(f"Seal file: {SEAL_FILE}")
        digest = SEAL_FILE.read_text().strip()
        print(f"SHA-256: {digest}")
    except FileExistsError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
