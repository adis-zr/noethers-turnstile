/// EC-016 — Compile determinism (Spec §8).
///
/// The compiler is a pure function.  Given the same ProofContext as input,
/// it must produce bit-identical output across any number of calls, on any
/// thread, in any order.
///
/// Properties:
///   D1 — Same context twice → same permission, same derivation provenance hash.
///   D2 — 1000 sequential calls on same context → identical results.
///   D3 — Concurrent calls on same context → identical results (no race).
///   D4 — Permission is not affected by wall-clock time unless a token or
///         context expiry has fired.
///   D5 — Serde round-trip of ProofContext → recompile → same permission.
///   D6 — Different contexts with identical structure → same permission
///         (structural equivalence).
use chrono::Utc;
use std::sync::{Arc, Barrier};
use std::thread;
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn stable_ctx() -> ProofContext {
    let claim_id = "claim-det";
    let candidate_id = "z-det";
    let context_id = "ctx-det";
    let allowed_use = "det-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-det".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-det".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None, // no expiry — stable forever
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── D1: Two calls → same result ───────────────────────────────────────────────

#[test]
fn d1_same_context_twice_same_permission() {
    let ctx = stable_ctx();
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();
    assert_eq!(
        j1.permission, j2.permission,
        "D1: same context → same permission"
    );
}

#[test]
fn d1_same_context_twice_same_provenance_hash() {
    let ctx = stable_ctx();
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();
    assert_eq!(
        j1.derivation.provenance_hash, j2.derivation.provenance_hash,
        "D1: same context → same derivation provenance hash"
    );
}

#[test]
fn d1_same_context_twice_same_derivation_phase_sequence() {
    let ctx = stable_ctx();
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();

    let phases1: Vec<&str> = j1
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    let phases2: Vec<&str> = j2
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    assert_eq!(
        phases1, phases2,
        "D1: same context → same derivation phase sequence"
    );
}

// ── D2: 1000 sequential calls → identical ────────────────────────────────────

#[test]
fn d2_thousand_sequential_calls_identical() {
    let ctx = stable_ctx();
    let baseline = compile(ctx.clone()).unwrap().permission;

    for i in 0..1000 {
        let p = compile(ctx.clone()).unwrap().permission;
        assert_eq!(
            p, baseline,
            "D2: iteration {i} produced {p} instead of {baseline}"
        );
    }
}

// ── D3: Concurrent calls → identical ─────────────────────────────────────────

#[test]
fn d3_concurrent_calls_all_return_same_permission() {
    let ctx = Arc::new(stable_ctx());
    let baseline = compile((*ctx).clone()).unwrap().permission;

    let n_threads = 16;
    let barrier = Arc::new(Barrier::new(n_threads));

    let handles: Vec<_> = (0..n_threads)
        .map(|_| {
            let ctx_clone = Arc::clone(&ctx);
            let barrier_clone = Arc::clone(&barrier);
            thread::spawn(move || {
                // All threads start compiling at the same time.
                barrier_clone.wait();
                compile((*ctx_clone).clone()).unwrap().permission
            })
        })
        .collect();

    for (i, h) in handles.into_iter().enumerate() {
        let p = h.join().expect("thread panicked");
        assert_eq!(
            p, baseline,
            "D3: thread {i} returned {p} instead of {baseline}"
        );
    }
}

// ── D4: No wall-clock drift when no expiry ────────────────────────────────────

#[test]
fn d4_permission_stable_across_short_time_interval() {
    // compile() reads Utc::now() internally.  Without any expiry constraints,
    // the result must not change over a short interval.
    let ctx = stable_ctx();
    let p1 = compile(ctx.clone()).unwrap().permission;
    // Brief busy-wait — no sleep needed; just re-compile.
    let p2 = compile(ctx.clone()).unwrap().permission;
    let p3 = compile(ctx).unwrap().permission;
    assert_eq!(p1, p2, "D4: no time drift between consecutive calls");
    assert_eq!(p2, p3, "D4: no time drift between consecutive calls");
}

// ── D5: Serde round-trip → same permission ───────────────────────────────────

#[test]
fn d5_serde_roundtrip_then_recompile_same() {
    let ctx = stable_ctx();
    let p_before = compile(ctx.clone()).unwrap().permission;

    let json = serde_json::to_string(&ctx).unwrap();
    let recovered: ProofContext = serde_json::from_str(&json).unwrap();
    let p_after = compile(recovered).unwrap().permission;

    assert_eq!(
        p_before, p_after,
        "D5: serde round-trip broke determinism: {} vs {}",
        p_before, p_after
    );
}

// ── D6: Structurally identical contexts → same permission ────────────────────

#[test]
fn d6_structurally_identical_contexts_same_permission() {
    // Build the same logical context twice from scratch (different Rust objects,
    // same data).
    let build = || {
        let claim_id = "claim-struct";
        let candidate_id = "z-struct";
        let context_id = "ctx-struct";
        let allowed_use = "struct-use";
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
        ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp-struct".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::open("g1", "calibration_gap")],
            profiles: vec![Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![ProofToken {
                token_id: "tok-struct".into(),
                token_type: "CLOSE".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec!["g1".into()],
                bounds_gaps: vec![],
                provenance_hash: hash,
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "certifier".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            }],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            membership: Membership::InClass,
        }
    };

    let j1 = compile(build()).unwrap();
    let j2 = compile(build()).unwrap();
    assert_eq!(
        j1.permission, j2.permission,
        "D6: structurally identical contexts must produce same permission"
    );
    assert_eq!(
        j1.derivation.provenance_hash, j2.derivation.provenance_hash,
        "D6: structurally identical contexts must produce same provenance hash"
    );
}

// ── Regression: OOC contexts deterministic too ────────────────────────────────

#[test]
fn ooc_context_is_deterministic() {
    let mut ctx = stable_ctx();
    ctx.membership = Membership::OutOfClassExact;

    let p1 = compile(ctx.clone()).unwrap().permission;
    let p2 = compile(ctx.clone()).unwrap().permission;
    let p3 = compile(ctx).unwrap().permission;
    assert_eq!(p1, Permission::OOC);
    assert_eq!(p2, Permission::OOC);
    assert_eq!(p3, Permission::OOC);
}
