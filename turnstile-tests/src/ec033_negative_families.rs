/// EC-033 — Negative families N1–N10 (EC-001 §34).
///
/// EC-001 §34 defines ten negative families: exact deterministic computations
/// that are OUT_OF_CLASS unless an approximate consequential layer is added.
///
/// Pre-registered expectation for every negative family:
///   - Fake proof tokens attached to an OOC system MUST NOT promote it
///   - membership ≠ InClass → outcome = OOC regardless of token quality
///   - These are exactly what T1 (Fake-token non-promotion) guarantees
///
/// Negative families:
///   N1  — Sorting a list
///   N2  — Exact SQL over immutable snapshot
///   N3  — File hash verification
///   N4  — Unit conversion
///   N5  — Required-field validation
///   N6  — Static webpage rendering
///   N7  — Explicit CRUD update
///   N8  — Regex matching
///   N9  — Feature-flag read
///   N10 — Cache lookup
use chrono::Utc;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ooc_ctx(id: &str, membership: Membership) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{id}"),
        candidate_id: format!("z-{id}"),
        context_id: format!("ctx-{id}"),
        context_fingerprint: format!("fp-{id}"),
        allowed_use: "diagnostics".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership,
    }
}

fn full_evidence_token(ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: "tok-fake-evidence".into(),
        token_type: "FAKE_PROOF".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "attacker".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn with_fake_proof(mut ctx: ProofContext) -> ProofContext {
    ctx.gaps.push(GapRecord::closed("g1", "fake_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::AAA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = full_evidence_token(&ctx);
    ctx.tokens.push(tok);
    ctx
}

/// Assert that an OOC system produces OOC even with full fake evidence.
fn assert_ooc_with_fake_proof(id: &str, membership: Membership) {
    let ctx = with_fake_proof(ooc_ctx(id, membership));
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "N family {id}: OOC system with fake proof must remain OOC"
    );
}

// ── N1: Sorting a list ────────────────────────────────────────────────────────

#[test]
fn n1_sort_is_out_of_class_exact() {
    assert_ooc_with_fake_proof("sort", Membership::OutOfClassExact);
}

// ── N2: Exact SQL over immutable snapshot ─────────────────────────────────────

#[test]
fn n2_exact_sql_is_out_of_class_exact() {
    assert_ooc_with_fake_proof("sql", Membership::OutOfClassExact);
}

// ── N3: File hash verification ────────────────────────────────────────────────

#[test]
fn n3_file_hash_verification_is_out_of_class_exact() {
    assert_ooc_with_fake_proof("hash-verify", Membership::OutOfClassExact);
}

// ── N4: Unit conversion ───────────────────────────────────────────────────────

#[test]
fn n4_unit_conversion_is_out_of_class_exact() {
    assert_ooc_with_fake_proof("unit-convert", Membership::OutOfClassExact);
}

// ── N5: Required-field validation ────────────────────────────────────────────

#[test]
fn n5_field_validation_is_out_of_class_exact() {
    assert_ooc_with_fake_proof("field-validation", Membership::OutOfClassExact);
}

// ── N6: Static webpage rendering ─────────────────────────────────────────────

#[test]
fn n6_static_rendering_is_out_of_class_no_consequential_use() {
    assert_ooc_with_fake_proof("static-render", Membership::OutOfClassNoConsequentialUse);
}

// ── N7: Explicit CRUD update ──────────────────────────────────────────────────

#[test]
fn n7_explicit_crud_is_out_of_class_authorized_deterministic_write() {
    assert_ooc_with_fake_proof(
        "crud-update",
        Membership::OutOfClassAuthorizedDeterministicWrite,
    );
}

// ── N8: Regex matching ────────────────────────────────────────────────────────

#[test]
fn n8_regex_match_is_out_of_class_exact() {
    assert_ooc_with_fake_proof("regex-match", Membership::OutOfClassExact);
}

// ── N9: Feature-flag read ─────────────────────────────────────────────────────

#[test]
fn n9_feature_flag_read_is_out_of_class_no_consequential_use() {
    assert_ooc_with_fake_proof("feature-flag", Membership::OutOfClassNoConsequentialUse);
}

// ── N10: Cache lookup ─────────────────────────────────────────────────────────

#[test]
fn n10_cache_lookup_is_out_of_class_no_consequential_use() {
    assert_ooc_with_fake_proof("cache-lookup", Membership::OutOfClassNoConsequentialUse);
}

// ── Cross-family invariant: all OOC variants produce OOC ─────────────────────

#[test]
fn all_ooc_variants_absorb_fake_proof() {
    let variants = vec![
        Membership::OutOfClassExact,
        Membership::OutOfClassAuthorizedDeterministicWrite,
        Membership::OutOfClassNoConsequentialUse,
        Membership::OutOfClassOther("any-other-reason".into()),
    ];

    for variant in variants {
        assert_ooc_with_fake_proof("multi-variant", variant);
    }
}

// ── Boundary check: in-class system CAN be admitted ──────────────────────────
// Confirms the negative result is about OOC membership, not a broken compiler.

#[test]
fn in_class_system_with_proof_is_admitted() {
    let mut ctx = ProofContext {
        claim_id: "in-class-claim".into(),
        candidate_id: "z-in-class".into(),
        context_id: "ctx-ic".into(),
        context_fingerprint: "fp-ic".into(),
        allowed_use: "diagnostics".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "truth_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ctx.tokens.push(ProofToken {
        token_id: "tok-ic".into(),
        token_type: "TEST".into(),
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
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "In-class system with valid proof should be admitted"
    );
}

// ── OOC membership derivation step appears first ─────────────────────────────

#[test]
fn ooc_membership_derivation_step_is_first() {
    let ctx = with_fake_proof(ooc_ctx("deriv-check", Membership::OutOfClassExact));
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
    assert_eq!(
        j.derivation.steps.first().map(|s| s.phase.as_str()),
        Some("membership_check"),
        "Membership check must be the first (and only) derivation step for OOC"
    );
    assert_eq!(
        j.derivation.steps.len(),
        1,
        "OOC early exit must produce exactly one derivation step"
    );
}
