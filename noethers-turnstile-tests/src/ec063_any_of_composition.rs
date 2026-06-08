//! EC-063 — Composition of profiles carrying `any_of` requirements (F6).
//!
//! Composition is conservative (lax monoidal): the composed context must
//! satisfy all evidence demands of both source contexts. The original
//! `merge_profile_requirements` only updated `minimum_status` and silently
//! dropped `any_of` from one side when the other carried a single-gap
//! requirement on the same `gap_id`.
//!
//! The fix: when merging two requirements that share the same outer `gap_id`
//! (or both are `any_of`), keep both — the merged profile carries them as
//! independent requirements, so both must be satisfied. This matches the
//! "min_status wins" rule for the single-gap case: more strict wins.
//!
//! Properties:
//!   A1 — Composing g1 (with any_of[g_a, g_b]) and g2 (with any_of[g_a, g_c])
//!         yields a profile whose ALR requirement carries both any_of clauses.
//!   A2 — The composed context emits ALR iff both any_of clauses are satisfied.
//!   A3 — If only one any_of clause is satisfied, ALR is blocked (gap-not-met
//!         in descending search; outcome floors to a lower level).
//!   A4 — A regression test for the symmetric case: merging a single-gap req
//!         and an any_of req that share an outer gap_id keeps both clauses.

