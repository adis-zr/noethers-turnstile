/// EC-003T — Scope containment: intersection is conservative (T14).
///
/// Covers theorems:
///   T14 — Scope containment: composed scope ⊆ every input scope
///   T10 — Composition monotonicity: scope can only narrow
///
/// The scope intersection law:
///   - Empty list means "unconstrained" (all candidates admitted)
///   - Non-empty list means "only these" (intersection filters)
///   - Intersection with empty = the non-empty list (tighter wins)
///   - Intersection with disjoint sets = empty set (no candidates)
///
/// Tests:
///   - Empty ∩ X = X
///   - X ∩ X = X
///   - {a,b} ∩ {b,c} = {b}
///   - {a} ∩ {b} = {} (disjoint — empty intersection)
///   - N-way intersection is monotonically narrowing
///   - All four scope fields (candidates, paths, tools, resources)
///   - Proptest: composed scope ⊆ each input scope
use turnstile_core::context::{Scope, Membership, ProofContext};
use turnstile_core::{compile, compose, expiry::Expiry, permission::Permission};
use proptest::prelude::*;

fn scope_with_tools(tools: Vec<&str>) -> Scope {
    Scope {
        allowed_candidates: vec![],
        allowed_paths: vec![],
        allowed_tools: tools.into_iter().map(String::from).collect(),
        allowed_resources: vec![],
    }
}

fn scope_with_candidates(candidates: Vec<&str>) -> Scope {
    Scope {
        allowed_candidates: candidates.into_iter().map(String::from).collect(),
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    }
}

fn scope_with_paths(paths: Vec<&str>) -> Scope {
    Scope {
        allowed_candidates: vec![],
        allowed_paths: paths.into_iter().map(String::from).collect(),
        allowed_tools: vec![],
        allowed_resources: vec![],
    }
}

