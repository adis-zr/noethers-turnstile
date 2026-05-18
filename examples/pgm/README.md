# PGM Inference — turnstile integration example

This example shows how to integrate turnstile with a real domain: probabilistic graphical model (PGM) inference on Bayesian networks. It demonstrates the full mapping from domain evidence (inference certificates, freshness tokens, identity proofs) onto turnstile's gap/profile/token API.

The example is entirely self-contained. It copies the minimal types it needs from the ecds-pgm reference adapter rather than importing from it.

---

## What's here

```
bridge/         domain adapter — token types, fingerprinting, gap profiles, bridge API
data/bif/       BIF benchmark graphs (not committed; see below)
tests/
  test_1_bridge.py   agreement tests — verifies the translation layer is correct
  test_2_demo.py     narrative tests — shows what the compiler does step by step
  test_3_stress.py   stress tests    — adversarial inputs targeting the Rust path
  test_4_bif.py      BIF integration — real graph topologies (skips if no files)
  test_5_gaps.py     gap-correctness — model_specification_gap gate, approximate inference
                     BIF benchmark, context expiry TTL, and serde round-trip
```

---

## Install

Turnstile must be built first. From the repo root:

```bash
python3 -m maturin develop
```

Then install this example:

```bash
cd examples/pgm
python3 -m pip install -e ".[dev]"
```

---

## Run the tests

From `examples/pgm/`:

```bash
pytest tests/ -v                      # all tests (test_4 skips if no BIF files)
pytest tests/test_1_bridge.py -v     # bridge agreement tests
pytest tests/test_2_demo.py -v -s    # narrative demo — prints derivation steps
pytest tests/test_3_stress.py -v     # compiler stress tests
pytest tests/test_4_bif.py -v        # BIF integration (requires data/bif/)
pytest tests/test_5_gaps.py -v       # gap correctness, expiry, serde round-trip
```

`conftest.py` at the example root automatically puts the workspace `python/` directory first on
`sys.path`, so tests always run against the locally-built `turnstile` rather than any previously
installed wheel.  No `PYTHONPATH` export is needed.

---

## Gap taxonomy

The bridge defines 11 standard gaps. Each represents a distinct piece of evidence a certifier must supply before the corresponding permission tier is reachable.

| Gap | What it captures |
|-----|-----------------|
| `model_identity_gap` | The graph structure is pinned to this exact model fingerprint |
| `query_identity_gap` | The query target and type are pinned |
| `evidence_identity_gap` | The observation dict is pinned |
| `algorithm_reproducibility_gap` | The inference algorithm is registered and reproducible |
| `approximation_gap` | The result is exact (or a certified bound has been supplied) |
| `model_specification_gap` | The supplied model is adequate for the real-world target — **not** just that the computation was correct given the model |
| `certifier_soundness_gap` | The certifier algorithm is sound for the claimed guarantee type |
| `bound_scope_gap` | The certified bound applies to exactly this problem instance |
| `runtime_registry_gap` | All runtime dependencies are registered and version-controlled |
| `freshness_gap` | The evidence and model versions are current |
| `provenance_gap` | The full provenance chain is auditable |

### Why `model_specification_gap` gates ALR

`approximation_gap` proves that the inference is close to the posterior of the *supplied* model. It does not prove that the supplied model is an adequate representation of the real-world system. `model_specification_gap` is the only gap that addresses adequacy. Without bounding it, a rollout certificate (ALR) only certifies "correct computation on a model of unknown relevance" — which is the production failure mode identified in the paper.

The design consequence: `ExactInferenceToken + FreshnessToken` earns AEX (the computation is exact and fresh) but not ALR (no adequacy claim). ALR requires a `ModelSpecificationToken` issued by a domain expert or external validation process that is independent of the inference system itself.

---

## Signal semantics (stress test reference)

The `test_3_stress.py` tests exercise the Rust compiler directly. Three signal distinctions are
tested precisely:

| Scenario | Signal | Why |
|----------|--------|-----|
| Wrong-provenance token (valid status, hash mismatch) | `REF` | `PROVENANCE_MISMATCH` structural blocker at step 4 — credential seen and rejected |
| Dead credential (correct provenance, `Invalid`/`Revoked`/`Malformed` status) | `REF` | `DEAD_CREDENTIAL` structural blocker at step 4 — credential explicitly refused |
| Time-expired token (`Valid` status, past `expires_at`) | `EXP` | Step 6 EXP floor fires for any valid-provenance valid-status time-expired token, regardless of whether a profile was satisfied |
| Out-of-class membership | `OOC` | Membership check at step 1, before token evaluation |

`REF` is not `OOC`: `REF` means "a credential was presented and structurally rejected"; `OOC`
means "the candidate is not in the class".  They are distinct outcomes in the permission order
(`OOC < EXP < REF`).

---

## BIF benchmark files

`test_4_bif.py` uses real Bayesian network files from the bnlearn repository. These are not committed to this repo.

**Tested on:**

| Tier | Networks |
|------|----------|
| Tier 1 (fast) | asia, cancer, earthquake, sachs, survey |
| Tier 2 (medium) | alarm, child, insurance, hailfinder, hepar2, win95pts |
| Tier 3 (large) | andes, link, munin1, pigs, water |

**To run the BIF tests**, download the `.bif` files from:

> https://www.bnlearn.com/bnrepository/

Place them in `examples/pgm/data/bif/`. The directory is gitignored; re-run `pytest tests/test_4_bif.py -v` once files are present.

---

## How to adapt this to your domain

Integrating turnstile with a new domain requires three things:

**1. Define your gap taxonomy** — what pieces of evidence exist, and what each one proves.

```python
MY_GAPS = ["calibration_gap", "scope_gap", "freshness_gap"]
```

**2. Define your profiles** — which gaps must be closed/bounded for each permission tier.

```python
MY_PROFILES = {
    "DIA": {},
    "REV": {"calibration_gap": "bounded"},
    "ALR": {"calibration_gap": "closed", "freshness_gap": "closed"},
}
```

**3. Build tokens** with `compute_provenance_hash()` and hand them to `compile()`.

```python
import turnstile as t

claim_id   = fingerprint(my_model)
candidate_id = fingerprint(my_query)
context_id = fingerprint(my_context)
allowed_use = "my-domain-action"

prov_hash = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)

tok = t.ProofToken(
    token_id="cal-001",
    token_type="CALIBRATION",
    schema_version="1.0",
    status="valid",
    closes_gaps=["calibration_gap"],
    bounds_gaps=[],
    provenance_hash=prov_hash,
    issued_at=time.time(),
    issuer="my-certifier",
)

ctx = t.ProofContext(
    claim_id=claim_id,
    candidate_id=candidate_id,
    context_id=context_id,
    allowed_use=allowed_use,
    membership=t.Membership.InClass,
    authority_ceiling=t.Permission.ALR,
    expiry=t.Expiry.never(),
    gaps=[t.GapRecord(g, g) for g in MY_GAPS],
    profiles=build_profiles(MY_PROFILES),
    tokens=[tok],
)

live = t.compile(ctx)
rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_id)
print(live.permission_str(rt))  # "ALR" if calibration_gap closed + freshness present
```

The key insight: **your domain supplies the certifiers; turnstile handles the algebra.**
