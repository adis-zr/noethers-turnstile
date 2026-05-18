# PGM Inference — turnstile integration example

This example shows how to integrate turnstile with a real domain: probabilistic
graphical model (PGM) inference on Bayesian networks. It is structured in two
parts that serve different purposes.

**The bridge** (`bridge/`) maps PGM evidence (inference certificates, freshness
tokens, identity proofs) onto turnstile's gap/profile/token API and is exercised by
the test suite.

**The demo** (`demo/`) loads a real Bayesian network, runs inference at three memory
budgets using the certified inference compiler, translates each certificate into
turnstile proof tokens, and compiles a permission judgment — showing how memory
pressure drives outcomes all the way from OOC to AEX.

---

## What's here

```
bridge/                 domain adapter — token types, fingerprinting, gap profiles, bridge API
  bif_parser.py         BIF file parser → graph_dict / query_dict for fingerprinting
  bridge.py             compile_pgm() — main integration point
  claims.py             GAP_BASIS (11 gaps), PROFILE_REQUIREMENTS per claim class
  fingerprints.py       SHA-256 fingerprinting for graph / query / evidence dicts
  tokens.py             ExactInferenceToken, CertifiedBoundToken, FreshnessToken, etc.

demo/                   self-contained end-to-end production demo (no hilbert-flow dep)
  inference/            trimmed copy of ecds-pgm certified_inference compiler
    compiler/
      cert_policy.py    Hilbert composition guard + stubs for C1/TP-C1
      certificate_selector.py  Phase 2 geometry selection
      frontier.py       Pareto-frontier tree-knapsack DP (Phase 1)
      registry.py       ExactKernelFamily + HilbertKernelFamily registry
    kernels/
      exact.py          Dense sum-product variable elimination
      hilbert.py        Mini-bucket 2-group factor-split approximation
    certificates.py     ExactCertificate, HilbertIntervalCertificate, InfiniteCertificate
    envelope.py         Elimination DAG builder (min-fill)
    model.py            Variable, Factor, GraphicalModel, Query
  bif_loader.py         parse_bif, make_bif_instance (integer-ID inference format)
  tokens.py             cert_to_proof_tokens() — InferenceResult → ProofToken list
  run_demo.py           main script; prints budget sweep table

data/bif/               BIF benchmark graphs (not committed; see below)

tests/
  test_1_bridge.py      agreement tests — gap coverage per token type (10 tests)
  test_2_demo.py        narrative tests — full derivation walkthrough (4 tests)
  test_3_stress.py      stress tests — adversarial inputs targeting the Rust path (17 tests)
  test_4_bif.py         BIF integration — real graph topologies (32 tests; skips if no files)
  test_5_gaps.py        gap-correctness — model_specification_gap gate, TTL, serde (20 tests)
  test_6_demo.py        demo tokens.py unit tests — all geometry types (9 tests)

results/                captured outputs from test runs and demo runs
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

```bash
# From examples/pgm/
pytest tests/ -v                      # all 97 tests
pytest tests/test_1_bridge.py -v      # bridge agreement tests
pytest tests/test_2_demo.py -v -s     # narrative demo — prints derivation steps
pytest tests/test_3_stress.py -v      # compiler stress tests
pytest tests/test_4_bif.py -v         # BIF integration (requires data/bif/)
pytest tests/test_5_gaps.py -v        # gap correctness, expiry, serde round-trip
pytest tests/test_6_demo.py -v        # demo tokens.py unit tests
```

`conftest.py` at the example root puts the workspace `python/` directory first on
`sys.path` so tests always run against the locally-built `turnstile`.

---

## Run the demo

```bash
# From examples/pgm/  (diabetes.bif must be in data/bif/)
python demo/run_demo.py
```

Expected output (takes ~4 seconds total):

```
Diabetes BIF — certified inference permission sweep
Network : 413 variables, 413 factors
Query   : bg_24 (variable 412)
Evidence: none
C1/TP-C1: n/a (stubbed) — requires experiments package

