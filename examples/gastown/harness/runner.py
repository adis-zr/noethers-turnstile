"""GasTown harness runner.

Processes traces and pairs judgments with expected labels.
"""

from __future__ import annotations

from typing import Any, Optional

from adapter.otel_adapter import process_trace as _adapter_process_trace, Judgment
from .evaluator import classify_verdict, detect_compiler_bug


# ── Default window settings for sensitivity analysis ──────────────────────────
_WINDOW_SETTINGS = [
    {"w_evidence": 900, "w_grace": 60},    # 15 min
    {"w_evidence": 1800, "w_grace": 60},   # 30 min (default)
    {"w_evidence": 3600, "w_grace": 60},   # 60 min
]


def run_trace(
    trace: list[dict],
    now_unix: float | None = None,
    bead_type: str = "normal",
    ordering_policy: str = "BUFFER",
    w_evidence: int = 1800,
    w_grace: int = 60,
    token_registry=None,
) -> list[Judgment]:
    """Run the adapter on a trace and return all judgments.

    Parameters
    ----------
    trace : list[dict]
        OTEL records.
    now_unix : float
        Current timestamp.
    bead_type : str
        "normal" or "experiment".
    ordering_policy : str
        "BUFFER", "STRICT", or "BEST_EFFORT".
    """
    return _adapter_process_trace(
        trace=trace,
        now_unix=now_unix,
        bead_type=bead_type,
        token_registry=token_registry,
        w_evidence=w_evidence,
        w_grace=w_grace,
        ordering_policy=ordering_policy,
    )


def run_and_evaluate(
    trace: list[dict],
    label: dict,
    now_unix: float | None = None,
    bead_type: str = "normal",
    ordering_policy: str = "BUFFER",
    inject_wrong_mechanism: bool = False,
    token_registry=None,
    w_evidence: int = 1800,
    w_grace: int = 60,
) -> dict:
    """Run the adapter on a trace and evaluate against the label.

    Returns a dict with keys: verdict, case (optional), anomaly (optional),
    emitted_perm, expected_perm.
    """
    import time as _time
    if now_unix is None:
        now_unix = _time.time()

    judgments = run_trace(
        trace=trace,
        now_unix=now_unix,
        bead_type=bead_type,
        ordering_policy=ordering_policy,
        token_registry=token_registry,
        w_evidence=w_evidence,
        w_grace=w_grace,
    )

    expected_perm = label.get("expected_permission", "ALR")

    # Zero judgments against non-empty expected → ADAPTER_FAILURE
    if len(judgments) == 0:
        return {
            "verdict": "ADAPTER_FAILURE",
            "emitted_perm": None,
            "expected_perm": expected_perm,
            "track": label.get("track", "B"),
        }

    # Pair first judgment against expected
    j = judgments[0]
    emitted_perm = str(j.permission)

    # Detect compiler bug
    authority_ceiling = None
    ceiling_bug = detect_compiler_bug(
        emitted_perm=emitted_perm,
        gap_states=j.gap_states,
        raised_exception=None,
        authority_ceiling=authority_ceiling,
    )

    result = classify_verdict(
        emitted_perm=emitted_perm,
        expected={
            "permission": expected_perm,
            "max_acceptable_permission": label.get("max_acceptable_permission"),
            "ceiling_blocked_permission": label.get("ceiling_blocked_permission"),
            "control_outcome_acceptable": label.get("control_outcome_acceptable", False),
            "ground_truth_label": label.get("ground_truth_label", "SOUND"),
        },
        compiler_bug_detected=(ceiling_bug is not None),
        wrong_mechanism=inject_wrong_mechanism,
        track=label.get("track", "B"),
        gap_states=j.gap_states,
    )

    result["emitted_perm"] = emitted_perm
    result["expected_perm"] = expected_perm
    return result


def run_window_sensitivity(
    trace_label_pairs: list[tuple[list[dict], dict]],
    now_unix: float | None = None,
    bead_type: str = "normal",
) -> list[dict]:
    """Run sensitivity analysis at three W_evidence settings.

    Returns a list of 3 result dicts, one per window setting.
    """
    import time as _time
    if now_unix is None:
        now_unix = _time.time()

    results = []
    for window in _WINDOW_SETTINGS:
        window_results = []
        for trace, label in trace_label_pairs:
            r = run_and_evaluate(
                trace=trace,
                label=label,
                now_unix=now_unix,
                bead_type=bead_type,
                w_evidence=window["w_evidence"],
                w_grace=window["w_grace"],
            )
            window_results.append(r)

        # Summarize
        verdict_counts: dict[str, int] = {}
        for r in window_results:
            v = r.get("verdict", "UNKNOWN")
            verdict_counts[v] = verdict_counts.get(v, 0) + 1

        # Return per-trace or aggregate
        if len(window_results) == 1:
            row = dict(window_results[0])
            row["w_evidence"] = window["w_evidence"]
            row["w_grace"] = window["w_grace"]
        else:
            row = {
                "w_evidence": window["w_evidence"],
                "w_grace": window["w_grace"],
                "verdict_counts": verdict_counts,
            }
        results.append(row)

    return results