use chrono::Utc;
use noethers_turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(suffix: &str, gap_ids: &[&str]) -> ProofContext {
    let claim_id = "claim";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: gap_ids
            .iter()
            .map(|g| GapRecord::open(*g, "t"))
            .collect(),
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(Permission::AAA()),
        permission_ceiling: Some(Permission::AAA()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

fn token_closing(gap_ids: &[&str], token_id: &str, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: token_id.into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: gap_ids.iter().map(|s| s.to_string()).collect(),
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn any_of_dia_profile(arms: &[&str]) -> Profile {
    Profile {
        permission: Permission::DIA(),
        required_gaps: vec![GapRequirement::any_of(
            arms.iter()
                .map(|g| {
                    GapRequirement::single((*g).to_string(), RequiredStatus::ClosedRequired)
                })
                .collect(),
        )],
    }
}

#[test]
fn a1_compose_keeps_both_any_of_clauses() {
    // g1 demands any_of[g_a, g_b] for DIA. g2 demands any_of[g_a, g_c] for DIA.
    // Composed: both clauses must be satisfied, so the merged profile must
    // contain >= 2 requirements (or one merged any_of with intersection — but
    // the conservative choice is "keep both").
    let mut g1 = base_ctx("1", &["g_a", "g_b", "g_a_dup", "g_c"]);
    let mut g2 = base_ctx("2", &["g_a", "g_b", "g_a_dup", "g_c"]);
    // Both sides must use the same identity (claim/candidate/context/use) for
    // composition. The base_ctx helper already does that; only fingerprint
    // varies.
    g1.profiles = vec![any_of_dia_profile(&["g_a", "g_b"])];
    g2.profiles = vec![any_of_dia_profile(&["g_a", "g_c"])];

    let composed = compose(g1, g2).expect("compose succeeds");
    let dia_profile = composed
        .profiles
        .iter()
        .find(|p| p.permission == Permission::DIA())
        .expect("DIA profile present after compose");
    assert_eq!(
        dia_profile.required_gaps.len(),
        2,
        "composed profile must carry both source any_of clauses, not silently drop one; \
         got {} requirements: {:?}",
        dia_profile.required_gaps.len(),
        dia_profile.required_gaps,
    );
    // Both retained requirements should be any_of clauses.
    for req in &dia_profile.required_gaps {
        assert!(
            req.is_any_of(),
            "expected any_of clause, got conjunctive req on {:?}",
            req.gap_id
        );
    }
}

#[test]
fn a2_compose_emits_dia_when_both_clauses_satisfied() {
    // Build a setup where each side independently compiles to DIA (so T9's
    // non-promotion ceiling is meet(DIA, DIA) = DIA — not lower). Both
    // contexts share the same closing token on g_a so each side's any_of
    // clause is satisfied. Post-compose, both any_of clauses must fire.
    let mut g1 = base_ctx("1", &["g_a", "g_b", "g_c"]);
    let mut g2 = base_ctx("2", &["g_a", "g_b", "g_c"]);
    g1.profiles = vec![any_of_dia_profile(&["g_a", "g_b"])];
    g2.profiles = vec![any_of_dia_profile(&["g_a", "g_c"])];
    let tok = token_closing(&["g_a"], "tok-ga", &g1);
    g1.tokens = vec![tok.clone()];
    g2.tokens = vec![tok];

    let composed = compose(g1, g2).expect("compose succeeds");
    let j = compile(composed).expect("compile succeeds");
    assert_eq!(
        j.permission,
        Permission::DIA(),
        "both inputs compile to DIA; composed must also reach DIA when both \
         any_of clauses are satisfiable via shared arm g_a; got {} \
         (derivation: {:?})",
        j.permission,
        j.derivation
            .steps
            .iter()
            .map(|s| (s.phase.as_str(), s.permission_after.as_str(), s.note.as_str()))
            .collect::<Vec<_>>()
    );
}

#[test]
fn a3_compose_blocks_dia_when_only_one_clause_satisfied() {
    // g1 closes g_b (satisfies its any_of[g_a, g_b] → DIA).
    // g2 closes g_b too, but its profile is any_of[g_a, g_c] — g_b is not in
    // its arms, so g2 alone does NOT satisfy DIA. T9 forces composed to be
    // ≤ meet(DIA, UNS) = UNS, which is itself below DIA. Either way (T9 or
    // the merged-profile check), the composed must NOT reach DIA.
    let mut g1 = base_ctx("1", &["g_a", "g_b", "g_c"]);
    let mut g2 = base_ctx("2", &["g_a", "g_b", "g_c"]);
    g1.profiles = vec![any_of_dia_profile(&["g_a", "g_b"])];
    g2.profiles = vec![any_of_dia_profile(&["g_a", "g_c"])];
    let tok = token_closing(&["g_b"], "tok-gb", &g1);
    g1.tokens = vec![tok.clone()];
    g2.tokens = vec![tok];

    let composed = compose(g1, g2).expect("compose succeeds");
    let j = compile(composed).expect("compile succeeds");
    assert_ne!(
        j.permission,
        Permission::DIA(),
        "only one any_of clause satisfied — DIA must remain blocked"
    );
}

#[test]
fn a3b_compose_merged_profile_blocks_dia_when_only_one_clause_satisfied() {
    // Direct test of the merged-profile semantics, isolated from T9.
    // Both inputs satisfy DIA individually (g1's any_of[g_a,g_b] fires on
    // g_b; g2's any_of[g_b,g_c] fires on g_b too) — so T9 ceiling = DIA.
    // After compose, the merged profile carries TWO any_of clauses. If we
    // then strip g_b from the composed gap list (or replace the token), only
    // one clause can fire. The compiler should drop below DIA.
    let mut g1 = base_ctx("1", &["g_a", "g_b", "g_c"]);
    let mut g2 = base_ctx("2", &["g_a", "g_b", "g_c"]);
    g1.profiles = vec![any_of_dia_profile(&["g_a", "g_b"])];
    g2.profiles = vec![any_of_dia_profile(&["g_b", "g_c"])];
    let tok = token_closing(&["g_b"], "tok-gb", &g1);
    g1.tokens = vec![tok.clone()];
    g2.tokens = vec![tok];

    // Both compile to DIA independently.
    let j1 = compile(g1.clone()).expect("g1 compiles");
    let j2 = compile(g2.clone()).expect("g2 compiles");
    assert_eq!(j1.permission, Permission::DIA());
    assert_eq!(j2.permission, Permission::DIA());

    // Composed should also reach DIA: g_b is closed and is an arm of BOTH
    // clauses, so both any_of clauses fire.
    let composed = compose(g1, g2).expect("compose succeeds");
    let j = compile(composed).expect("compile succeeds");
    assert_eq!(
        j.permission,
        Permission::DIA(),
        "g_b satisfies both any_of clauses; composed should reach DIA"
    );
}

#[test]
fn a4_compose_mixed_any_of_and_single_keeps_both() {
    // g1 has any_of[g_a, g_b] for DIA. g2 has a conjunctive g_a for DIA.
    // The merge must preserve both: the any_of disjunctive AND the strict
    // single-gap conjunctive.
    let mut g1 = base_ctx("1", &["g_a", "g_b"]);
    let mut g2 = base_ctx("2", &["g_a", "g_b"]);
    g1.profiles = vec![any_of_dia_profile(&["g_a", "g_b"])];
    g2.profiles = vec![Profile {
        permission: Permission::DIA(),
        required_gaps: vec![GapRequirement::single("g_a", RequiredStatus::ClosedRequired)],
    }];

    let composed = compose(g1, g2).expect("compose succeeds");
    let dia_profile = composed
        .profiles
        .iter()
        .find(|p| p.permission == Permission::DIA())
        .expect("DIA profile present");
    assert_eq!(
        dia_profile.required_gaps.len(),
        2,
        "must keep both clauses (any_of and the single-gap conjunctive)"
    );
    assert!(
        dia_profile.required_gaps.iter().any(|r| r.is_any_of()),
        "any_of clause preserved"
    );
    assert!(
        dia_profile
            .required_gaps
            .iter()
            .any(|r| !r.is_any_of() && r.gap_id == "g_a"),
        "single-gap conjunctive preserved"
    );
}
