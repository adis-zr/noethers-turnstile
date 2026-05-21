"""GasTown seance — staleness certificate builder.

A seance staleness certificate satisfies the BOUNDED requirement for
context_integrity_gap when:
  - staleness_seconds ≤ 3600
  - commits_elapsed ≤ 10 (or -1 treated conservatively as failing)

The token type is "gt.seance_staleness_bound.v1".
Its closes_gaps list is ALWAYS empty (structural contract — seance can never
CLOSE context_integrity_gap, only BOUND it).
"""

from __future__ import annotations

import noethers_turnstile as t
from .provenance import compute_action_provenance_hash

# Staleness bounds (spec §1.3, "Profile conditions for context_integrity_gap BOUNDED")
_MAX_STALENESS_SECONDS = 3600
_MAX_COMMITS_ELAPSED = 10

# Staleness classification thresholds
_FRESH_THRESHOLD_SECONDS = 1200  # ≤ 20 min → FRESH
_STALE_THRESHOLD_SECONDS = 3600  # ≤ 1 hr and > 20 min → STALE; > 1 hr → COLD


def classify_staleness(staleness_seconds: float, commits_elapsed: int) -> str:
    """Classify seance staleness as FRESH, STALE, or COLD.

    FRESH: staleness_seconds ≤ 1200 AND commits_elapsed in [0, 10]
    STALE: staleness_seconds in (1200, 3600] AND commits_elapsed in [0, 10]
    COLD:  staleness_seconds > 3600 OR commits_elapsed > 10 OR commits_elapsed == -1
    """
    if commits_elapsed == -1 or commits_elapsed > _MAX_COMMITS_ELAPSED:
        return "COLD"
    if staleness_seconds > _MAX_STALENESS_SECONDS:
        return "COLD"
    if staleness_seconds <= _FRESH_THRESHOLD_SECONDS:
        return "FRESH"
    return "STALE"


def _is_within_bounds(staleness_seconds: float, commits_elapsed: int) -> bool:
    """Return True iff the seance is within staleness bounds for BOUNDED status.

    Per spec §1.3:
    - staleness_seconds ≤ 3600
    - commits_elapsed ≤ 10 (and not -1, which is treated as failing)
    """
    if commits_elapsed == -1:
        return False
    if commits_elapsed > _MAX_COMMITS_ELAPSED:
        return False
    if staleness_seconds > _MAX_STALENESS_SECONDS:
        return False
    return True


def build_seance_token(
    seance_event: dict,
    bead_id: str,
    run_id: str,
    rig: str,
    git_commit: str,
    claim_class: str,
) -> t.ProofToken:
    """Build a noethers-turnstile ProofToken representing a seance staleness certificate.

    The token:
    - Always has closes_gaps = []   (structural contract)
    - Has bounds_gaps = ["context_integrity_gap"] iff within staleness bounds
    - Has provenance_hash scoped to (bead_id, run_id, rig, git_commit, claim_class)

    Parameters
    ----------
    seance_event : dict
        The gt.seance OTEL record.
    bead_id, run_id, rig, git_commit : str
        Identity dimensions from the current trace context.
    claim_class : str
        The allowed_use string for the current claim.
    """
    staleness_seconds = float(seance_event.get("staleness_seconds", 9999))
    commits_elapsed = int(seance_event.get("commits_elapsed", -1))
    predecessor_run_id = seance_event.get("predecessor_run_id", "")
    current_ts = float(seance_event.get("current_timestamp", seance_event.get("timestamp", 0)))
    predecessor_ts = float(seance_event.get("predecessor_prime_timestamp", current_ts - staleness_seconds))

    staleness_class = classify_staleness(staleness_seconds, commits_elapsed)
    within_bounds = _is_within_bounds(staleness_seconds, commits_elapsed)

    prov_hash = compute_action_provenance_hash(bead_id, run_id, rig, git_commit, claim_class)

    return t.ProofToken(
        token_id=f"seance-{run_id}-{bead_id}",
        token_type="gt.seance_staleness_bound.v1",
        schema_version="gt/0.1",
        status="valid",
        closes_gaps=[],                             # structural contract: always empty
        bounds_gaps=["context_integrity_gap"] if within_bounds else [],
        provenance_hash=prov_hash,
        issued_at=current_ts,
        issuer="gt.seance",
        is_negative_control=False,
    )
