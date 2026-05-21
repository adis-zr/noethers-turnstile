"""GasTown harness collector — aggregates verdict results.

Accumulates per-judgment verdicts and produces aggregate statistics for
hypothesis confirmation, failure code distribution, gap status distribution,
TCB implications, and sharpness analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from collections import defaultdict

from .evaluator import get_tcb_implications, EXPECTED_OUTPUT_SCHEMA


@dataclass
class AggregateCollector:
    """Collects judgment verdicts and aggregates statistics."""

    corpus_version: str = "0.0.0"
    adapter_version: str = "0.1.0"

    # Verdict counts
    _verdict_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Failure code counts
    _failure_codes: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Gap status distribution: {gap_id: {status: count}}
    _gap_status: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )

    # H3 depth data: {depth: [permission_str]}
    _h3_depth_data: dict[int, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    # Hypothesis results
    _h1_cases: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    _h2_eta_count: int = 0
    _hypothesis_verdicts: list[dict] = field(default_factory=list)

    # H5 Track A results
    _h5_track_a_count: int = 0

    # Sharpness analysis: {primary_gap: count}
    _primary_gap_dist: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Gap status cross-tab: {pattern: {gap_id: {status: count}}}
    _gap_cross_tab: dict[str, dict[str, dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )

    # Track-separated verdict counts
    _track_verdicts: dict[str, dict[str, int]] = field(
        default_factory=lambda: {"A": defaultdict(int), "B": defaultdict(int)}
    )

    def record_verdict(
        self,
        verdict: str,
        track: str = "B",
        chain_depth: Optional[int] = None,
        case: Optional[int] = None,
        hypothesis: Optional[str] = None,
        emitted_perm: Optional[str] = None,
        ceiling_blocked: Optional[str] = None,
        primary_gap: Optional[str] = None,
    ) -> None:
        """Record a verdict from a judgment evaluation."""
        self._verdict_counts[verdict] += 1
        if track in self._track_verdicts:
            self._track_verdicts[track][verdict] += 1
        else:
            self._track_verdicts[track] = defaultdict(int)
            self._track_verdicts[track][verdict] += 1

        # H3 depth data — record depth even if emitted_perm is None
        if chain_depth is not None:
            self._h3_depth_data[chain_depth].append(emitted_perm if emitted_perm else verdict)

        # H1 case counts
        if case is not None and verdict == "UNSOUND_CAUGHT":
            self._h1_cases[case] += 1

        # H2 ETA count
        if verdict == "UNSOUND_CAUGHT" and emitted_perm == "ETA" and ceiling_blocked == "AAA":
            self._h2_eta_count += 1

        # H5 Track A
        if track == "A" and hypothesis == "H5":
            self._h5_track_a_count += 1

        # Sharpness
        if primary_gap:
            self._primary_gap_dist[primary_gap] += 1

        # Store for hypothesis aggregation
        self._hypothesis_verdicts.append({
            "verdict": verdict,
            "track": track,
            "chain_depth": chain_depth,
            "case": case,
            "hypothesis": hypothesis,
            "emitted_perm": emitted_perm,
        })

    def record_failure_code(self, failure_code: str) -> None:
        """Record a failure code occurrence."""
        self._failure_codes[failure_code] += 1

    def record_gap_status(self, gap_id: str, status: str) -> None:
        """Record an observed gap status."""
        self._gap_status[gap_id][status] += 1

    def record_gap_status_cross_tab(self, pattern: str, gap_id: str, status: str) -> None:
        """Record a gap status for the cross-tab (A1/A5 Level 3 evidence)."""
        self._gap_cross_tab[pattern][gap_id][status] += 1

    def aggregate(self) -> dict:
        """Produce aggregate statistics."""
        # TCB implications from failure codes
        tcb_impl: dict[str, int] = defaultdict(int)
        for fc in self._failure_codes:
            for implication in get_tcb_implications(fc):
                tcb_impl[implication] += self._failure_codes[fc]

        # Track-separated results
        track_a = dict(self._track_verdicts.get("A", {}))
        track_b = dict(self._track_verdicts.get("B", {}))

        # H1 results
        h1_results = {
            "case_1": self._h1_cases.get(1, 0),
            "case_2": self._h1_cases.get(2, 0),
            "case_3": self._h1_cases.get(3, 0),
            "total": sum(
                v for k, v in self._verdict_counts.items()
                if k == "UNSOUND_CAUGHT"
            ),
        }

        # H2 results
        h2_results = {
            "eta_count": self._h2_eta_count,
            "confirmed": self._h2_eta_count > 0,
        }

        # H3 depth data
        h3_depth_data = {
            depth: perms for depth, perms in self._h3_depth_data.items()
        }

        # Sharpness analysis
        sharpness_analysis = {
            "primary_gap_distribution": dict(self._primary_gap_dist),
            "sound_missed_count": self._verdict_counts.get("SOUND_MISSED", 0),
        }

        # H5 results
        h5_results = {
            "track_a_sound_correct": self._track_verdicts.get("A", {}).get("SOUND_CORRECT", 0),
            "track_a_count": self._h5_track_a_count,
        }

        return {
            "corpus_version": self.corpus_version,
            "adapter_version": self.adapter_version,
            "verdict_counts": dict(self._verdict_counts),
            "failure_codes": dict(self._failure_codes),
            "gap_status_distribution": {
                gid: dict(counts) for gid, counts in self._gap_status.items()
            },
            "tcb_implications": dict(tcb_impl),
            "h1_results": h1_results,
            "h2_results": h2_results,
            "h3_depth_data": h3_depth_data,
            "h5_results": h5_results,
            "sharpness_analysis": sharpness_analysis,
            "track_a": track_a,
            "track_b": track_b,
            "verdict_counts_by_track": {"A": track_a, "B": track_b},
            "gap_status_cross_tab": {
                pat: {gid: dict(s) for gid, s in gaps.items()}
                for pat, gaps in self._gap_cross_tab.items()
            },
            "hypothesis_results": {
                "H1": h1_results,
                "H2": h2_results,
                "H3": {"depth_data": h3_depth_data},
                "H5": h5_results,
            },
        }
