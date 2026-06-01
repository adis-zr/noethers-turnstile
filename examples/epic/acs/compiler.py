"""Thin wrapper around noethers_turnstile.compile() for the MED-001 benchmark."""
from __future__ import annotations

import noethers_turnstile as t


def compile_context(proof_context: t.ProofContext) -> t.LiveJudgment:
    return t.compile(proof_context)
