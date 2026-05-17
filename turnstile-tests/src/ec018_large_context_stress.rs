/// EC-018 — Large-context stress tests.
///
/// Verifies that the compiler and composition operator remain correct and
/// terminate in reasonable time for large inputs.  This is not a benchmark;
/// it is a correctness guard for production-scale contexts.
///
/// Scenarios:
///   L1 — 100 gaps, 100 tokens (each closes one gap), single DIA profile.
///   L2 — 50 gaps with a mix of Open/Bounded/Closed; profiled at DIA requiring
///         all 50 closed.  Only 49 are closed → OOC (one gap open).
///   L3 — compose_n of 20 contexts each with 10 gaps → non-promotion holds.
///   L4 — 200 tokens in a context (only 1 has correct provenance) → compiler
///         accepts the one valid token and emits DIA.
///   L5 — Context with 500 gaps, all open, requiring all closed → OOC.
///   L6 — compose_n of 50 single-gap contexts → composed authority ceiling
///         is the meet of all input ceilings.
use chrono::Utc;
use turnstile_core::{
    compile, compose_n,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn make_large_ctx(
    n_gaps: usize,
    close_count: usize,
    authority_ceiling: Permission,
) -> ProofContext {
    let claim_id = "claim-large";
    let candidate_id = "z-large";
    let context_id = "ctx-large";
    let allowed_use = "large-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let gaps: Vec<GapRecord> = (0..n_gaps)
        .map(|i| GapRecord::open(format!("g{i}"), "calibration_gap"))
        .collect();

    let requirements: Vec<GapRequirement> = (0..n_gaps)
        .map(|i| GapRequirement {
            gap_id: format!("g{i}"),
            minimum_status: RequiredStatus::ClosedRequired,
        })
        .collect();

    let tokens: Vec<ProofToken> = (0..close_count)
        .map(|i| ProofToken {
            token_id: format!("tok-{i}"),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![format!("g{i}")],
            bounds_gaps: vec![],
            provenance_hash: hash.clone(),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        })
        .collect();

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-large".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: requirements,
        }],
        tokens,
        expiry: Expiry::never(),
        authority_ceiling,
        membership: Membership::InClass,
    }
}

// ── L1: 100 gaps all closed → DIA ────────────────────────────────────────────

#[test]
fn l1_hundred_gaps_all_closed_emits_dia() {
    let ctx = make_large_ctx(100, 100, Permission::AAA);
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L1: 100 gaps all closed must emit DIA"
    );
}

// ── L2: 50 gaps, 49 closed → OOC (one open) ──────────────────────────────────

#[test]
fn l2_one_gap_open_out_of_50_yields_ooc() {
    let ctx = make_large_ctx(50, 49, Permission::AAA); // only 49/50 closed
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "L2: 49/50 gaps closed must yield REF (in-class candidate, profile defined but unmet)"
    );
}

// ── L3: compose_n of 20 contexts → non-promotion ─────────────────────────────

#[test]
fn l3_compose_n_twenty_contexts_non_promotion() {
    let ctxs: Vec<ProofContext> = (0..20)
        .map(|i| {
            let claim_id = format!("claim-large-n{i}");
            let candidate_id = format!("z-large-n{i}");
            let context_id = format!("ctx-large-n{i}");
            let allowed_use = "large-n-use";
            let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

            ProofContext {
                claim_id,
                candidate_id,
                context_id,
                context_fingerprint: format!("fp-n{i}"),
                allowed_use: allowed_use.into(),
                disallowed_uses: vec![],
                scope: Scope::default(),
                gaps: vec![GapRecord::open(format!("g-n{i}"), "gap")],
                profiles: vec![Profile {
                    permission: Permission::DIA,
                    required_gaps: vec![GapRequirement {
                        gap_id: format!("g-n{i}"),
                        minimum_status: RequiredStatus::ClosedRequired,
                    }],
                }],
                tokens: vec![ProofToken {
                    token_id: format!("tok-n{i}"),
                    token_type: "CLOSE".into(),
                    schema_version: "0.1".into(),
                    status: TokenStatus::Valid,
                    closes_gaps: vec![format!("g-n{i}")],
                    bounds_gaps: vec![],
                    provenance_hash: hash,
                    issued_at: Utc::now(),
                    expires_at: None,
                    issuer: "test".into(),
                    details: serde_json::Value::Null,
                    is_negative_control: false,
                }],
                expiry: Expiry::never(),
                authority_ceiling: Permission::AAA,
                membership: Membership::InClass,
            }
        })
        .collect();

    let individual_permissions: Vec<Permission> = ctxs
        .iter()
        .map(|c| compile(c.clone()).unwrap().permission)
        .collect();

    let composed = compose_n(ctxs).unwrap();
    let pc = compile(composed).unwrap().permission;

    for (i, &pi) in individual_permissions.iter().enumerate() {
        assert!(
            pc <= pi,
            "L3: composed permission {pc} must be ≤ individual permission {pi} (context {i})"
        );
    }
}