Running tight budget (9 MB)...  done (0.5s) → OOC (no plan fits)
Running medium budget (20 MB)... done (2.7s) → DIA
Running loose budget (120 MB)... done (0.8s) → AEX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Budget    Budget     Geometry    KL bound    Mem         C1    Permission
─────────────────────────────────────────────────────────────────────
tight     9 MB       —           —           —           n/a   OOC
medium    20 MB      infinite    ∞           20.0 MB     n/a   DIA
loose     120 MB     exact       0.0000      115.1 MB    n/a   AEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

See `results/demo_diabetes_2026-05-17.txt` for a captured run with full notes.

---

## How the demo works

The demo exercises the certified inference compiler at three memory budgets and
feeds each result into turnstile.

### The inference compiler (demo/inference/)

The compiler is a two-phase system copied from `ecds-pgm/certified_inference/`:

**Phase 1 — execution plan selection**

`build_envelope(model, query)` constructs an elimination DAG using min-fill order.
`Compiler.compile()` runs a Pareto-frontier tree-knapsack DP over the DAG, selecting
an execution kernel at each site to minimize memory while preserving a valid certificate.

Two kernel families are available in the demo:

| Kernel | When selected | Certificate | KL bound |
|--------|---------------|-------------|----------|
| `ExactKernelFamily` | site memory ≤ budget | `ExactCertificate` | 0.0 |
| `HilbertKernelFamily` | exact doesn't fit | `HilbertIntervalCertificate` | log(n_groups) per site |

If no kernel fits any site within budget, the compiler raises `ValueError` — the
problem is out of class for that memory tier (OOC row).

**Phase 2 — certificate geometry selection**

`CertificateSelector` checks whether the plan's composition is sound:

- **All-exact plan**: geometry = `"exact"`, KL = 0.
- **Hilbert plan, disjoint scopes**: geometry = `"hilbert"`, KL = sum of per-site bounds.
- **Hilbert plan, overlapping scopes**: `hilbert_composition_guard()` fires. The scalar
  additive KL bound would overcount when Hilbert site output scopes are not pairwise
  disjoint. The selector then tries C1 → FK-KL → TP-C1 in order. In the demo all
  three are stubbed (they require `experiments.residual_emitter` / `experiments.oracle`
  from the full ecds-pgm package). Result: geometry = `"infinite"`, KL = ∞.

On diabetes at 20 MB there are 161 Hilbert sites with 4307 overlapping scope pairs,
so the guard always fires at that budget — the medium row gets DIA.

**Why diabetes and not a smaller network**

Asia, Cancer, and Earthquake (Tier 1) all collapse to a single-point Pareto frontier:
Hilbert is Pareto-dominated on small binary networks because the 2-group split adds
auxiliary variable overhead that costs *more* memory than exact elimination at those
factor sizes. Every budget above ~200 bytes gives exact everywhere.

Diabetes (413 vars, cardinalities 3–21) is large enough that Hilbert's per-site
memory savings are real, producing genuinely different outcomes at different budgets.

### Budget calibration (hardcoded for diabetes)

| Label | Budget | Outcome |
|-------|--------|---------|
| tight | 9,000,000 B (~9 MB) | OOC — min feasible plan ≈11.2 MB |
| medium | 20,000,000 B (~20 MB) | DIA — Hilbert plan fits, guard fires → infinite |
| loose | 120,000,000 B (~120 MB) | AEX — exact everywhere, KL=0 |

### The translation layer (demo/tokens.py)

`cert_to_proof_tokens()` converts an `InferenceResult` into a list of turnstile
`ProofToken` objects by mapping certificate geometry to gap coverage:

| Geometry | ProofToken type | Gaps closed | Gaps bounded |
|----------|-----------------|-------------|--------------|
| `exact` | `ExactInferenceToken` + `FreshnessToken` | approximation, model_identity, query_identity, evidence_identity, algorithm_reproducibility, freshness | — |
| `hilbert` / `fkkl` | `CertifiedBoundToken` + `FreshnessToken` | bound_scope, freshness | approximation, certifier_soundness |
| `infinite` | `InfiniteCertToken` (status=invalid) | — | — |

