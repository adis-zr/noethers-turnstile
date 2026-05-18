# A concrete example: PGM inference

The `examples/pgm` directory shows a complete domain adapter for Bayesian network inference.

The domain defines 11 gaps including `approximation_gap`, `model_specification_gap`, `freshness_gap`, and `evidence_identity_gap`. It defines profiles for four claim classes: exact inference result, certified approximate inference, uncertified approximate inference, and inference comparison.

Running the memory-budget demo against the diabetes BIF network (`python demo/run_demo.py`) produces:

```
Budget    Budget     Geometry    KL bound    Mem         Permission
tight      9 MB       —           —           —           OOC
medium    20 MB       infinite    ∞           20.0 MB     DIA
loose    120 MB       exact       0.0000     115.1 MB     AEX
```

Three rows, three meaningfully different outcomes:

- **OOC** — no certified plan fits within 9 MB. The inference problem is out of class for this memory tier. The minimum feasible plan requires ~11.2 MB.
- **DIA** — a plan fits in 20 MB using the Hilbert kernel, but the composition soundness check fails (4307 overlapping scope pairs across 161 sites). A finite KL bound requires a residual certificate that is not available here. Result: infinite certificate, no useful bound, permission stays at the in-class floor.
- **AEX** — exact inference everywhere at 120 MB. KL = 0. The computation is provably correct given the model. Permission is AEX, not ALR.

The last point is the key lesson. AEX proves the computation was correct given the model. ALR requires a separate `ModelSpecificationToken` issued by a domain expert attesting that the model is adequate for the real-world target. No inference kernel can self-issue that token. The system will not grant ALR without it.

```
AEX: "the computation was correct given the model."
ALR: "the model is adequate AND the computation was correct."
```

These are different questions. The compiler enforces the distinction.

---

## The certifier boundary

Every token in the system is issued by a **certifier** — a domain-specific authority that runs its own checks before signing a token. The compiler consumes tokens; it does not produce them. This separation is load-bearing.

If the compiler also issued tokens, the trust chain would collapse to the process trusting itself.

The PGM example ships a `PGMExactCertifier` in `bridge/certifier.py`. It accepts a graph, query, evidence, and algorithm; runs inference internally; verifies the certificate geometry is `"exact"`; and computes all fingerprints itself from the inputs. The caller cannot supply pre-computed hashes. If inference fails or returns an approximate certificate, the certifier refuses to issue.

The `PGMModelSpecificationCertifier` is a stub that raises `NotImplementedError` with an explanation. This is intentional. The inference system computes P(query | evidence, model). It has no access to the real-world system the model is supposed to represent. Issuing a `ModelSpecificationToken` would be the system attesting to its own adequacy — the exact circularity the certifier boundary is designed to prevent. Any production deployment that wants ALR must implement this certifier externally, with validation artifacts, scope limits, and an expiry policy.

---

## Getting started

Install the library:

```bash
pip install noethers-turnstile
```

Or build from source with maturin:

```bash
maturin develop
```

A minimal compilation:

```python
import noethers_turnstile as t

ctx = t.ProofContext(
    claim_id="my-claim",
    candidate_id="z-001",
    context_id="ctx-001",
    context_fingerprint="fp-001",
    allowed_use="diagnostics",
    membership=t.Membership.InClass,
    authority_ceiling=t.Permission.AAA,
    expiry=t.Expiry.never(),
    gaps=[t.GapRecord("g1", "calibration_gap")],
    profiles=[t.Profile(
        t.Permission.DIA,
        [t.GapRequirement("g1", "closed")],
    )],
    tokens=[],  # no evidence yet
)

live = t.compile(ctx)
rt = t.RuntimeContext(now_unix=..., context_fingerprint="fp-001")
print(live.permission_str(rt))  # → "UNS" (profile exists, gap unsatisfied)
```

Add a token with correct provenance and the gap closes:

```python
prov = t.compute_provenance_hash("my-claim", "z-001", "ctx-001", "diagnostics")

token = t.ProofToken(
    token_id="tok-001",
    token_type="CALIBRATION",
    schema_version="0.1",
    status="valid",
    closes_gaps=["g1"],
    bounds_gaps=[],
    provenance_hash=prov,
    issued_at=...,
    issuer="my-certifier",
)

ctx.tokens = [token]
live = t.compile(ctx)
print(live.permission_str(rt))  # → "DIA"
```

For a complete domain adapter, see `examples/pgm/bridge/`. For the full memory-budget demo, see `examples/pgm/demo/run_demo.py`.