"""
PGM domain certifiers — reference implementation of the token issuance side.

Trust model
-----------
Certifiers are external authorities. The compiler (noethers-turnstile) trusts their output
structurally — it checks provenance hashes and fingerprint bindings — but makes no
scientific judgment about whether the certifier's claim is adequate for the real-world
target. That separation is intentional and load-bearing.

Two roles exist in the PGM domain:

  PGMExactCertifier
      Can self-certify. It takes a graph, query, evidence, and algorithm; runs
      inference internally; checks the result; and issues an ExactInferenceToken
      with fingerprints it computed itself from the inputs. The caller cannot supply
      pre-computed fingerprints — that would make this a token factory, not a
      certifier. This certifier is implemented here because the inference system can
      fully check its own work.

  PGMModelSpecificationCertifier
      Cannot be implemented by the inference system. Issuing a ModelSpecificationToken
      requires a domain expert who can attest that the model is adequate for the
      real-world target: that the variables are the right variables, the conditional
      probability tables reflect real causal or statistical structure, and the network
      topology is appropriate for the decision being supported. This interface is
      defined here to make that responsibility explicit, not to pretend it can be
      automated. See the stub below.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

from .fingerprints import fingerprint, fingerprint_evidence, fingerprint_graph, fingerprint_query
from .tokens import ExactInferenceToken


@dataclass
class ExactInferenceSpec:
    """All inputs the certifier needs to run and verify inference."""

    graph: dict      # {"variables": [...], "factors": [...]}
    query: dict      # {"target": ..., "type": ...}
    evidence: dict   # observation dict (may be empty)
    algorithm: str   # "exact" (only value this certifier accepts)


class CertifierError(Exception):
    pass


class PGMExactCertifier:
    """
    Issues ExactInferenceToken for PGM exact inference.

    Key property: fingerprints are computed here from the inputs. The caller
    supplies graph/query/evidence/algorithm — not pre-computed hashes. If the
    inference fails or the algorithm is not "exact", this certifier refuses to issue.
    """

    def __init__(
        self,
        inference_fn: Callable[[dict, dict, dict], object],
        issuer_id: str = "pgm-exact-certifier/1.0",
        ttl_seconds: float = 86_400.0,
    ):
        """
        Parameters
        ----------
        inference_fn:
            Callable that accepts (graph, query, evidence) and returns an object
            with a `.certificate_geometry` attribute. Must return "exact" geometry
            for this certifier to issue. Raises ValueError if inference cannot run.
        issuer_id:
            Identity string embedded in the issued token.
        ttl_seconds:
            Token lifetime in seconds. Defaults to 24 hours.
        """
        self._inference_fn = inference_fn
        self._issuer_id = issuer_id
        self._ttl_seconds = ttl_seconds

    def issue(self, spec: ExactInferenceSpec) -> ExactInferenceToken:
        """
        Run inference, verify the result is exact, and issue an ExactInferenceToken.

        Raises CertifierError if:
        - algorithm is not "exact"
        - inference raises (out-of-class, budget exceeded, etc.)
        - certificate geometry is not "exact" (result is approximate)
        """
        if spec.algorithm != "exact":
            raise CertifierError(
                f"PGMExactCertifier only certifies exact inference; got {spec.algorithm!r}"
            )

        # Run inference — this is where the certifier checks its own work.
        # If it raises, we do not issue.
        try:
            result = self._inference_fn(spec.graph, spec.query, spec.evidence)
        except Exception as exc:
            raise CertifierError(f"Inference failed: {exc}") from exc

        if result.certificate_geometry != "exact":
            raise CertifierError(
                f"Expected exact certificate geometry, got {result.certificate_geometry!r}. "
                "This certifier will not issue for approximate results."
            )

        # Certifier computes all fingerprints from the inputs — never from the caller.
        fp_graph = fingerprint_graph(spec.graph)
        fp_query = fingerprint_query(spec.query)
        fp_evidence = fingerprint_evidence(spec.evidence)
        fp_algorithm = fingerprint(spec.algorithm)

        return ExactInferenceToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="ExactInferenceToken",
            status="VALID",
            issuer=self._issuer_id,
            graph_fingerprint=fp_graph,
            query_fingerprint=fp_query,
            evidence_fingerprint=fp_evidence,
            algorithm_fingerprint=fp_algorithm,
        )


class PGMModelSpecificationCertifier:
    """
    Stub for the ModelSpecificationToken certifier.

    This certifier cannot be implemented by the inference system. It requires a
    domain expert who can attest that the model is adequate for the real-world target.
    The interface is defined here to make that responsibility explicit.

    What a real implementation would need
    --------------------------------------
    - Validation artifacts: peer-reviewed study, clinical trial data, or equivalent
      external evidence that the BIF model faithfully represents the real system
    - Scope limits: the specific population, decision context, and time period the
      model was validated for — tokens issued outside that scope are not valid
    - Assumptions list: which variables are assumed exogenous, which CPTs are learned
      vs. specified by domain experts, and what distributional shift is tolerated
    - Expiry policy: model specifications go stale; validation is tied to a version
      and must be renewed when the model or its deployment context changes

    Why this is a stub
    ------------------
    The inference system computes P(query | evidence, model). It has no access to
    the real-world system the model is supposed to represent. A ModelSpecificationToken
    issued by the inference system would be the system attesting to its own adequacy —
    exactly the circularity the certifier boundary is designed to prevent.

    The token type is registered in the bridge gap taxonomy. AEX → ALR requires this
    token to be present and VALID. The system will not grant ALR without it.
    """

    def issue(self, *args, **kwargs):
        raise NotImplementedError(
            "PGMModelSpecificationCertifier cannot be implemented by the inference system. "
            "A domain expert must issue ModelSpecificationToken after validating that the "
            "model is adequate for the real-world target. See class docstring for details."
        )
