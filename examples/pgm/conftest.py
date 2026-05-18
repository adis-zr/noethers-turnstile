"""Pytest configuration for the pgm example.

Inserts the workspace turnstile source ahead of any installed wheel so that
tests always run against the local build.  This prevents stale-wheel failures
when the installed package lags behind the source tree.
"""
import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))
