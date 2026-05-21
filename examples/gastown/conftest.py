"""Pytest configuration for the gastown benchmark.

Inserts the workspace noethers_turnstile source ahead of any installed wheel so
that tests always run against the local build.
"""
import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

_GASTOWN = Path(__file__).resolve().parent
if str(_GASTOWN) not in sys.path:
    sys.path.insert(0, str(_GASTOWN))
