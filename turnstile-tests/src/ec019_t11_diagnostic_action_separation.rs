/// EC-019 — T11: Diagnostic / action separation (exhaustive composition).
///
/// T11: Diagnostic evidence cannot compose into action.
///   The meet of two permissions preserves the weaker permission's action set.
///   Specifically: meet(DIA, X) < AEX for all X, because DIA < AEX.
///
/// This means: if one composition input's authority ceiling is DIA, the
/// composed context's authority ceiling (which is meet of both) is at most DIA,
/// and no action permission can be emitted.
///
/// Note on composition semantics: compose() creates a new combined context with:
///   - authority_ceiling = meet(ceil1, ceil2)
///   - profiles = union, taking stricter requirements on conflict
///   - tokens = union (first context's IDs are kept)
///   - gaps = union, minimum status
///
/// T11 is enforced via the authority ceiling meet, not by preventing profile
/// combination.  The test for T11 is: a DIA authority ceiling in one input
/// must cap the composed output below any action permission.
///
/// Also covers:
///   - ESC ceiling blocks AAA
///   - ROL ceiling blocks AAA
///   - ETA ceiling blocks AAA
///   - OOC in any input of compose_n dominates the composed membership
use chrono::Utc;
use turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn ctx_with_ceiling(suffix: &str, ceiling: Permission) -> ProofContext {
    let claim_id = format!("claim-t11-{suffix}");
    let candidate_id = format!("z-t11-{suffix}");
    let context_id = format!("ctx-t11-{suffix}");
    let allowed_use = "t11-shared-use";
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-t11-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-t11-{suffix}"),
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
        authority_ceiling: ceiling,
        membership: Membership::InClass,
    }
}

fn action_permissions() -> [Permission; 3] {
    [Permission::AEX, Permission::ALR, Permission::AAA]
}

// ── T11: DIA authority ceiling in one input blocks action in composed ─────────

#[test]
fn t11_dia_ceiling_in_one_input_blocks_all_action_permissions() {
    let ctx_dia_ceil = ctx_with_ceiling("dia-ceil", Permission::DIA);
    let ctx_aaa = ctx_with_ceiling("aaa", Permission::AAA);

    // Verify the DIA-ceiling context alone emits DIA.
    let p_dia = compile(ctx_dia_ceil.clone()).unwrap().permission;
    assert_eq!(
        p_dia,
        Permission::DIA,
        "setup: ctx with DIA ceiling must emit DIA"
    );

    let composed = compose(ctx_dia_ceil, ctx_aaa).unwrap();
    let pc = compile(composed).unwrap().permission;

    for &action in &action_permissions() {
        assert!(
            pc < action,
            "T11: DIA ceiling in one input must block {action} in composed; got {pc}"
        );
    }
}

#[test]
fn t11_dia_ceiling_is_symmetric_blocker() {
    // Order of composition must not matter for the ceiling meet.
    let ctx1 = ctx_with_ceiling("dia-s1", Permission::DIA);
    let ctx2 = ctx_with_ceiling("aaa-s2", Permission::AAA);

    let c1 = compose(ctx1.clone(), ctx2.clone()).unwrap();
    let c2 = compose(ctx2, ctx1).unwrap();

    let p1 = compile(c1).unwrap().permission;
    let p2 = compile(c2).unwrap().permission;

    for &action in &action_permissions() {
        assert!(
            p1 < action,
            "T11 symmetric: c1 must not yield {action}; got {p1}"
        );
        assert!(
            p2 < action,
            "T11 symmetric: c2 must not yield {action}; got {p2}"
        );
    }
}

// ── T11: Sub-DIA ceilings also block action ───────────────────────────────────

#[test]
fn t11_sub_dia_ceilings_block_action_permissions() {
    // ESC, ROL, ETA, REF, UNS, EXP, OOC — all below DIA — must also block action.
    let sub_dia = [
        Permission::ESC,
        Permission::ROL,
        Permission::ETA,
        Permission::REF,
        Permission::UNS,
    ];

    for &low_ceil in &sub_dia {
        let ctx_low = ctx_with_ceiling(&format!("low-{low_ceil}"), low_ceil);
        let ctx_aaa = ctx_with_ceiling(&format!("aaa-for-{low_ceil}"), Permission::AAA);

        let composed = compose(ctx_low, ctx_aaa).unwrap();
        let pc = compile(composed).unwrap().permission;

        for &action in &action_permissions() {
            assert!(
                pc < action,
                "T11: ceiling {low_ceil} + AAA must not yield {action}; got {pc}"
            );
        }
    }
}

