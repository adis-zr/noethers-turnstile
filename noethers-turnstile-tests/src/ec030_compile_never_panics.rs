/// EC-030 — compile() and compose() must never panic on arbitrary inputs.
///
/// For a library to be TLA+-grade reliable, the core functions must be total:
/// they must return a Result rather than panicking, regardless of input.  This
/// suite constructs adversarial inputs that exercise every edge the review
/// identified as a potential panic surface and asserts that only Ok / Err
/// is returned — never a panic.
///
///   N1 — compile() with empty gaps, empty profiles, empty tokens.
///   N2 — compile() with a gap that has no matching token.
///   N3 — compile() with all TokenStatus variants.
///   N4 — Bound::try_numeric(NaN) returns None (NaN rejected at construction).
///   N5 — compile() with Bound::Numeric(f64::INFINITY).
///   N6 — compile() with Bound::Numeric(f64::NEG_INFINITY).
///   N7 — compose() with two contexts that have disjoint gaps.
///   N8 — compose() with empty token lists on both sides.
///   N9 — compile() with a 1000-gap context.
///   N10 — compile() with a 1000-token context where one has correct provenance.
///   N11 — compose_n() with 200 contexts (fold stability).
///   N12 — compile() with a profile listing 100 gap requirements.
///   N13 — compile() with very long field strings (10k chars each).
use chrono::Utc;
use noethers_noethers_turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(suffix: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-n-{suffix}"),
        candidate_id: format!("z-n-{suffix}"),
        context_id: format!("ctx-n-{suffix}"),
        context_fingerprint: format!("fp-n-{suffix}"),
        allowed_use: "n-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── N1: Empty gaps/profiles/tokens ────────────────────────────────────────────

#[test]
fn n1_empty_context_does_not_panic() {
    let ctx = base_ctx("n1");
    let result = compile(ctx);
    assert!(
        result.is_ok() || result.is_err(),
        "N1: must return Ok or Err, never panic"
    );
}

// ── N2: Gap without matching token ────────────────────────────────────────────

#[test]
fn n2_unsatisfied_gap_does_not_panic() {
    let mut ctx = base_ctx("n2");
    ctx.gaps.push(GapRecord::open("g1", "orphan_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // No token that closes g1.
    let result = compile(ctx);
    assert!(
        result.is_ok(),
        "N2: unsatisfied gap must return Ok(OOC), not panic"
    );
}

// ── N3: All TokenStatus variants ──────────────────────────────────────────────

#[test]
fn n3_all_token_status_variants_do_not_panic() {
    for status in [
        TokenStatus::Valid,
        TokenStatus::Invalid,
        TokenStatus::Expired,
        TokenStatus::Revoked,
        TokenStatus::Malformed,
    ] {
        let mut ctx = base_ctx(&format!("n3-{status:?}"));
        ctx.gaps.push(GapRecord::open("g1", "gap"));
        ctx.profiles.push(Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let hash = compute_provenance_hash(
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        );
        ctx.tokens.push(ProofToken {
            token_id: format!("tok-{status:?}"),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        });
        let result = compile(ctx);
        assert!(
            result.is_ok() || result.is_err(),
            "N3: TokenStatus::{status:?} must not cause a panic"
        );
    }
}

// ── N4: NaN in Bound::Numeric ─────────────────────────────────────────────────

#[test]
fn n4_nan_bound_rejected_at_construction() {
    // Bound::try_numeric returns None for NaN — NaN is rejected before it can
    // reach the compiler, so compile() never sees an unsound Eq value.
    assert!(
        Bound::try_numeric(f64::NAN).is_none(),
        "N4: Bound::try_numeric(NaN) must return None"
    );
}

// ── N5: +Infinity in Bound::Numeric ──────────────────────────────────────────

#[test]
fn n5_positive_infinity_bound_does_not_panic() {
    let mut ctx = base_ctx("n5");
    ctx.gaps.push(GapRecord::bounded(
        "g1",
        "inf_gap",
        Bound::numeric(f64::INFINITY),
    ));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    });
    let result = compile(ctx);
    assert!(
        result.is_ok() || result.is_err(),
        "N5: +inf Bound::Numeric must not panic"
    );
}

// ── N6: -Infinity in Bound::Numeric ──────────────────────────────────────────

#[test]
fn n6_negative_infinity_bound_does_not_panic() {
    let mut ctx = base_ctx("n6");
    ctx.gaps.push(GapRecord::bounded(
        "g1",
        "neg_inf_gap",
        Bound::numeric(f64::NEG_INFINITY),
    ));
    let result = compile(ctx);
    assert!(
        result.is_ok() || result.is_err(),
        "N6: -inf Bound::Numeric must not panic"
    );
}

// ── N7: Compose with disjoint gaps ────────────────────────────────────────────

#[test]
fn n7_compose_with_disjoint_gaps_does_not_panic() {
    let mut g1 = base_ctx("n7a");
    let mut g2 = base_ctx("n7b");
    g1.gaps.push(GapRecord::open("gap-only-in-g1", "type1"));
    g2.gaps.push(GapRecord::open("gap-only-in-g2", "type2"));
    let result = compose(g1, g2);
    assert!(
        result.is_ok() || result.is_err(),
        "N7: compose with disjoint gaps must not panic"
    );
    if let Ok(composed) = result {
        assert_eq!(
            composed.gaps.len(),
            2,
            "N7: composed gaps must contain both disjoint gaps"
        );
    }
}

// ── N8: Compose with empty token lists ────────────────────────────────────────

#[test]
fn n8_compose_empty_tokens_does_not_panic() {
    let g1 = base_ctx("n8a");
    let g2 = base_ctx("n8b");
    let result = compose(g1, g2);
    assert!(
        result.is_ok(),
        "N8: compose with empty token lists must succeed"
    );
    assert_eq!(result.unwrap().tokens.len(), 0, "N8: no tokens in result");
}

// ── N9: 1000-gap context ─────────────────────────────────────────────────────

#[test]
fn n9_thousand_gap_context_does_not_panic() {
    let mut ctx = base_ctx("n9");
    for i in 0..1000 {
        ctx.gaps.push(GapRecord::open(format!("g{i}"), "gap"));
    }
    let result = compile(ctx);
    assert!(
        result.is_ok() || result.is_err(),
        "N9: 1000-gap context must not panic"
    );
}

// ── N10: 1000-token context with one correct token ────────────────────────────

#[test]
fn n10_thousand_token_context_does_not_panic() {
    let mut ctx = base_ctx("n10");
    ctx.gaps.push(GapRecord::open("g1", "gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });

    let correct_hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );

    for i in 0..999 {
        ctx.tokens.push(ProofToken {
            token_id: format!("wrong-tok-{i}"),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: "deadbeef".repeat(8), // wrong provenance
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        });
    }
    // One correct token at the end.
    ctx.tokens.push(ProofToken {
        token_id: "correct-tok".into(),
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

    let result = compile(ctx);
    assert!(result.is_ok(), "N10: 1000-token context must not panic");
    assert_eq!(
        result.unwrap().permission,
        Permission::DIA,
        "N10: correct token must satisfy the profile"
    );
}

// ── N11: compose_n with 200 contexts ─────────────────────────────────────────

#[test]
fn n11_compose_n_200_contexts_does_not_panic() {
    let contexts: Vec<ProofContext> = (0..200).map(|i| base_ctx(&format!("n11-{i}"))).collect();
    let result = compose_n(contexts);
    assert!(
        result.is_ok() || result.is_err(),
        "N11: compose_n(200) must not panic"
    );
}

// ── N12: Profile with 100 gap requirements ────────────────────────────────────

#[test]
fn n12_profile_with_100_gap_requirements_does_not_panic() {
    let mut ctx = base_ctx("n12");
    for i in 0..100 {
        ctx.gaps.push(GapRecord::open(format!("g{i}"), "gap"));
    }
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: (0..100)
            .map(|i| GapRequirement {
                gap_id: format!("g{i}"),
                minimum_status: RequiredStatus::ClosedRequired,
            })
            .collect(),
    });
    let result = compile(ctx);
    assert!(
        result.is_ok() || result.is_err(),
        "N12: profile with 100 required gaps must not panic"
    );
}

// ── N13: Very long field strings ──────────────────────────────────────────────

#[test]
fn n13_long_field_strings_do_not_panic() {
    let long = "Z".repeat(10_000);
    let hash = compute_provenance_hash(&long, &long, &long, &long);
    let ctx = ProofContext {
        claim_id: long.clone(),
        candidate_id: long.clone(),
        context_id: long.clone(),
        context_fingerprint: "fp-n13".into(),
        allowed_use: long.clone(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![],
        tokens: vec![ProofToken {
            token_id: "n13-tok".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
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
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let result = compile(ctx);
    assert!(
        result.is_ok() || result.is_err(),
        "N13: long field strings must not panic in compile()"
    );
}
