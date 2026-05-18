"""Deterministic fingerprinting for PGM objects.

Copied from ecds-pgm/ecds_pgm/fingerprints.py — no external dependencies.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def fingerprint(obj: Any) -> str:
    """Full SHA-256 hex digest (64 chars) of stable JSON.

    64 hex = 256-bit collision resistance. Truncating to 16 chars (64-bit)
    risks birthday collisions at production token-registry scale.
    """
    return hashlib.sha256(_stable_json(obj).encode()).hexdigest()


def fingerprint_graph(graph_dict: dict) -> str:
    return fingerprint(graph_dict)


def fingerprint_query(query_dict: dict) -> str:
    return fingerprint(query_dict)


def fingerprint_evidence(evidence_dict: dict) -> str:
    return fingerprint(evidence_dict)