// ── T11: OOC in one input of compose → composed membership is OOC ─────────────

#[test]
fn t11_ooc_input_in_compose_yields_ooc_membership() {
    let ctx_ooc = ProofContext {
        claim_id: "claim-t11-ooc".into(),
        candidate_id: "z-t11-ooc".into(),
        context_id: "ctx-t11-ooc".into(),
        context_fingerprint: "fp-t11-ooc".into(),
        allowed_use: "t11-shared-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::OutOfClassExact,
    };
    let ctx_aaa = ctx_with_ceiling("for-ooc", Permission::AAA);

    let composed = compose(ctx_ooc, ctx_aaa).unwrap();
    let pc = compile(composed).unwrap().permission;
    assert_eq!(
        pc,
        Permission::OOC,
        "T11: OOC membership in any compose input must yield OOC in composed context"
    );
}

// ── T11: REV ceiling does not yield AEX or above ─────────────────────────────

#[test]
fn t11_rev_ceiling_blocks_action_permissions() {
    let ctx_rev = ctx_with_ceiling("rev-ceil", Permission::REV);
    let ctx_aaa = ctx_with_ceiling("aaa-rev", Permission::AAA);

    let composed = compose(ctx_rev, ctx_aaa).unwrap();
    let pc = compile(composed).unwrap().permission;
    for &action in &action_permissions() {
        assert!(
            pc < action,
            "T11: REV ceiling + AAA must not yield {action}; got {pc}"
        );
    }
}

// ── T11: meet lattice arithmetic (T8 basis for T11) ──────────────────────────

#[test]
fn t11_meet_of_dia_and_any_permission_is_at_most_dia() {
    // This is the lattice basis: meet(DIA, X) ≤ DIA for all X.
    // So if one input's authority ceiling is DIA, the composed ceiling ≤ DIA.
    for p in Permission::descending() {
        let m = Permission::DIA.meet(p);
        assert!(
            m <= Permission::DIA,
            "T11 lattice: meet(DIA, {p}) = {m} must be ≤ DIA"
        );
    }
}

#[test]
fn t11_authority_ceiling_meet_never_promotes() {
    // For all (c1, c2), meet(c1, c2) ≤ min(c1, c2).
    let all: Vec<Permission> = Permission::descending().collect();
    for &c1 in &all {
        for &c2 in &all {
            let m = c1.meet(c2);
            assert!(m <= c1, "T11: meet({c1}, {c2}) = {m} must be ≤ {c1}");
            assert!(m <= c2, "T11: meet({c1}, {c2}) = {m} must be ≤ {c2}");
        }
    }
}

// ── Regression: single-input context with DIA ceiling ────────────────────────

#[test]
fn single_context_dia_ceiling_blocks_action() {
    let ctx = ctx_with_ceiling("single-dia", Permission::DIA);
    let j = compile(ctx).unwrap();
    for &action in &action_permissions() {
        assert!(
            j.permission < action,
            "single context DIA ceiling must block {action}; got {}",
            j.permission
        );
    }
}

#[test]
fn composed_authority_ceiling_equals_meet_of_inputs() {
    let all = [
        Permission::OOC,
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::AAA,
    ];
    for &c1 in &all {
        for &c2 in &all {
            let ctx1 = ctx_with_ceiling(&format!("ceil-a-{c1}"), c1);
            let ctx2 = ctx_with_ceiling(&format!("ceil-b-{c2}"), c2);
            let composed = compose(ctx1, ctx2).unwrap();
            let expected_ceiling = c1.meet(c2);
            assert_eq!(
                composed.authority_ceiling, expected_ceiling,
                "composed ceiling must be meet({c1}, {c2}) = {expected_ceiling}; got {}",
                composed.authority_ceiling
            );
        }
    }
}
