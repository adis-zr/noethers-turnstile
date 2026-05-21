"""GasTown Component 1 skeleton corpus generator.

Generates a complete set of LabeledTrace objects covering all pattern families
per §3.1 of the spec. Structural fields are fully deterministic; narrative
fill is handled by filler.py.

Corpus targets (§3.1):
  CLEAN  50   (SOUND_CORRECT baseline)
  L1–L7  70   (10 each; H1 coverage)
  L8     20   (5 families × 4 depths; H3 coverage)
  A1–A5  25   (5 each; H6 coverage)
  DIA     5   (permission algebra)
  AEX     5   (permission algebra)
  ROL     5   (permission algebra)
  Total 180
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from adapter.token_registry import TokenRegistry
from .patterns import (
    PatternLabel,
    make_clean_trace,
    make_l1_trace,
    make_l2_trace,
    make_l3_trace,
    make_l4_trace,
    make_l5_trace,
    make_l6_trace,
    make_l7_trace,
    make_l8_trace,
    make_a1_trace,
    make_a2_trace,
    make_a3_trace,
    make_a4_trace,
    make_a5_trace,
    make_dia_trace,
    make_aex_trace,
    make_rol_trace,
)

# ── Corpus targets per §3.1 ───────────────────────────────────────────────────

CORPUS_TARGETS: dict[str, int] = {
    "CLEAN": 50,
    "L1": 10,
    "L2": 10,
    "L3": 10,
    "L4": 10,
    "L5": 10,
    "L6": 10,
    "L7": 10,
    "L8": 20,  # 5 families × 4 depths
    "A1": 5,
    "A2": 5,
    "A3": 5,
    "A4": 5,
    "A5": 5,
    "DIA": 5,
    "AEX": 5,
    "ROL": 5,
}


# ── LabeledTrace ──────────────────────────────────────────────────────────────

@dataclass
class LabeledTrace:
    """A synthetic OTEL trace with its ground-truth label."""
    trace: list[dict]
    label: PatternLabel
    convoy_id: str
    bead_type: str = "normal"
    token_registry: TokenRegistry | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "trace": self.trace,
            "label": self.label.to_dict(),
            "convoy_id": self.convoy_id,
            "bead_type": self.bead_type,
        }


# ── Deterministic ID generation ───────────────────────────────────────────────

def _make_run_id(base: str, family: str, idx: int) -> str:
    return f"{base}-{family.lower()}-{idx:04d}"


def _make_bead_id(family: str, idx: int) -> str:
    return f"bead-{family.lower()}-{idx:04d}"


def _make_convoy_id(family: str, idx: int) -> str:
    return f"convoy-{family.lower()}-{idx:04d}"


# ── Base constants ────────────────────────────────────────────────────────────

_BASE_RIG = "rig-corpus"
_BASE_GIT = "corpus000deadbeef"
_BASE_TS = 1_748_736_000.0  # 2025-06-01 00:00:00 UTC


# ── Family generators ─────────────────────────────────────────────────────────

def _gen_clean(base_run_id: str, base_ts: float, n: int = 50) -> list[LabeledTrace]:
    result = []
    # Alternate roles for variety: polecat (40) + mayor (10)
    roles = ["polecat"] * 40 + ["mayor"] * 10
    for i in range(n):
        role = roles[i % len(roles)]
        run_id = _make_run_id(base_run_id, "CLEAN", i)
        bead_id = _make_bead_id("CLEAN", i)
        ts = base_ts + i * 120.0
        trace, lbl = make_clean_trace(run_id=run_id, bead_id=bead_id,
                                      rig=_BASE_RIG, git_commit=_BASE_GIT,
                                      ts=ts, role=role)
        result.append(LabeledTrace(trace=trace, label=lbl,
                                   convoy_id=_make_convoy_id("CLEAN", i),
                                   bead_type="normal"))
    return result


def _gen_laundering(base_run_id: str, base_ts: float,
                    family: str, factory, n: int = 10,
                    bead_type: str = "normal") -> list[LabeledTrace]:
    result = []
    for i in range(n):
        run_id = _make_run_id(base_run_id, family, i)
        bead_id = _make_bead_id(family, i)
        ts = base_ts + i * 120.0
        trace, lbl = factory(run_id=run_id, bead_id=bead_id,
                              rig=_BASE_RIG, git_commit=_BASE_GIT, ts=ts)
        result.append(LabeledTrace(trace=trace, label=lbl,
                                   convoy_id=_make_convoy_id(family, i),
                                   bead_type=bead_type))
    return result


def _gen_l8(base_run_id: str, base_ts: float) -> list[LabeledTrace]:
    """5 families × 4 depths (2, 3, 4, 5) = 20 instances."""
    result = []
    idx = 0
    for family_idx in range(5):
        for depth in [2, 3, 4, 5]:
            run_id = _make_run_id(base_run_id, "L8", idx)
            bead_id = _make_bead_id("L8", idx)
            ts = base_ts + idx * 300.0
            trace, lbl = make_l8_trace(run_id=run_id, bead_id=bead_id,
                                       rig=_BASE_RIG, git_commit=_BASE_GIT,
                                       ts=ts, depth=depth, family_idx=family_idx)
            result.append(LabeledTrace(trace=trace, label=lbl,
                                       convoy_id=_make_convoy_id("L8", idx),
                                       bead_type="normal"))
            idx += 1
    return result


def _gen_adversarial(base_run_id: str, base_ts: float,
                     family: str, factory, n: int = 5) -> list[LabeledTrace]:
    result = []
    for i in range(n):
        run_id = _make_run_id(base_run_id, family, i)
        bead_id = _make_bead_id(family, i)
        ts = base_ts + i * 120.0
        trace, lbl = factory(run_id=run_id, bead_id=bead_id,
                              rig=_BASE_RIG, git_commit=_BASE_GIT, ts=ts)
        token_registry = None
        if family == "A3":
            token_registry = TokenRegistry()
            token_registry.revoke_run_id(run_id)
        result.append(LabeledTrace(trace=trace, label=lbl,
                                   convoy_id=_make_convoy_id(family, i),
                                   bead_type="normal",
                                   token_registry=token_registry))
    return result


def _gen_dia(base_run_id: str, base_ts: float, n: int = 5) -> list[LabeledTrace]:
    result = []
    roles = ["dog", "boot", "dog", "boot", "dog"]
    for i in range(n):
        run_id = _make_run_id(base_run_id, "DIA", i)
        bead_id = _make_bead_id("DIA", i)
        ts = base_ts + i * 120.0
        trace, lbl = make_dia_trace(run_id=run_id, bead_id=bead_id,
                                    rig=_BASE_RIG, git_commit=_BASE_GIT,
                                    ts=ts, role=roles[i % len(roles)])
        result.append(LabeledTrace(trace=trace, label=lbl,
                                   convoy_id=_make_convoy_id("DIA", i),
                                   bead_type="normal"))
    return result


def _gen_aex(base_run_id: str, base_ts: float, n: int = 5) -> list[LabeledTrace]:
    result = []
    for i in range(n):
        run_id = _make_run_id(base_run_id, "AEX", i)
        bead_id = _make_bead_id("AEX", i)
        ts = base_ts + i * 120.0
        trace, lbl = make_aex_trace(run_id=run_id, bead_id=bead_id,
                                    rig=_BASE_RIG, git_commit=_BASE_GIT, ts=ts)
        result.append(LabeledTrace(trace=trace, label=lbl,
                                   convoy_id=_make_convoy_id("AEX", i),
                                   bead_type="experiment"))
    return result


def _gen_rol(base_run_id: str, base_ts: float, n: int = 5) -> list[LabeledTrace]:
    result = []
    for i in range(n):
        run_id = _make_run_id(base_run_id, "ROL", i)
        bead_id = _make_bead_id("ROL", i)
        ts = base_ts + i * 120.0
        trace, lbl = make_rol_trace(run_id=run_id, bead_id=bead_id,
                                    rig=_BASE_RIG, git_commit=_BASE_GIT, ts=ts)
        result.append(LabeledTrace(trace=trace, label=lbl,
                                   convoy_id=_make_convoy_id("ROL", i),
                                   bead_type="normal"))
    return result


# ── Main generator ────────────────────────────────────────────────────────────

def generate_component1_corpus(
    base_ts: float = _BASE_TS,
    base_run_id: str = "corpus",
) -> list[LabeledTrace]:
    """Generate the full Component 1 synthetic corpus (180 traces).

    Returns a list of LabeledTrace objects in family order:
      CLEAN (50) → L1–L7 (10 each) → L8 (20) → A1–A5 (5 each) → DIA/AEX/ROL (5 each)
    """
    corpus: list[LabeledTrace] = []

    # Spread base timestamps so each family occupies a distinct window
    t_offset = 0.0
    step = 3600.0  # 1 hour per family block

    corpus += _gen_clean(base_run_id, base_ts + t_offset)
    t_offset += step

    for family, factory in [
        ("L1", make_l1_trace),
        ("L2", make_l2_trace),
        ("L3", make_l3_trace),
        ("L4", make_l4_trace),
        ("L5", make_l5_trace),
        ("L6", make_l6_trace),
        ("L7", make_l7_trace),
    ]:
        corpus += _gen_laundering(base_run_id, base_ts + t_offset, family, factory)
        t_offset += step

    corpus += _gen_l8(base_run_id, base_ts + t_offset)
    t_offset += step

    for family, factory in [
        ("A1", make_a1_trace),
        ("A2", make_a2_trace),
        ("A3", make_a3_trace),
        ("A4", make_a4_trace),
        ("A5", make_a5_trace),
    ]:
        corpus += _gen_adversarial(base_run_id, base_ts + t_offset, family, factory)
        t_offset += step

    corpus += _gen_dia(base_run_id, base_ts + t_offset)
    t_offset += step

    corpus += _gen_aex(base_run_id, base_ts + t_offset)
    t_offset += step

    corpus += _gen_rol(base_run_id, base_ts + t_offset)

    return corpus
