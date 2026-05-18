/// EC-040 — Composition identity laws and lax monoidal structure.
///
/// EC-001 §24 and the lax monoidal specification require composition to satisfy:
///   - Identity: compose(empty_context, ctx) degrades as expected (not a true unit,
///     but composing with a "minimal" context must not widen any field)
///   - Associativity: compose(compose(A,B),C) ≡ compose(A,compose(B,C)) for authority
///     ceiling, expiry, and disallowed_uses
///   - Left/right behavior: compose(ctx, ctx) must equal ctx for idempotent fields
///   - T10: N-ary composition is equivalent to left-fold compose
///
///   CI1  — compose(ctx, ctx) is idempotent for authority_ceiling
///   CI2  — compose(ctx, ctx) is idempotent for disallowed_uses
///   CI3  — compose(ctx, ctx) is idempotent for scope
///   CI4  — compose(ctx, ctx): gap status is min (Open min Open = Open)
///   CI5  — Associativity: authority ceiling under nested compose
///   CI6  — Associativity: expiry under nested compose
///   CI7  — Associativity: disallowed_uses under nested compose
///   CI8  — compose_n([A,B,C]) = compose(compose(A,B),C) (left-fold equivalence)
///   CI9  — compose(A, compose(B, C)) = compose_n([A,B,C]) (right-associative equivalence)
///   CI10 — compose with UseConflict always fails closed
///   CI11 — compose with TokenConflict always fails closed
///   CI12 — compose_n single-element is identity
use chrono::Utc;
use noethers_noethers_turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    error::CompositionError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, GapStatus, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(id: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{id}"),
        candidate_id: format!("z-{id}"),
        context_id: format!("ctx-{id}"),
        context_fingerprint: format!("fp-{id}"),
        allowed_use: "compose-test".into(),
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

fn valid_token(id: &str, closes: Vec<&str>, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: id.into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: closes.into_iter().map(String::from).collect(),
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── CI1: compose(ctx, ctx) is idempotent for authority_ceiling ────────────────

#[test]
fn ci1_compose_self_authority_ceiling_idempotent() {
    let mut ctx = base_ctx("ci1");
    ctx.authority_ceiling = Permission::DIA;

    let composed = compose(ctx.clone(), ctx.clone()).unwrap();
    assert_eq!(
        composed.authority_ceiling,
        Permission::DIA,
        "CI1: compose(ctx,ctx) authority_ceiling must equal ctx's ceiling"
    );
}

// ── CI2: compose(ctx, ctx) is idempotent for disallowed_uses ─────────────────

#[test]
fn ci2_compose_self_disallowed_uses_idempotent() {
    let mut ctx = base_ctx("ci2");
    ctx.disallowed_uses = vec!["write".into(), "delete".into()];

    let composed = compose(ctx.clone(), ctx.clone()).unwrap();
    let mut d1 = composed.disallowed_uses.clone();
    d1.sort();
    let mut d2 = ctx.disallowed_uses.clone();
    d2.sort();

    assert_eq!(
        d1, d2,
        "CI2: compose(ctx,ctx) disallowed_uses must not grow (dedup)"
    );
}

// ── CI3: compose(ctx, ctx) is idempotent for scope ───────────────────────────

#[test]
fn ci3_compose_self_scope_idempotent() {
    let mut ctx = base_ctx("ci3");
    ctx.scope = Scope {
        allowed_candidates: vec!["z-1".into(), "z-2".into()],
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    };

    let composed = compose(ctx.clone(), ctx.clone()).unwrap();
    assert_eq!(
        composed.scope.allowed_candidates, ctx.scope.allowed_candidates,
        "CI3: compose(ctx,ctx) scope must equal ctx's scope (intersection with self)"
    );
}

// ── CI4: compose(ctx, ctx) gap status is minimum (Open min Open = Open) ───────

#[test]
fn ci4_compose_self_gap_status_is_minimum_open() {
    let mut ctx = base_ctx("ci4");
    ctx.gaps.push(GapRecord::open("g1", "t"));

    let composed = compose(ctx.clone(), ctx.clone()).unwrap();
    assert!(
        matches!(composed.find_gap("g1").unwrap().status, GapStatus::Open),
        "CI4: compose(Open,Open) must equal Open"
    );
}

#[test]
fn ci4_compose_self_gap_status_is_minimum_closed() {
    let mut ctx = base_ctx("ci4c");
    ctx.gaps.push(GapRecord::closed("g1", "t"));

    let composed = compose(ctx.clone(), ctx.clone()).unwrap();
    assert!(
        matches!(composed.find_gap("g1").unwrap().status, GapStatus::Closed),
        "CI4: compose(Closed,Closed) must equal Closed"
    );
}

// ── CI5: Associativity of authority ceiling under nested compose ──────────────

#[test]
fn ci5_authority_ceiling_is_associative() {
    let mut a = base_ctx("ci5a");
    a.authority_ceiling = Permission::AEX;
    let mut b = base_ctx("ci5b");
    b.authority_ceiling = Permission::DIA;
    let mut c = base_ctx("ci5c");
    c.authority_ceiling = Permission::REV;

    // (A ∩ B) ∩ C
    let lhs = {
        let ab = compose(a.clone(), b.clone()).unwrap();
        compose(ab, c.clone()).unwrap()
    };

    // A ∩ (B ∩ C)
    let rhs = {
        let bc = compose(b.clone(), c.clone()).unwrap();
        compose(a.clone(), bc).unwrap()
    };

    assert_eq!(
        lhs.authority_ceiling, rhs.authority_ceiling,
        "CI5: authority_ceiling composition must be associative"
    );
    // Meet(AEX, DIA, REV) = DIA (minimum of the three)
    assert_eq!(
        lhs.authority_ceiling,
        Permission::DIA,
        "CI5: meet(AEX, DIA, REV) must be DIA"
    );
}

// ── CI6: Associativity of expiry under nested compose ────────────────────────

#[test]
fn ci6_expiry_is_associative() {
    let t = Utc::now();
    let mut a = base_ctx("ci6a");
    a.expiry = Expiry::at(t + chrono::Duration::seconds(300));
    let mut b = base_ctx("ci6b");
    b.expiry = Expiry::at(t + chrono::Duration::seconds(100)); // earliest
    let mut c = base_ctx("ci6c");
    c.expiry = Expiry::at(t + chrono::Duration::seconds(200));

    let lhs = {
        let ab = compose(a.clone(), b.clone()).unwrap();
        compose(ab, c.clone()).unwrap()
    };

    let rhs = {
        let bc = compose(b.clone(), c.clone()).unwrap();
        compose(a.clone(), bc).unwrap()
    };

    assert_eq!(
        lhs.expiry.deadline, rhs.expiry.deadline,
        "CI6: expiry composition must be associative"
    );
    assert_eq!(
        lhs.expiry.deadline,
        Some(t + chrono::Duration::seconds(100)),
        "CI6: minimum expiry must be selected (100s)"
    );
}

// ── CI7: Associativity of disallowed_uses under nested compose ────────────────

#[test]
fn ci7_disallowed_uses_is_associative() {
    let mut a = base_ctx("ci7a");
    a.disallowed_uses = vec!["use-1".into()];
    let mut b = base_ctx("ci7b");
    b.disallowed_uses = vec!["use-2".into()];
    let mut c = base_ctx("ci7c");
    c.disallowed_uses = vec!["use-3".into()];

    let lhs = {
        let ab = compose(a.clone(), b.clone()).unwrap();
        compose(ab, c.clone()).unwrap()
    };

    let rhs = {
        let bc = compose(b.clone(), c.clone()).unwrap();
        compose(a.clone(), bc).unwrap()
    };

    let mut lhs_uses = lhs.disallowed_uses.clone();
    let mut rhs_uses = rhs.disallowed_uses.clone();
    lhs_uses.sort();
    rhs_uses.sort();

    assert_eq!(
        lhs_uses, rhs_uses,
        "CI7: disallowed_uses composition must be associative"
    );
    assert_eq!(
        lhs_uses.len(),
        3,
        "CI7: all three disallowed_uses must be present"
    );
}

// ── CI8: compose_n([A,B,C]) = left-fold compose(compose(A,B),C) ──────────────

#[test]
fn ci8_compose_n_equals_left_fold() {
    let mut a = base_ctx("ci8a");
    a.authority_ceiling = Permission::AEX;
    a.disallowed_uses = vec!["use-a".into()];

    let mut b = base_ctx("ci8b");
    b.authority_ceiling = Permission::DIA;
    b.disallowed_uses = vec!["use-b".into()];

    let mut c = base_ctx("ci8c");
    c.authority_ceiling = Permission::REV;
    c.disallowed_uses = vec!["use-c".into()];

    // Left-fold
    let left_fold = {
        let ab = compose(a.clone(), b.clone()).unwrap();
        compose(ab, c.clone()).unwrap()
    };

    // compose_n
    let n_ary = compose_n(vec![a.clone(), b.clone(), c.clone()]).unwrap();

    assert_eq!(
        left_fold.authority_ceiling, n_ary.authority_ceiling,
        "CI8: compose_n authority_ceiling must equal left-fold"
    );

    let mut lf_uses = left_fold.disallowed_uses.clone();
    let mut na_uses = n_ary.disallowed_uses.clone();
    lf_uses.sort();
    na_uses.sort();
    assert_eq!(
        lf_uses, na_uses,
        "CI8: compose_n disallowed_uses must equal left-fold"
    );
}

// ── CI9: A ∩ (B ∩ C) = compose_n([A,B,C]) for authority ceiling ──────────────

#[test]
fn ci9_right_associative_equals_compose_n() {
    let mut a = base_ctx("ci9a");
    a.authority_ceiling = Permission::AEX;
    let mut b = base_ctx("ci9b");
    b.authority_ceiling = Permission::DIA;
    let mut c = base_ctx("ci9c");
    c.authority_ceiling = Permission::REV;

    let right_fold = {
        let bc = compose(b.clone(), c.clone()).unwrap();
        compose(a.clone(), bc).unwrap()
    };

    let n_ary = compose_n(vec![a, b, c]).unwrap();

    assert_eq!(
        right_fold.authority_ceiling, n_ary.authority_ceiling,
        "CI9: right-associative compose must equal compose_n for authority ceiling"
    );
}

// ── CI10: UseConflict always fails closed ─────────────────────────────────────

#[test]
fn ci10_use_conflict_always_fails_closed() {
    let ctx1 = base_ctx("ci10a"); // allowed_use = "compose-test"
    let mut ctx2 = base_ctx("ci10b");
    ctx2.allowed_use = "different-use".into(); // conflict

    let result = compose(ctx1, ctx2);
    assert!(
        matches!(result, Err(CompositionError::UseConflict)),
        "CI10: UseConflict must fail closed"
    );
}

#[test]
fn ci10_use_conflict_is_symmetric() {
    let ctx_a = base_ctx("ci10ca"); // allowed_use = "compose-test"
    let mut ctx_b = base_ctx("ci10cb");
    ctx_b.allowed_use = "different".into();

    let fwd = compose(ctx_a.clone(), ctx_b.clone());
    let rev = compose(ctx_b, ctx_a);

    assert!(matches!(fwd, Err(CompositionError::UseConflict)));
    assert!(matches!(rev, Err(CompositionError::UseConflict)));
}

// ── CI11: TokenConflict always fails closed ───────────────────────────────────

#[test]
fn ci11_token_conflict_always_fails_closed() {
    let mut ctx1 = base_ctx("ci11a");
    let mut ctx2 = base_ctx("ci11b");

    let tok1 = valid_token("shared-tok", vec!["g1"], &ctx1);
    let mut tok2 = valid_token("shared-tok", vec!["g2"], &ctx2); // different closes
    tok2.token_id = "shared-tok".into();

    ctx1.gaps.push(GapRecord::open("g1", "t"));
    ctx2.gaps.push(GapRecord::open("g2", "t"));
    ctx1.tokens.push(tok1);
    ctx2.tokens.push(tok2);

    let result = compose(ctx1, ctx2);
    assert!(
        matches!(result, Err(CompositionError::TokenConflict { .. })),
        "CI11: TokenConflict must fail closed"
    );
}

// ── CI12: compose_n single-element is equivalent to the element ──────────────

#[test]
fn ci12_compose_n_single_element_identity() {
    let mut ctx = base_ctx("ci12");
    ctx.authority_ceiling = Permission::DIA;
    ctx.disallowed_uses = vec!["write".into()];
    ctx.gaps.push(GapRecord::closed("g1", "t"));

    let result = compose_n(vec![ctx.clone()]).unwrap();

    assert_eq!(
        result.authority_ceiling, ctx.authority_ceiling,
        "CI12: single-element compose_n authority_ceiling"
    );
    assert_eq!(
        result.disallowed_uses, ctx.disallowed_uses,
        "CI12: single-element compose_n disallowed_uses"
    );
    assert_eq!(
        result.gaps.len(),
        ctx.gaps.len(),
        "CI12: single-element compose_n gaps"
    );
}

// ── Compile-then-compose non-promotion: end-to-end ────────────────────────────

#[test]
fn compile_compose_non_promotion_end_to_end() {
    let mut ctx1 = base_ctx("e2e1");
    ctx1.gaps.push(GapRecord::closed("g1", "t"));
    ctx1.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok1 = valid_token("tok-e2e1", vec!["g1"], &ctx1);
    ctx1.tokens.push(tok1);

    let mut ctx2 = base_ctx("e2e2");
    ctx2.gaps.push(GapRecord::closed("g1", "t"));
    ctx2.authority_ceiling = Permission::ROL; // this will cap the composed result
    ctx2.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok2 = valid_token("tok-e2e2", vec!["g1"], &ctx2);
    ctx2.tokens.push(tok2);

    let p1 = compile(ctx1.clone()).unwrap().permission;
    let p2 = compile(ctx2.clone()).unwrap().permission;

    let composed = compose(ctx1, ctx2).unwrap();
    let p_composed = compile(composed).unwrap().permission;

    // Non-promotion: composed permission ≤ min(p1, p2)
    let min_input = p1.meet(p2);
    assert!(
        p_composed <= min_input,
        "Non-promotion: compose then compile must give ≤ min(compile(ctx1), compile(ctx2)): {p_composed} > {min_input}"
    );
}
