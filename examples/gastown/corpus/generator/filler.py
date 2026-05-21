"""GasTown corpus filler pass.

Adds narrative placeholder fields to OTEL events without modifying structural
fields. In the paper's Phase 2, an LLM fills the narrative_placeholder values.
Structural fields (event_type, run_id, bead_id, timestamp, role, rig,
git_commit, exit_type, etc.) must never be modified by the filler.

Spot-check: ≥ 5% of filled traces should be audited for structural contamination
before the corpus is used in Component 1 analysis.
"""

from __future__ import annotations

import copy

# Structural fields that must not be modified by the filler
_STRUCTURAL_FIELDS = frozenset({
    "event_type",
    "timestamp",
    "run_id",
    "bead_id",
    "role",
    "rig",
    "git_commit",
    "exit_type",
    "hook_mode",
    "subcommand",
    "status",
    "is_mayor",
    "is_fabricated",
    "chain_complete",
    "chain_partial",
    "is_mayor_authorized",
    "gate_pass",
    "detail_contract_valid",
    "resolution_status",
    "has_failure_evidence",
    "staleness_seconds",
    "commits_elapsed",
    "staleness_class",
    "predecessor_run_id",
    "bead_type",
    "agent_name",
    "issue_id",
    # provenance override fields (L1/L4 laundering)
    "provenance_run_id",
    "provenance_bead_id",
    "provenance_rig",
    "provenance_git_commit",
})

# Narrative fields that the LLM will fill
_NARRATIVE_FIELDS_BY_EVENT = {
    "agent.instantiate": ["task_description"],
    "done": ["summary"],
    "prime": ["context_note"],
    "sling": ["rationale"],
    "bd.call": ["output_note"],
    "escalate": ["escalation_reason"],
    "gt.seance": ["recovery_note"],
    "mol.squash": ["molecule_summary"],
    "mol.burn": ["abandonment_reason"],
    "mail": ["message_body"],
}


def apply_filler(trace: list[dict]) -> list[dict]:
    """Apply the narrative filler pass to a trace.

    Returns a new list of event dicts with narrative_placeholder added.
    Structural fields are never modified.
    """
    filled = []
    for event in trace:
        ev = copy.deepcopy(event)
        etype = ev.get("event_type", "")
        # Add a generic narrative placeholder for all events
        if "narrative_placeholder" not in ev:
            ev["narrative_placeholder"] = _make_placeholder(etype)
        # Add event-type-specific narrative fields (empty; LLM fills these)
        for field in _NARRATIVE_FIELDS_BY_EVENT.get(etype, []):
            if field not in ev:
                ev[field] = ""
        # Verify structural fields are untouched
        for sf in _STRUCTURAL_FIELDS:
            if sf in event and ev.get(sf) != event[sf]:
                raise ValueError(
                    f"Filler contaminated structural field '{sf}' in {etype} event"
                )
        filled.append(ev)
    return filled


def _make_placeholder(event_type: str) -> str:
    """Return a static narrative placeholder string for the given event type."""
    _PLACEHOLDERS = {
        "agent.instantiate": "[LLM: describe agent task and context]",
        "done": "[LLM: summarize what was accomplished]",
        "prime": "[LLM: describe context recovery]",
        "sling": "[LLM: describe delegation rationale]",
        "bd.call": "[LLM: describe operation outcome]",
        "escalate": "[LLM: describe escalation trigger]",
        "gt.seance": "[LLM: describe session recovery context]",
        "mol.squash": "[LLM: describe molecule completion]",
        "mol.burn": "[LLM: describe abandonment reason]",
        "mail": "[LLM: describe message content]",
        "convoy.membership": "[LLM: describe convoy context]",
        "authority_chain": "[LLM: describe authority chain]",
        "resolution_attempt": "[LLM: describe resolution attempt]",
        "experiment_scope_token": "[LLM: describe experiment scope]",
    }
    return _PLACEHOLDERS.get(event_type, "[LLM: narrative]")