// ── L4: 200 tokens, only 1 correct provenance → DIA ─────────────────────────

#[test]
fn l4_200_tokens_only_one_valid_provenance_emits_dia() {
    let claim_id = "claim-l4";
    let candidate_id = "z-l4";
    let context_id = "ctx-l4";
    let allowed_use = "l4-use";
    let correct_hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let mut tokens: Vec<ProofToken> = (0..199)
        .map(|i| ProofToken {
            token_id: format!("tok-bad-{i}"),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: format!("wrong-hash-{i:064x}"), // wrong
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        })
        .collect();

    // The one good token.
    tokens.push(ProofToken {
        token_id: "tok-good".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: correct_hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-l4".into(),
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
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L4: 200 tokens but only 1 with correct provenance must still emit DIA"
    );
}

// ── L5: 500 gaps, all open → OOC ─────────────────────────────────────────────

#[test]
fn l5_500_open_gaps_all_required_yields_ooc() {
    let ctx = make_large_ctx(500, 0, Permission::AAA); // 0 tokens → all open
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "L5: 500 open gaps required closed must yield REF (in-class candidate, profile defined but unmet)"
    );
}

// ── L6: compose_n of 50 contexts → ceiling is meet of all ────────────────────

#[test]
fn l6_compose_n_50_contexts_ceiling_is_meet_of_all() {
    // Each context has a different authority ceiling.  Composed ceiling must be
    // the meet (minimum) of all.
    let ceilings = [
        Permission::AAA,
        Permission::ALR,
        Permission::AEX,
        Permission::REV,
        Permission::DIA,
    ];

    let ctxs: Vec<ProofContext> = (0..50)
        .map(|i| {
            let ceiling = ceilings[i % ceilings.len()];
            let claim_id = format!("claim-l6-{i}");
            let candidate_id = format!("z-l6-{i}");
            let context_id = format!("ctx-l6-{i}");
            let allowed_use = "l6-use";
            let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);
            ProofContext {
                claim_id,
                candidate_id,
                context_id,
                context_fingerprint: format!("fp-l6-{i}"),
                allowed_use: allowed_use.into(),
                disallowed_uses: vec![],
                scope: Scope::default(),
                gaps: vec![],
                profiles: vec![],
                tokens: vec![ProofToken {
                    token_id: format!("tok-l6-{i}"),
                    token_type: "DUMMY".into(),
                    schema_version: "0.1".into(),
                    status: TokenStatus::Valid,
                    closes_gaps: vec![],
                    bounds_gaps: vec![],
                    provenance_hash: hash,
                    issued_at: Utc::now(),
                    expires_at: None,
                    issuer: "test".into(),
                    details: serde_json::Value::Null,
                    is_negative_control: false,
                }],
                expiry: Expiry::never(),
                authority_ceiling: ceiling,
                membership: Membership::InClass,
            }
        })
        .collect();

    let expected_ceiling = ceilings
        .iter()
        .copied()
        .fold(Permission::AAA, |a, b| a.meet(b));

    let composed = compose_n(ctxs).unwrap();
    assert_eq!(
        composed.authority_ceiling, expected_ceiling,
        "L6: authority_ceiling of composed context must be meet of all input ceilings"
    );
}