### Turnstile permission compilation

For each budget row (except OOC), the demo builds a `ProofContext` with:
- `GAP_BASIS` — all 11 standard gaps
- `build_profiles(claim_class)` — permission tier requirements from `bridge/claims.py`
- The translated proof tokens

`t.compile(ctx).permission_str(rt)` returns the earned permission.

### The model_specification_gap boundary

The loose row earns AEX, not ALR. `model_specification_gap` stays OPEN across all
rows because no inference kernel can certify that the diabetes BIF model is an
adequate representation of real patients. ALR requires `model_specification_gap`
BOUNDED, which needs a `ModelSpecificationToken` issued by a domain expert — a token
the inference system cannot self-issue.

```
AEX: "the computation was correct given the model."
ALR: "the model is adequate AND the computation was correct."
```

This is the design point of the demo: the permission system enforces the scientific
boundary between computational correctness and model adequacy.

---

## How the tests work

### test_1_bridge.py — agreement tests

Verify that `compile_pgm()` returns the correct permission for each combination of
token type, token status, and claim class. These tests are the ground truth for the
translation layer: they confirm that gap closures follow directly from the rules in
`bridge/claims.py`.

Key scenarios:

| Test | Tokens | Expected permission |
|------|--------|---------------------|
| BRIDGE-001 | ExactInferenceToken | AEX |
| BRIDGE-002 | ExactInferenceToken + FreshnessToken | AEX (model_specification_gap open) |
| BRIDGE-003 | CertifiedBoundToken (certified_approximate) | AEX |
| BRIDGE-004 | ModelIdentityToken only | DIA (query_identity_gap open) |
| BRIDGE-005 | No tokens | DIA |
| BRIDGE-006 | Empty runtime dict | OOC |
| BRIDGE-007 | Revoked ExactInferenceToken | DIA |
| BRIDGE-008 | Full evidence, ceiling=REV | REV |
| BRIDGE-009 | uncertified_approximate_inference | REV (no AEX/ALR profile) |
| BRIDGE-010 | compose() non-promotion | composed ≤ meet(perm_a, perm_b) |

### test_2_demo.py — narrative tests

Run with `-s` to see derivation steps printed to stdout. Demonstrate:
- DEMO-001: Full derivation — ExactInferenceToken + FreshnessToken → AEX
- DEMO-002: Revoked token — gaps stay closed, permission stays DIA
- DEMO-003: Ceiling enforcement — full evidence earns ALR, capped at REV
- DEMO-004: Composition — non-upgrade property illustrated

### test_3_stress.py — stress tests

Exercise the Rust compiler path directly with adversarial inputs. Three key signal
distinctions tested precisely:

| Scenario | Signal | Why |
|----------|--------|-----|
| Wrong-provenance token (valid status, hash mismatch) | `REF` | PROVENANCE_MISMATCH at step 4 |
| Dead credential (correct provenance, Invalid/Revoked/Malformed status) | `REF` | DEAD_CREDENTIAL at step 4 |
| Time-expired token (Valid status, past expires_at) | `EXP` | Step 6 EXP floor |
| Out-of-class membership | `OOC` | Membership check at step 1 |

`REF` ≠ `OOC`: REF means "a credential was presented and rejected"; OOC means "the
candidate is not in the class."

### test_4_bif.py — BIF integration tests

Load real BIF networks and verify gap coverage. Skips automatically if `data/bif/`
is empty. Three test groups:

1. `test_bif_exact_token_earns_aex` — ExactInferenceToken on real networks → AEX
2. `test_bif_exact_plus_freshness_earns_aex` — same + FreshnessToken; still AEX (model_specification_gap open)
3. `test_bif_007_no_tokens_gives_dia` — all 20 networks; no tokens → DIA

Runs against all BIF files found in `data/bif/` across Tiers 1–4.

### test_5_gaps.py — gap correctness tests

