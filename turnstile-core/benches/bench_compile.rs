/// Criterion benchmark for the compile() hot path.
///
/// Measures judgment compilation latency across four representative workloads:
///   1. Empty context (out-of-class, returns OOC immediately)
///   2. Single-gap context, gap closed, profile satisfied
///   3. Six-gap context, all closed, highest profile wins
///   4. Adversarial: token with wrong provenance (gap stays open)
use chrono::Utc;
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn make_token(closes: Vec<String>, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: "bench-tok".into(),
        token_type: "BENCH".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: closes,
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "bench".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn base_ctx(n_gaps: usize, closed: bool, bad_provenance: bool) -> ProofContext {
    let claim_id = "bench-claim".to_string();
    let candidate_id = "bench-z".to_string();
    let context_id = "bench-ctx".to_string();
    let allowed_use = "bench-use".to_string();

    let gaps: Vec<GapRecord> = (0..n_gaps)
        .map(|i| {
            if closed {
                GapRecord::closed(format!("g{}", i), "bench_gap")
            } else {
                GapRecord::open(format!("g{}", i), "bench_gap")
            }
        })
        .collect();

    let profiles = if n_gaps > 0 {
        vec![Profile {
            permission: Permission::DIA,
            required_gaps: (0..n_gaps)
                .map(|i| GapRequirement {
                    gap_id: format!("g{}", i),
                    minimum_status: RequiredStatus::ClosedRequired,
                })
                .collect(),
        }]
    } else {
        vec![]
    };

    let ctx = ProofContext {
        claim_id: claim_id.clone(),
        candidate_id: candidate_id.clone(),
        context_id: context_id.clone(),
        context_fingerprint: "bench-fp".into(),
        allowed_use: allowed_use.clone(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles,
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    if n_gaps == 0 || !closed {
        return ctx;
    }

    let closes: Vec<String> = (0..n_gaps).map(|i| format!("g{}", i)).collect();
    let mut tok = make_token(closes, &ctx);
    if bad_provenance {
        tok.provenance_hash = "00".repeat(32); // wrong
    }

    ProofContext {
        tokens: vec![tok],
        ..ctx
    }
}

fn bench_compile(c: &mut Criterion) {
    let mut group = c.benchmark_group("compile");

    // 1. Out-of-class (returns OOC immediately).
    let ooc_ctx = ProofContext {
        membership: Membership::OutOfClassExact,
        ..base_ctx(0, false, false)
    };
    group.bench_function("out_of_class", |b| {
        b.iter(|| compile(black_box(ooc_ctx.clone())).unwrap())
    });

    // 2. Single gap, closed, profile satisfied.
    let one_gap_ctx = base_ctx(1, true, false);
    group.bench_function("single_gap_closed", |b| {
        b.iter(|| compile(black_box(one_gap_ctx.clone())).unwrap())
    });

    // 3. Six gaps, all closed, DIA emitted.
    let six_gap_ctx = base_ctx(6, true, false);
    group.bench_function("six_gaps_closed", |b| {
        b.iter(|| compile(black_box(six_gap_ctx.clone())).unwrap())
    });

    // 4. Six gaps, token with wrong provenance (adversarial).
    let bad_prov_ctx = base_ctx(6, true, true);
    group.bench_function("six_gaps_bad_provenance", |b| {
        b.iter(|| compile(black_box(bad_prov_ctx.clone())).unwrap())
    });

    group.finish();
}

criterion_group!(benches, bench_compile);
criterion_main!(benches);
