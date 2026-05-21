"""GasTown provenance — five-id provenance hash enforcement.

Maps GasTown domain ids onto noethers-turnstile's (claim_id, candidate_id,
context_id, allowed_use) tuple.

Mapping (spec §2.2):
  claim_id    = run_id   (the action / run identity)
  candidate_id = bead_id  (the candidate being judged)
  context_id  = "{run_id}:{rig}:{git_commit}"  (environment snapshot)
  allowed_use = claim_class / allowed_use string
"""

from __future__ import annotations

import noethers_turnstile as t

# Separator used when building context_id from run_id, rig, git_commit.
# Using "|" to reduce collision risk with ":" appearing in values.
_SEP = "|"


def _build_context_id(run_id: str, rig: str, git_commit: str) -> str:
    """Build the context_id string from the three environment dimensions."""
    return f"{run_id}{_SEP}{rig}{_SEP}{git_commit}"


# Expose as public name for tests
build_context_id = _build_context_id


def compute_action_provenance_hash(
    bead_id: str,
    run_id: str,
    rig: str,
    git_commit: str,
    allowed_use: str,
) -> str:
    """Compute the provenance hash for a GasTown action.

    Wraps t.compute_provenance_hash with the correct five-id → four-param
    mapping:
      claim_id    = run_id
      candidate_id = bead_id
      context_id  = "{run_id}|{rig}|{git_commit}"
      allowed_use = allowed_use

    Returns a 64-character hex SHA-256 string.
    """
    context_id = _build_context_id(run_id, rig, git_commit)
    return t.compute_provenance_hash(run_id, bead_id, context_id, allowed_use)


def verify_provenance(
    token_bead_id: str,
    token_run_id: str,
    token_rig: str,
    token_git_commit: str,
    token_allowed_use: str,
    claimed_bead_id: str,
    claimed_run_id: str,
    claimed_rig: str,
    claimed_git_commit: str,
    claimed_allowed_use: str,
    stored_hash: str,
) -> bool:
    """Verify that a stored provenance hash matches the claimed five-id tuple.

    Returns True iff all five dimensions match and the hash is valid.
    """
    expected_hash = compute_action_provenance_hash(
        claimed_bead_id, claimed_run_id, claimed_rig,
        claimed_git_commit, claimed_allowed_use,
    )
    if stored_hash != expected_hash:
        return False
    # Also check that token dimensions match claimed dimensions
    if token_bead_id != claimed_bead_id:
        return False
    if token_run_id != claimed_run_id:
        return False
    if token_rig != claimed_rig:
        return False
    if token_git_commit != claimed_git_commit:
        return False
    if token_allowed_use != claimed_allowed_use:
        return False
    return True