Twenty tests targeting specific gap behaviors:
- GAP-001 through GAP-005: `model_specification_gap` gate — blocks ALR without a
  `ModelSpecificationToken`, enables ALR with one, rejects revoked tokens
- GAP-006/007: certified approximate inference with/without model spec token
- GAP-008/009: approximate inference permission ceilings
- GAP-010: model_specification_gap present in the gap taxonomy
- GAP-011 through GAP-014: TTL/expiry behavior
- GAP-015 through GAP-020: serde round-trip — claim_id, provenance_hash, OOC

### test_6_demo.py — demo tokens unit tests

Test `demo/tokens.py` directly using a mock `InferenceResult`:
- `claim_class_for_geometry()` for all geometry types
- Exact geometry: 5 gaps closed, 0 bounded, freshness present
- Hilbert geometry: bound_scope closed, 2 gaps bounded, freshness present
- Infinite geometry: 0 closed, 0 bounded, no freshness, status=invalid
- Provenance hash threaded to all tokens
- Unique token IDs across calls

---

## Gap taxonomy

The bridge defines 11 standard gaps:

| Gap | What it captures |
|-----|-----------------|
| `model_identity_gap` | Graph structure pinned to this exact fingerprint |
| `query_identity_gap` | Query target and type pinned |
| `evidence_identity_gap` | Observation dict pinned |
| `algorithm_reproducibility_gap` | Inference algorithm registered and reproducible |
| `approximation_gap` | Result is exact or a certified bound has been supplied |
| `model_specification_gap` | Supplied model is adequate for the real-world target |
| `certifier_soundness_gap` | Certifier algorithm is sound for the claimed guarantee type |
| `bound_scope_gap` | Certified bound applies to exactly this problem instance |
| `runtime_registry_gap` | Runtime dependencies are registered and version-controlled |
| `freshness_gap` | Evidence and model versions are current |
| `provenance_gap` | Full provenance chain is auditable |

### Why model_specification_gap gates ALR

`approximation_gap` proves the inference is close to the posterior of the *supplied*
model. It does not prove the supplied model is an adequate representation of the
real-world system. `model_specification_gap` is the only gap that addresses adequacy.

The consequence: `ExactInferenceToken + FreshnessToken` earns AEX (exact and fresh)
but not ALR (no adequacy claim). ALR requires a `ModelSpecificationToken` issued by
a domain expert or external validation process independent of the inference system.

---

## BIF benchmark files

`test_4_bif.py` and `demo/run_demo.py` use real Bayesian network files from the
bnlearn repository. These are not committed to this repo.

Download `.bif` files from:

> https://www.bnlearn.com/bnrepository/

Place them in `examples/pgm/data/bif/`. The directory is gitignored.

**Networks tested:**

| Tier | Networks |
|------|----------|
| Tier 1 (fast, <10 vars) | asia, cancer, earthquake, sachs, survey |
| Tier 2 (medium, 20–70 vars) | alarm, child, insurance, hailfinder, hepar2, win95pts |
| Tier 3 (large, 200–1000 vars) | andes, link, munin1, pigs, water |
| Tier 4 (very large) | barley, diabetes, mildew, pathfinder |

The demo requires `diabetes.bif` specifically. All other tests accept any available
subset of the above.

**Note on Tier 1 networks and the demo:** Asia, Cancer, Earthquake, Sachs, and Survey
all produce single-point Pareto frontiers — Hilbert is Pareto-dominated on small binary
networks. These networks work correctly with the bridge tests but cannot demonstrate
memory-budget variation in the demo. Diabetes (Tier 4) is required for the demo.

---

## How to adapt this to your domain

**1. Define your gap taxonomy** — what pieces of evidence exist and what each proves.

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

claim_id     = fingerprint(my_model)
candidate_id = fingerprint(my_query)
context_id   = fingerprint(my_context)
allowed_use  = "my-domain-action"

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
print(live.permission_str(rt))
```

The key insight: **your domain supplies the certifiers; turnstile handles the algebra.**
