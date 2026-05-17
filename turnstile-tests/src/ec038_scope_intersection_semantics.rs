/// EC-038 — Scope intersection semantics (EC-001 §22, T14).
///
/// EC-001 §22 states that scope is a domain-supplied set under intersection.
/// Scope intersection must:
///   - Never widen (T14)
///   - Be computed for all four scope fields (candidates, paths, tools, resources)
///   - Preserve the empty-list = unconstrained (top) semantics
///   - Under N-ary composition, be the intersection of all inputs
///
///   SI1  — Unconstrained (empty list) intersected with constraint = constraint
///   SI2  — Two overlapping constraints → intersection (shared elements only)
///   SI3  — Two disjoint constraints → empty intersection
///   SI4  — Empty list ∩ empty list = empty list (unconstrained ∩ unconstrained)
///   SI5  — N-ary composition: scope is intersection of all inputs
///   SI6  — Scope intersection is commutative (A ∩ B = B ∩ A)
///   SI7  — Scope intersection is associative ((A∩B)∩C = A∩(B∩C))
///   SI8  — All four scope fields (candidates, paths, tools, resources) intersect
///   SI9  — Composed scope never contains an element not in all inputs (T14)
///   SI10 — compose() preserves unconstrained paths when one ctx has no path constraint
use turnstile_core::{
    compose, compose_n,
    context::{ProofContext, Scope, Membership},
    expiry::Expiry,
    permission::Permission,
};

fn ctx_with_scope(id: &str, scope: Scope) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{id}"),
        candidate_id: format!("z-{id}"),
        context_id: format!("ctx-{id}"),
        context_fingerprint: format!("fp-{id}"),
        allowed_use: "scope-test".into(),
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

fn scope_candidates(candidates: Vec<&str>) -> Scope {
    Scope {
        allowed_candidates: candidates.into_iter().map(String::from).collect(),
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    }
}

// ── SI1: Unconstrained ∩ constrained = constrained ───────────────────────────

#[test]
fn si1_unconstrained_intersect_constrained_is_constrained() {
    let ctx1 = ctx_with_scope("si1a", Scope::default()); // unconstrained (empty list)
    let ctx2 = ctx_with_scope(
        "si1b",
        scope_candidates(vec!["z-1", "z-2"]),
    );

    let composed = compose(ctx1, ctx2.clone()).unwrap();
    // Intersection of top with {z-1, z-2} = {z-1, z-2}
    assert_eq!(
        composed.scope.allowed_candidates,
        ctx2.scope.allowed_candidates,
        "SI1: unconstrained ∩ constrained must equal the constrained set"
    );
}

#[test]
fn si1_constrained_intersect_unconstrained_is_constrained() {
    let ctx1 = ctx_with_scope("si1c", scope_candidates(vec!["z-alpha", "z-beta"]));
    let ctx2 = ctx_with_scope("si1d", Scope::default());

    let composed = compose(ctx1.clone(), ctx2).unwrap();
    assert_eq!(
        composed.scope.allowed_candidates,
        ctx1.scope.allowed_candidates,
        "SI1: constrained ∩ unconstrained must equal the constrained set"
    );
}

// ── SI2: Overlapping constraints → intersection ───────────────────────────────

#[test]
fn si2_overlapping_constraints_produce_intersection() {
    let ctx1 = ctx_with_scope("si2a", scope_candidates(vec!["z-1", "z-2", "z-3"]));
    let ctx2 = ctx_with_scope("si2b", scope_candidates(vec!["z-2", "z-3", "z-4"]));

    let composed = compose(ctx1, ctx2).unwrap();
    let mut result = composed.scope.allowed_candidates.clone();
    result.sort();

    assert!(result.contains(&"z-2".to_string()), "SI2: z-2 is in both, must be in intersection");
    assert!(result.contains(&"z-3".to_string()), "SI2: z-3 is in both, must be in intersection");
    assert!(!result.contains(&"z-1".to_string()), "SI2: z-1 is only in ctx1, must not be in intersection");
    assert!(!result.contains(&"z-4".to_string()), "SI2: z-4 is only in ctx2, must not be in intersection");
    assert_eq!(result.len(), 2, "SI2: intersection must have exactly 2 elements");
}

