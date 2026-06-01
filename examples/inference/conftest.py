"""Pytest configuration for the inference experiments.

Ensures the workspace noethers_turnstile is on the path.
"""
import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

_ISING = Path(__file__).resolve().parent / "ising"
if str(_ISING) not in sys.path:
    sys.path.insert(0, str(_ISING))
