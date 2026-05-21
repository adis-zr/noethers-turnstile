"""GasTown token registry — liveness and revocation queries.

In-memory implementation for the benchmark harness.
Unavailability fails closed (treats token as invalid/revoked).
"""

from __future__ import annotations


class TokenRegistry:
    """In-memory token registry tracking revoked tokens and run IDs."""

    def __init__(self) -> None:
        self._revoked_tokens: set[str] = set()
        self._revoked_run_ids: set[str] = set()

    def revoke_token(self, token_id: str) -> None:
        """Mark a specific token as revoked."""
        self._revoked_tokens.add(token_id)

    def revoke_run_id(self, run_id: str) -> None:
        """Revoke all tokens associated with the given run_id."""
        self._revoked_run_ids.add(run_id)

    def is_revoked(self, token_id: str) -> bool:
        """Return True iff the token is revoked.

        Fails closed: if the registry is unavailable, treat token as revoked.
        """
        return token_id in self._revoked_tokens

    def is_run_id_revoked(self, run_id: str) -> bool:
        """Return True iff the run_id has been revoked."""
        return run_id in self._revoked_run_ids

    def token_status(self, token_id: str, run_id: str | None = None) -> str:
        """Return 'valid' or 'revoked' for a token.

        If the token's run_id is revoked, all tokens from that run are revoked.
        """
        if run_id and self.is_run_id_revoked(run_id):
            return "revoked"
        if self.is_revoked(token_id):
            return "revoked"
        return "valid"


# Module-level default registry (shared across calls unless overridden)
_DEFAULT_REGISTRY = TokenRegistry()


def get_default_registry() -> TokenRegistry:
    """Return the module-level default token registry."""
    return _DEFAULT_REGISTRY
