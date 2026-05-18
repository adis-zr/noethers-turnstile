/// EC-015 — Disallowed-use accumulation invariant (T13).
///
/// T13: Disallowed-use accumulation
///   The disallowed_uses list is a monotone accumulator.  Composition always
///   takes the union of both contexts' disallowed_uses.  A disallowed use that
///   appears in either input must appear in the output.  It can never disappear.
///
/// Tests:
///   - Union of disjoint disallowed_uses lists
///   - Union of overlapping lists (no duplication)
///   - Empty + non-empty → non-empty (identity with empty set)
///   - Non-empty + empty → non-empty
///   - Compose-n: disallowed_uses is the union of all inputs
///   - After composition, compile() outcome is at most ROL when disallowed_uses is non-empty
///   - Disallowed use present in either input blocks AAA in composed context
///   - Proptest: for any two contexts, composed disallowed_uses ⊇ each input's list
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn make_ctx(suffix: &str, disallowed: Vec<&str>) -> ProofContext {
    let claim_id = format!("claim-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = "shared-dis-use";
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: disallowed.into_iter().map(String::from).collect(),
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-{suffix}"),
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
    }
}

// ── Union semantics ───────────────────────────────────────────────────────────

#[test]
fn disjoint_disallowed_lists_are_unioned() {
    let ctx1 = make_ctx("dis-u1", vec!["use-A", "use-B"]);
    let ctx2 = make_ctx("dis-u2", vec!["use-C", "use-D"]);
    let composed = compose(ctx1, ctx2).unwrap();

    assert!(composed.disallowed_uses.contains(&"use-A".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-B".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-C".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-D".to_string()));
    assert_eq!(
        composed.disallowed_uses.len(),
        4,
        "T13: all 4 disallowed uses must appear in union"
    );
}

#[test]
fn overlapping_disallowed_lists_no_duplication() {
    let ctx1 = make_ctx("dis-ov1", vec!["use-A", "use-B"]);
    let ctx2 = make_ctx("dis-ov2", vec!["use-B", "use-C"]);
    let composed = compose(ctx1, ctx2).unwrap();

    assert!(composed.disallowed_uses.contains(&"use-A".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-B".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-C".to_string()));
    assert_eq!(
        composed.disallowed_uses.len(),
        3,
        "T13: overlapping disallowed use must not be duplicated; expected 3, got {}",
        composed.disallowed_uses.len()
    );
}

#[test]
fn empty_plus_nonempty_yields_nonempty() {
    let ctx1 = make_ctx("dis-en1", vec![]);
    let ctx2 = make_ctx("dis-en2", vec!["use-X"]);
    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.disallowed_uses.contains(&"use-X".to_string()),
        "T13: empty + [use-X] must yield [use-X]"
    );
    assert_eq!(composed.disallowed_uses.len(), 1);
}

#[test]
fn nonempty_plus_empty_yields_nonempty() {
    let ctx1 = make_ctx("dis-ne1", vec!["use-Y"]);
    let ctx2 = make_ctx("dis-ne2", vec![]);
    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.disallowed_uses.contains(&"use-Y".to_string()),
        "T13: [use-Y] + empty must yield [use-Y]"
    );
}

#[test]
fn both_empty_stays_empty() {
    let ctx1 = make_ctx("dis-ee1", vec![]);
    let ctx2 = make_ctx("dis-ee2", vec![]);
    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.disallowed_uses.is_empty(),
        "T13: empty + empty must stay empty"
    );
}

// ── compose_n accumulates across all inputs ───────────────────────────────────

#[test]
fn compose_n_accumulates_all_disallowed_uses() {
    let ctxs = vec![
        make_ctx("dis-n1", vec!["use-P"]),
        make_ctx("dis-n2", vec!["use-Q"]),
        make_ctx("dis-n3", vec!["use-R"]),
    ];
    let composed = compose_n(ctxs).unwrap();
    assert!(composed.disallowed_uses.contains(&"use-P".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-Q".to_string()));
    assert!(composed.disallowed_uses.contains(&"use-R".to_string()));
}

// ── Effect on compile outcome ─────────────────────────────────────────────────

#[test]
fn nonempty_disallowed_blocks_aaa_after_composition() {
    let ctx1 = make_ctx("dis-blk1", vec!["use-BLOCKED"]);
    let ctx2 = make_ctx("dis-blk2", vec![]);
    let composed = compose(ctx1, ctx2).unwrap();
    let j = compile(composed).unwrap();
    assert!(
        j.permission <= Permission::ROL,
        "T13: non-empty disallowed_uses in composed context must cap outcome at ROL; got {}",
        j.permission
    );
}

#[test]
fn disallowed_from_either_input_blocks_action_in_composed() {
    // ctx1 has disallowed, ctx2 does not.  Composed must still be capped.
    let ctx1 = make_ctx("dis-ei1", vec!["dangerous"]);
    let ctx2 = make_ctx("dis-ei2", vec![]);
    let c1 = compose(ctx1.clone(), ctx2.clone()).unwrap();
    let j1 = compile(c1).unwrap();
    assert!(
        j1.permission <= Permission::ROL,
        "disallowed from ctx1 must block action in composed"
    );

    // ctx2 has disallowed, ctx1 does not.
    let ctx1b = make_ctx("dis-ei1b", vec![]);
    let ctx2b = make_ctx("dis-ei2b", vec!["dangerous"]);
    let c2 = compose(ctx1b, ctx2b).unwrap();
    let j2 = compile(c2).unwrap();
    assert!(
        j2.permission <= Permission::ROL,
        "disallowed from ctx2 must block action in composed"
    );
}

// ── Proptest: disallowed_uses ⊇ each input ────────────────────────────────────

fn arb_disallowed_list() -> impl Strategy<Value = Vec<String>> {
    prop::collection::vec("[a-z]{3,8}", 0..4).prop_map(|v| {
        // Deduplicate within the same list.
        let mut seen = std::collections::HashSet::new();
        v.into_iter().filter(|s| seen.insert(s.clone())).collect()
    })
}

proptest! {
    #[test]
    fn prop_composed_disallowed_uses_is_superset_of_both(
        list1 in arb_disallowed_list(),
        list2 in arb_disallowed_list(),
    ) {
        let mut ctx1 = make_ctx("prop-dis-1", vec![]);
        ctx1.disallowed_uses = list1.clone();
        let mut ctx2 = make_ctx("prop-dis-2", vec![]);
        ctx2.disallowed_uses = list2.clone();

        let composed = compose(ctx1, ctx2).unwrap();
        let composed_set: std::collections::HashSet<&String> =
            composed.disallowed_uses.iter().collect();

        for u in &list1 {
            prop_assert!(
                composed_set.contains(u),
                "T13: disallowed use '{u}' from input1 must appear in composed context"
            );
        }
        for u in &list2 {
            prop_assert!(
                composed_set.contains(u),
                "T13: disallowed use '{u}' from input2 must appear in composed context"
            );
        }
    }

    #[test]
    fn prop_nonempty_disallowed_always_caps_at_rol(
        use_name in "[a-z]{4,10}",
    ) {
        let mut ctx1 = make_ctx("prop-dis-cap1", vec![]);
        ctx1.disallowed_uses = vec![use_name.clone()];
        let ctx2 = make_ctx("prop-dis-cap2", vec![]);
        let composed = compose(ctx1, ctx2).unwrap();
        let j = compile(composed).unwrap();
        prop_assert!(
            j.permission <= Permission::ROL,
            "T13: non-empty disallowed_uses must always cap at ROL; got {}",
            j.permission
        );
    }
}