fn ctx_with_scope(suffix: &str, scope: Scope) -> ProofContext {
    ProofContext {
        claim_id: "claim-sc".into(),
        candidate_id: "z-sc".into(),
        context_id: format!("ctx-sc-{suffix}"),
        context_fingerprint: format!("fp-sc-{suffix}"),
        allowed_use: "sc-use".into(),
        disallowed_uses: vec![],
        scope,
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── Identity laws ─────────────────────────────────────────────────────────────

#[test]
fn empty_scope_intersect_nonempty_returns_nonempty() {
    let a = scope_with_tools(vec![]);              // unconstrained
    let b = scope_with_tools(vec!["hammer"]);      // constrained
    let result = a.intersect(b);
    assert_eq!(result.allowed_tools, vec!["hammer"]);
}

#[test]
fn nonempty_scope_intersect_empty_returns_nonempty() {
    let a = scope_with_tools(vec!["hammer"]);
    let b = scope_with_tools(vec![]);
    let result = a.intersect(b);
    assert_eq!(result.allowed_tools, vec!["hammer"]);
}

#[test]
fn same_tools_intersect_gives_same() {
    let a = scope_with_tools(vec!["a", "b"]);
    let b = scope_with_tools(vec!["a", "b"]);
    let result = a.intersect(b);
    let mut r = result.allowed_tools;
    r.sort();
    assert_eq!(r, vec!["a", "b"]);
}

// ── Overlap cases ─────────────────────────────────────────────────────────────

#[test]
fn partial_overlap_gives_intersection() {
    let a = scope_with_tools(vec!["a", "b"]);
    let b = scope_with_tools(vec!["b", "c"]);
    let result = a.intersect(b);
    assert_eq!(result.allowed_tools, vec!["b"]);
}

#[test]
fn disjoint_tools_gives_empty_intersection() {
    let a = scope_with_tools(vec!["a"]);
    let b = scope_with_tools(vec!["b"]);
    let result = a.intersect(b);
    assert!(
        result.allowed_tools.is_empty(),
        "disjoint tools must give empty intersection"
    );
}

#[test]
fn disjoint_candidates_gives_empty_intersection() {
    let a = scope_with_candidates(vec!["user-1"]);
    let b = scope_with_candidates(vec!["user-2"]);
    let result = a.intersect(b);
    assert!(result.allowed_candidates.is_empty());
}

// ── Multi-field scope ─────────────────────────────────────────────────────────

#[test]
fn scope_intersection_is_per_field() {
    let a = Scope {
        allowed_candidates: vec!["c1".into()],
        allowed_paths: vec!["/api".into(), "/admin".into()],
        allowed_tools: vec!["read".into(), "write".into()],
        allowed_resources: vec![],
    };
    let b = Scope {
        allowed_candidates: vec!["c1".into(), "c2".into()],
        allowed_paths: vec!["/api".into()],
        allowed_tools: vec!["read".into(), "delete".into()],
        allowed_resources: vec!["r1".into()],
    };
    let r = a.intersect(b);
    assert_eq!(r.allowed_candidates, vec!["c1"]);
    assert_eq!(r.allowed_paths, vec!["/api"]);
    assert_eq!(r.allowed_tools, vec!["read"]);
    // resources: a is empty → b's resources win (unconstrained ∩ constrained = constrained)
    assert_eq!(r.allowed_resources, vec!["r1"]);
}

// ── Composition narrows scope ─────────────────────────────────────────────────

#[test]
fn composed_scope_contained_in_both_inputs() {
    let ctx1 = ctx_with_scope("1", scope_with_tools(vec!["a", "b", "c"]));
    let ctx2 = ctx_with_scope("2", scope_with_tools(vec!["b", "c", "d"]));

    let c1_tools = ctx1.scope.allowed_tools.clone();
    let c2_tools = ctx2.scope.allowed_tools.clone();

    let composed = compose(ctx1, ctx2).unwrap();

    // composed scope ⊆ c1 tools
    for t in &composed.scope.allowed_tools {
        assert!(c1_tools.contains(t), "composed tool {t} not in ctx1 scope");
    }
    // composed scope ⊆ c2 tools
    for t in &composed.scope.allowed_tools {
        assert!(c2_tools.contains(t), "composed tool {t} not in ctx2 scope");
    }
    // expected: {b, c}
    let mut result = composed.scope.allowed_tools.clone();
    result.sort();
    assert_eq!(result, vec!["b", "c"]);
}

#[test]
fn n_way_scope_narrows_monotonically() {
    // Start with a broad scope, compose with progressively narrower ones.
    let scopes = [
        vec!["a", "b", "c", "d"],
        vec!["a", "b", "c"],
        vec!["a", "b"],
        vec!["a"],
    ];
    let mut ctx = ctx_with_scope("narrow-0", scope_with_tools(scopes[0].clone()));

    for (i, tools) in scopes.iter().enumerate().skip(1) {
        let next = ctx_with_scope(&format!("narrow-{i}"), scope_with_tools(tools.clone()));
        ctx = compose(ctx, next).unwrap();
        let tools_len = ctx.scope.allowed_tools.len();
        assert!(
            tools_len <= scopes[i - 1].len(),
            "scope must narrow: expected ≤ {}, got {tools_len}",
            scopes[i - 1].len()
        );
    }

    // Final scope: {a} (only element in all)
    assert_eq!(ctx.scope.allowed_tools, vec!["a"]);
}

#[test]
fn disjoint_composed_scope_produces_empty_intersection() {
    let ctx1 = ctx_with_scope("disj-1", scope_with_paths(vec!["/api"]));
    let ctx2 = ctx_with_scope("disj-2", scope_with_paths(vec!["/admin"]));

    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.scope.allowed_paths.is_empty(),
        "disjoint path scopes must produce empty intersection"
    );
}

// ── Proptest: composed scope is always a subset of each input ─────────────────

fn arb_string_set(size: usize) -> impl Strategy<Value = Vec<String>> {
    prop::collection::vec("[a-z]{1,4}", 0..=size)
        .prop_map(|mut v| {
            v.sort();
            v.dedup();
            v
        })
}

proptest! {
    #[test]
    fn prop_composed_scope_subset_of_inputs(
        tools1 in arb_string_set(6),
        tools2 in arb_string_set(6),
    ) {
        let s1 = Scope { allowed_tools: tools1.clone(), ..Default::default() };
        let s2 = Scope { allowed_tools: tools2.clone(), ..Default::default() };
        let composed = s1.intersect(s2);

        // The composed tools must be a subset of both inputs
        // (or equal to the non-empty one when the other is empty).
        for t in &composed.allowed_tools {
            if !tools1.is_empty() {
                prop_assert!(tools1.contains(t), "composed tool {t} not in tools1={tools1:?}");
            }
            if !tools2.is_empty() {
                prop_assert!(tools2.contains(t), "composed tool {t} not in tools2={tools2:?}");
            }
        }
    }

    #[test]
    fn prop_scope_intersection_commutative(
        tools1 in arb_string_set(6),
        tools2 in arb_string_set(6),
    ) {
        let s1 = Scope { allowed_tools: tools1.clone(), ..Default::default() };
        let s2 = Scope { allowed_tools: tools2.clone(), ..Default::default() };
        let ab = s1.intersect(s2);

        let s1b = Scope { allowed_tools: tools1, ..Default::default() };
        let s2b = Scope { allowed_tools: tools2, ..Default::default() };
        let ba = s2b.intersect(s1b);

        let mut ab_sorted = ab.allowed_tools;
        let mut ba_sorted = ba.allowed_tools;
        ab_sorted.sort();
        ba_sorted.sort();
        prop_assert_eq!(ab_sorted, ba_sorted, "scope intersection must be commutative");
    }

    #[test]
    fn prop_scope_intersection_idempotent(
        tools in arb_string_set(6),
    ) {
        let s1 = Scope { allowed_tools: tools.clone(), ..Default::default() };
        let s2 = Scope { allowed_tools: tools.clone(), ..Default::default() };
        let result = s1.intersect(s2);
        let mut r = result.allowed_tools;
        r.sort();
        let mut expected = tools;
        expected.sort();
        prop_assert_eq!(r, expected, "scope intersection with self must be identity");
    }

    #[test]
    fn prop_scope_narrows_under_composition(
        tools1 in arb_string_set(6),
        tools2 in arb_string_set(6),
    ) {
        // The intersection must be ≤ min(len1, len2) when both non-empty.
        let result = Scope {
            allowed_tools: tools1.clone(), ..Default::default()
        }.intersect(Scope { allowed_tools: tools2.clone(), ..Default::default() });

        if !tools1.is_empty() && !tools2.is_empty() {
            prop_assert!(
                result.allowed_tools.len() <= tools1.len(),
                "intersection larger than input1"
            );
            prop_assert!(
                result.allowed_tools.len() <= tools2.len(),
                "intersection larger than input2"
            );
        }
    }
}