// ── SI3: Disjoint constraints → empty intersection ───────────────────────────

#[test]
fn si3_disjoint_constraints_produce_empty_scope() {
    let ctx1 = ctx_with_scope("si3a", scope_candidates(vec!["z-only-in-1"]));
    let ctx2 = ctx_with_scope("si3b", scope_candidates(vec!["z-only-in-2"]));

    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.scope.allowed_candidates.is_empty(),
        "SI3: disjoint candidate scopes must produce empty scope"
    );
}

// ── SI4: Unconstrained ∩ unconstrained = unconstrained ───────────────────────

#[test]
fn si4_unconstrained_intersect_unconstrained_is_unconstrained() {
    let ctx1 = ctx_with_scope("si4a", Scope::default());
    let ctx2 = ctx_with_scope("si4b", Scope::default());

    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.scope.allowed_candidates.is_empty(),
        "SI4: unconstrained ∩ unconstrained must be unconstrained (empty list)"
    );
}

// ── SI5: N-ary composition: scope is intersection of all inputs ───────────────

#[test]
fn si5_nary_composition_scope_is_intersection() {
    let ctx1 = ctx_with_scope("si5a", scope_candidates(vec!["z-1", "z-2", "z-3"]));
    let ctx2 = ctx_with_scope("si5b", scope_candidates(vec!["z-2", "z-3", "z-4"]));
    let ctx3 = ctx_with_scope("si5c", scope_candidates(vec!["z-3", "z-4", "z-5"]));

    let composed = compose_n(vec![ctx1, ctx2, ctx3]).unwrap();
    // Intersection: {z-1,z-2,z-3} ∩ {z-2,z-3,z-4} ∩ {z-3,z-4,z-5} = {z-3}
    assert_eq!(
        composed.scope.allowed_candidates,
        vec!["z-3".to_string()],
        "SI5: N-ary intersection of three overlapping sets must be [z-3]"
    );
}

// ── SI6: Scope intersection is commutative ────────────────────────────────────

#[test]
fn si6_scope_intersection_is_commutative() {
    let ctx1 = ctx_with_scope("si6a", scope_candidates(vec!["z-1", "z-2", "z-3"]));
    let ctx2 = ctx_with_scope("si6b", scope_candidates(vec!["z-2", "z-3", "z-4"]));

    let fwd = compose(ctx1.clone(), ctx2.clone()).unwrap();
    let rev = compose(ctx2, ctx1).unwrap();

    let mut fwd_cands = fwd.scope.allowed_candidates.clone();
    let mut rev_cands = rev.scope.allowed_candidates.clone();
    fwd_cands.sort();
    rev_cands.sort();

    assert_eq!(fwd_cands, rev_cands, "SI6: scope intersection must be commutative");
}

// ── SI7: Scope intersection is associative ────────────────────────────────────

#[test]
fn si7_scope_intersection_is_associative() {
    let ctx1 = ctx_with_scope("si7a", scope_candidates(vec!["z-1", "z-2", "z-3"]));
    let ctx2 = ctx_with_scope("si7b", scope_candidates(vec!["z-2", "z-3", "z-4"]));
    let ctx3 = ctx_with_scope("si7c", scope_candidates(vec!["z-3", "z-4", "z-5"]));

    // (ctx1 ∩ ctx2) ∩ ctx3
    let lhs = {
        let inner = compose(ctx1.clone(), ctx2.clone()).unwrap();
        compose(inner, ctx3.clone()).unwrap()
    };
    // ctx1 ∩ (ctx2 ∩ ctx3)
    let rhs = {
        let inner = compose(ctx2.clone(), ctx3.clone()).unwrap();
        compose(ctx1.clone(), inner).unwrap()
    };

    let mut lhs_cands = lhs.scope.allowed_candidates.clone();
    let mut rhs_cands = rhs.scope.allowed_candidates.clone();
    lhs_cands.sort();
    rhs_cands.sort();

    assert_eq!(lhs_cands, rhs_cands, "SI7: scope intersection must be associative");
}

