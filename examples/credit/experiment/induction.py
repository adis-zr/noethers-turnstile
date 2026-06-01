"""CRED-IND-001: Empty taxonomy induction loop.

Starting from a structural skeleton (v0: approximation_quality + freshness),
runs cases one at a time. Each time the compiler over-authorizes — emits ALR
when the expert says < ALR — it reads the case's blocking_gaps to find the
first OPEN gap not yet in the taxonomy and induces it.

Over-authorization criterion:
  compiler emits ALR  AND  expert_judgment is not ALR (or AAA)

Induction rule:
  Find the first gap in blocking_gaps not yet in the taxonomy.
  Add it to the ALR requirement table. Advance version.
"""
from __future__ import annotations

from .cases import INDUCTION_CASES, HELD_OUT_CASES
from .compiler import compile_case
from .profile import InductionState

_OVER_AUTH_CEILING = {"ALR", "AAA"}


def _perm_str(p) -> str:
    return str(p)


def _is_over_authorized(compiler_out: str, expert: str) -> bool:
    return compiler_out in _OVER_AUTH_CEILING and expert not in _OVER_AUTH_CEILING


def run_induction() -> tuple[InductionState, list[dict]]:
    state = InductionState()
    trace: list[dict] = []

    # ── Phase 0: positive control ──────────────────────────────────────────────
    positive = next(c for c in INDUCTION_CASES if c["case_id"] == "C01")
    result = compile_case(positive, state)
    out_str = _perm_str(result)
    trace.append({
        "phase": "positive_control",
        "case_id": "C01",
        "profile": state.version_str(),
        "compiler_output": out_str,
        "expert_judgment": positive["expert_judgment"],
        "over_authorized": False,
        "gap_induced": None,
        "note": positive["note"],
    })

    # ── Induction steps ────────────────────────────────────────────────────────
    for case in INDUCTION_CASES:
        if case["case_id"] == "C01":
            continue

        profile_before = state.version_str()
        result = compile_case(case, state)
        out_str = _perm_str(result)
        over_auth = _is_over_authorized(out_str, case["expert_judgment"])

        gap_induced = None
        profile_after = profile_before

        if over_auth:
            for gap in case["blocking_gaps"]:
                if gap not in state.alr_reqs:
                    state.add_gap(gap)
                    gap_induced = gap
                    profile_after = state.version_str()
                    break

        trace.append({
            "phase": "induction",
            "case_id": case["case_id"],
            "profile_before": profile_before,
            "profile_after": profile_after,
            "compiler_output": out_str,
            "expert_judgment": case["expert_judgment"],
            "over_authorized": over_auth,
            "gap_induced": gap_induced,
            "description": case["description"],
            "note": case.get("note", ""),
        })

    return state, trace


def run_convergence_check(state: InductionState) -> list[dict]:
    records = []
    for case in INDUCTION_CASES:
        result = compile_case(case, state)
        out_str = _perm_str(result)
        over_auth = _is_over_authorized(out_str, case["expert_judgment"])
        records.append({
            "case_id": case["case_id"],
            "profile": state.version_str(),
            "compiler_output": out_str,
            "expert_judgment": case["expert_judgment"],
            "over_authorized": over_auth,
            "converged": not over_auth,
            "description": case["description"],
        })
    return records


def run_generalization_check(state: InductionState) -> list[dict]:
    records = []
    for case in HELD_OUT_CASES:
        result = compile_case(case, state)
        out_str = _perm_str(result)
        over_auth = _is_over_authorized(out_str, case["expert_judgment"])
        agreement = out_str == case["expert_judgment"]
        records.append({
            "case_id": case["case_id"],
            "profile": state.version_str(),
            "compiler_output": out_str,
            "expert_judgment": case["expert_judgment"],
            "over_authorized": over_auth,
            "agreement": agreement,
            "description": case["description"],
            "note": case.get("note", ""),
        })
    return records
