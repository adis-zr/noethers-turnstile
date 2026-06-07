"""Build a ProofContext from ILS approach state and compile it.

Parameters
----------
rvr_ft       : current RVR at touchdown zone sensor (ft)
f1_clear     : ILS signal integrity is confirmed (no monitor alarm)
f3_present   : sub-CAT-I authorization token is present
dh_ft        : decision height for this approach (ft AGL); used to evaluate f2

The f2 bit (visual reference) is computed internally from rvr_ft and the
physical floor curve in geometry.py. It is not a caller-supplied flag.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t

from geometry import rvr_floor
from profiles import (
    GAP_SIGNAL, GAP_VISUAL, GAP_AUTH,
    GAP_TYPE_SIGNAL, GAP_TYPE_VISUAL, GAP_TYPE_AUTH,
    build_profiles, ILS_CHAIN,
)

_CLAIM_ID    = "ils.approach.v1"
_CONTEXT_ID  = "ils-audit-context"
_ALLOWED_USE = "approach_authorization"


def _make_token(gap_id: str, gap_type: str) -> t.ProofToken:
    h = t.compute_provenance_hash(_CLAIM_ID, gap_id, _CONTEXT_ID, _ALLOWED_USE)
    return t.ProofToken(
        token_id=f"tok-{gap_id}",
        token_type=gap_type,
        schema_version="0.1",
        status="valid",
        closes_gaps=[gap_id],
        bounds_gaps=[],
        provenance_hash=h,
        issued_at=time.time(),
        issuer="ils-certifier",
    )


def _gap_record(gap_id: str, gap_type: str, closed: bool) -> t.GapRecord:
    status = "closed" if closed else "open"
    return t.GapRecord(gap_id, gap_type, status=status)


def compile_approach(
    rvr_ft: float,
    dh_ft: float,
    f1_clear: bool,
    f3_present: bool,
) -> t.Judgment:
    """Compile an ILS approach state to a permission judgment.

    f2 (visual_reference) is computed from rvr_ft vs the geometric floor
    at dh_ft. The caller supplies rvr_ft and dh_ft; the bit is derived here.
    """
    geo = rvr_floor(dh_ft)
    f2_clear = geo.saturated or (rvr_ft >= geo.rvr_floor_ft)

    gaps = [
        _gap_record(GAP_SIGNAL, GAP_TYPE_SIGNAL, closed=f1_clear),
        _gap_record(GAP_VISUAL, GAP_TYPE_VISUAL, closed=f2_clear),
        _gap_record(GAP_AUTH,   GAP_TYPE_AUTH,   closed=f3_present),
    ]

    tokens = []
    if f1_clear:
        tokens.append(_make_token(GAP_SIGNAL, GAP_TYPE_SIGNAL))
    if f2_clear:
        tokens.append(_make_token(GAP_VISUAL, GAP_TYPE_VISUAL))
    if f3_present:
        tokens.append(_make_token(GAP_AUTH, GAP_TYPE_AUTH))

    ctx = t.ProofContext(
        claim_id=_CLAIM_ID,
        candidate_id=GAP_SIGNAL,
        context_id=_CONTEXT_ID,
        allowed_use=_ALLOWED_USE,
        membership=t.Membership.InClass,
        # Authority ceiling is the chain's Top — unconstrained by delegation.
        authority_ceiling=ILS_CHAIN.role(t.ChainRole.Top),
        expiry=t.Expiry.never(),
        gaps=gaps,
        profiles=build_profiles(),
        tokens=tokens,
    )

    # Compile against the native ILS chain. The judgment's chain_hash records
    # the chain that authorized the decision.
    return t.compile_static(ctx, chain=ILS_CHAIN)