// ── SI8: All four scope fields intersect independently ────────────────────────

#[test]
fn si8_all_four_scope_fields_intersect() {
    let ctx1 = ctx_with_scope("si8a", Scope {
        allowed_candidates: vec!["z-1".into(), "z-2".into()],
        allowed_paths: vec!["/api/v1".into(), "/api/v2".into()],
        allowed_tools: vec!["tool-a".into(), "tool-b".into()],
        allowed_resources: vec!["db-read".into(), "cache-read".into()],
    });

    let ctx2 = ctx_with_scope("si8b", Scope {
        allowed_candidates: vec!["z-2".into(), "z-3".into()],
        allowed_paths: vec!["/api/v2".into(), "/api/v3".into()],
        allowed_tools: vec!["tool-b".into(), "tool-c".into()],
        allowed_resources: vec!["cache-read".into(), "queue-read".into()],
    });

    let composed = compose(ctx1, ctx2).unwrap();

    assert_eq!(composed.scope.allowed_candidates, vec!["z-2".to_string()], "SI8: candidates");
    assert_eq!(composed.scope.allowed_paths, vec!["/api/v2".to_string()], "SI8: paths");
    assert_eq!(composed.scope.allowed_tools, vec!["tool-b".to_string()], "SI8: tools");
    assert_eq!(composed.scope.allowed_resources, vec!["cache-read".to_string()], "SI8: resources");
}

// ── SI9: T14 — composed scope never contains element not in all inputs ────────

#[test]
fn si9_t14_composed_scope_subset_of_each_input() {
    let ctx1 = ctx_with_scope("si9a", scope_candidates(vec!["z-1", "z-2", "z-3"]));
    let ctx2 = ctx_with_scope("si9b", scope_candidates(vec!["z-2", "z-3", "z-4"]));

    let composed = compose(ctx1.clone(), ctx2.clone()).unwrap();

    for c in &composed.scope.allowed_candidates {
        assert!(
            ctx1.scope.allowed_candidates.contains(c),
            "SI9/T14: composed candidate {c} must be in ctx1's scope"
        );
        assert!(
            ctx2.scope.allowed_candidates.contains(c),
            "SI9/T14: composed candidate {c} must be in ctx2's scope"
        );
    }
}

// ── SI10: Unconstrained paths preserved when one ctx has no path constraint ───

#[test]
fn si10_unconstrained_paths_preserved() {
    let ctx1 = ctx_with_scope("si10a", Scope {
        allowed_candidates: vec![],
        allowed_paths: vec!["/api/v1".into()],
        allowed_tools: vec![],
        allowed_resources: vec![],
    });
    let ctx2 = ctx_with_scope("si10b", Scope::default()); // no path constraint

    let composed = compose(ctx1.clone(), ctx2).unwrap();
    // /api/v1 is in ctx1; ctx2 is unconstrained (top) for paths
    // intersection: top ∩ {/api/v1} = {/api/v1}
    assert_eq!(
        composed.scope.allowed_paths,
        ctx1.scope.allowed_paths,
        "SI10: constrained path scope ∩ unconstrained = constrained"
    );
}

// ── Monotone narrowing: scope can only stay same or narrow under composition ──

#[test]
fn scope_is_monotone_narrowing_under_composition() {
    let ctx1 = ctx_with_scope("mono1", scope_candidates(vec!["z-1", "z-2", "z-3", "z-4"]));
    let ctx2 = ctx_with_scope("mono2", scope_candidates(vec!["z-2", "z-3"]));

    let composed = compose(ctx1.clone(), ctx2.clone()).unwrap();

    // composed scope must be a subset of ctx1's scope
    for c in &composed.scope.allowed_candidates {
        assert!(ctx1.scope.allowed_candidates.contains(c));
    }
    // composed scope length ≤ min of inputs
    assert!(
        composed.scope.allowed_candidates.len() <= ctx1.scope.allowed_candidates.len(),
        "Composed scope must not be wider than ctx1"
    );
    assert!(
        composed.scope.allowed_candidates.len() <= ctx2.scope.allowed_candidates.len(),
        "Composed scope must not be wider than ctx2"
    );
}
