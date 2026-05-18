/// EC-031 — Adversarial families A1–A10 (EC-001 §34).
///
/// EC-001 §34 defines ten adversarial laundering paths that the compiler must
/// refuse, downgrade, expire, or escalate correctly.  These tests pre-register
/// expected outcomes before constructing the inputs (call-the-shots discipline).
///
/// Each test names:
///   - The adversarial family (A1–A10)
///   - What the attacker attempts
///   - Why the compiler must block it
///   - The expected outcome
///
///   A1  — Fake-token promotion: OOC membership + tokens → must remain OOC
///   A2  — Diagnostic promoted into action: DIA ceiling + action profile → DIA at best
///   A3  — Stale context laundering: wrong runtime fingerprint → OOC (not EXP)
///   A4  — Provenance mismatch: mismatched hash → gap stays Open → OOC
///   A5  — Parent-scope laundering: composed scope narrows, child outside scope
///   A6  — Proxy-to-objective laundering: bounded gap satisfies only bounded req
///   A7  — Coupling omission: missing required gap → unsatisfied profile
///   A8  — Negative-control ritualization: NC token stale → REF in strict mode
///   A9  — Authority-gap laundering: authority ceiling always caps outcome
///   A10 — Domain-certifier overreach: audit derivation is not authority
use chrono::{Duration, Utc};
use turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
    NegativeControlStatus,
};

fn base_ctx(id: &str, use_: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{id}"),
        candidate_id: format!("z-{id}"),
        context_id: format!("ctx-{id}"),
        context_fingerprint: format!("fp-{id}"),
        allowed_use: use_.into(),
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

fn valid_token(id: &str, closes: Vec<String>, ctx: &ProofContext) -> ProofToken {
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
        closes_gaps: closes,
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── A1: Fake-token promotion ──────────────────────────────────────────────────
// Attacker: attach valid-looking tokens to an OOC system.
// Expected: OOC (membership check has priority, T1).

#[test]
fn a1_fake_token_cannot_promote_ooc_system() {
    let mut ctx = base_ctx("a1", "use");
    ctx.membership = Membership::OutOfClassExact;
    ctx.gaps.push(GapRecord::closed("g1", "calibration_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::AAA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-a1", vec!["g1".into()], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A1: OOC membership must absorb any token-based promotion"
    );
}

#[test]
fn a1_all_ooc_variants_block_even_with_full_evidence() {
    for membership in [
        Membership::OutOfClassExact,
        Membership::OutOfClassAuthorizedDeterministicWrite,
        Membership::OutOfClassNoConsequentialUse,
        Membership::OutOfClassOther("adversarial".into()),
    ] {
        let mut ctx = base_ctx("a1v", "use");
        ctx.membership = membership.clone();
        ctx.gaps.push(GapRecord::closed("g1", "t"));
        ctx.profiles.push(Profile {
            permission: Permission::AEX,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = valid_token("tok", vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);

        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission,
            Permission::OOC,
            "A1: membership {:?} must produce OOC",
            membership
        );
    }
}

// ── A2: Diagnostic promoted into action ──────────────────────────────────────
// Attacker: set authority_ceiling = DIA, then supply profile for AEX.
// Expected: DIA (authority ceiling clamps, T11).

#[test]
fn a2_diagnostic_ceiling_blocks_action_profile() {
    let mut ctx = base_ctx("a2", "use");
    ctx.authority_ceiling = Permission::DIA;
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-a2", vec!["g1".into()], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "A2: authority ceiling DIA must block AEX profile"
    );
    assert!(
        j.permission < Permission::AEX,
        "A2: result must be below AEX"
    );
}

#[test]
fn a2_composition_of_dia_and_action_stays_dia() {
    let mut ctx1 = base_ctx("a2c1", "use");
    ctx1.authority_ceiling = Permission::DIA;
    ctx1.gaps.push(GapRecord::closed("g1", "t"));
    ctx1.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok1 = valid_token("tok-c1", vec!["g1".into()], &ctx1);
    ctx1.tokens.push(tok1);

    let mut ctx2 = base_ctx("a2c2", "use");
    ctx2.gaps.push(GapRecord::closed("g1", "t"));
    ctx2.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok2 = valid_token("tok-c2", vec!["g1".into()], &ctx2);
    ctx2.tokens.push(tok2);

    let composed = compose(ctx1, ctx2).unwrap();
    let j = compile(composed).unwrap();
    assert!(
        j.permission <= Permission::DIA,
        "A2: composed DIA+AEX contexts must not produce action permission"
    );
}

// ── A3: Stale context laundering ─────────────────────────────────────────────
// Attacker: submit expired context with valid fresh tokens.
// Expected: EXP (context expiry fires before profile satisfaction).

#[test]
fn a3_expired_context_blocks_despite_valid_tokens() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("a3", "use");
    ctx.expiry = Expiry::at(past);
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-a3", vec!["g1".into()], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "A3: already-fired context expiry must produce EXP"
    );
}

#[test]
fn a3_stale_runtime_fingerprint_blocks_via_live_judgment() {
    let mut ctx = base_ctx("a3rt", "use");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-a3rt", vec!["g1".into()], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "compiled without expiry should be DIA"
    );

    // Runtime fingerprint mismatch simulates stale/wrong context.
    let rt = RuntimeContext::new(Utc::now(), "fp-different");
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::OOC,
        "A3: stale fingerprint at runtime must produce OOC (wrong context, not expiry)"
    );
}

// ── A4: Provenance mismatch ───────────────────────────────────────────────────
// Attacker: present a token with wrong provenance hash.
// Expected: gap stays Open → OOC (T3).

#[test]
fn a4_wrong_provenance_hash_leaves_gap_open() {
    let mut ctx = base_ctx("a4", "diagnostics");
    ctx.gaps.push(GapRecord::open("g1", "truth_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // Token for a different candidate
    let wrong_hash = compute_provenance_hash("claim-a4", "z-ATTACKER", "ctx-a4", "diagnostics");
    ctx.tokens.push(ProofToken {
        token_id: "tok-a4".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: wrong_hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "A4: provenance mismatch must not close gap; PROVENANCE_MISMATCH → REF (InClass)"
    );
}

#[test]
fn a4_recycled_token_from_different_claim_rejected() {
    // Token was issued for claim-X but is presented in claim-Y context.
    let hash_for_x = compute_provenance_hash("claim-X", "z-1", "ctx-1", "use");
    let mut ctx = base_ctx("a4r", "use");
    ctx.gaps.push(GapRecord::open("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // ctx has claim_id "claim-a4r" but token says "claim-X"
    ctx.tokens.push(ProofToken {
        token_id: "tok-recycled".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash_for_x, // wrong claim in hash
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "A4: recycled token from different claim must be rejected; PROVENANCE_MISMATCH → REF (InClass)"
    );
}

// ── A5: Parent-scope laundering ───────────────────────────────────────────────
// Attacker: compose two contexts; hope composed scope is wider than intersection.
// Expected: composed scope ⊆ each input scope (T14).

#[test]
fn a5_composed_scope_is_never_wider_than_inputs() {
    let mut ctx1 = base_ctx("a5a", "use");
    ctx1.scope = Scope {
        allowed_candidates: vec!["z-alpha".into(), "z-beta".into()],
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    };

    let mut ctx2 = base_ctx("a5b", "use");
    ctx2.scope = Scope {
        allowed_candidates: vec!["z-beta".into(), "z-gamma".into()],
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    };

    let composed = compose(ctx1.clone(), ctx2.clone()).unwrap();

    // z-alpha was in ctx1 but not ctx2; z-gamma was in ctx2 but not ctx1
    assert!(
        !composed
            .scope
            .allowed_candidates
            .contains(&"z-alpha".to_string()),
        "A5: z-alpha must not be in composed scope (not in ctx2)"
    );
    assert!(
        !composed
            .scope
            .allowed_candidates
            .contains(&"z-gamma".to_string()),
        "A5: z-gamma must not be in composed scope (not in ctx1)"
    );
    // z-beta is in both
    assert!(
        composed
            .scope
            .allowed_candidates
            .contains(&"z-beta".to_string()),
        "A5: z-beta must be in composed scope (in both)"
    );

    // Scope is always a subset of each input scope
    for c in &composed.scope.allowed_candidates {
        assert!(
            ctx1.scope.allowed_candidates.contains(c),
            "A5: every composed candidate must be in ctx1 scope"
        );
        assert!(
            ctx2.scope.allowed_candidates.contains(c),
            "A5: every composed candidate must be in ctx2 scope"
        );
    }
}

#[test]
fn a5_empty_scope_intersection_produces_empty_scope() {
    let mut ctx1 = base_ctx("a5e1", "use");
    ctx1.scope = Scope {
        allowed_candidates: vec!["z-only-in-1".into()],
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    };

    let mut ctx2 = base_ctx("a5e2", "use");
    ctx2.scope = Scope {
        allowed_candidates: vec!["z-only-in-2".into()],
        allowed_paths: vec![],
        allowed_tools: vec![],
        allowed_resources: vec![],
    };

    let composed = compose(ctx1, ctx2).unwrap();
    assert!(
        composed.scope.allowed_candidates.is_empty(),
        "A5: disjoint candidate scopes must compose to empty scope"
    );
}

// ── A6: Proxy-to-objective laundering ────────────────────────────────────────
// Attacker: provide a bounding token but the profile requires CLOSED.
// Expected: profile not satisfied → OOC.

#[test]
fn a6_bounding_token_does_not_satisfy_closed_required() {
    let mut ctx = base_ctx("a6", "use");
    ctx.gaps.push(GapRecord::open("g1", "proxy_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired, // must be CLOSED
        }],
    });

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    // Token that only BOUNDS the gap, does not close it
    ctx.tokens.push(ProofToken {
        token_id: "tok-bound".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],            // does not close
        bounds_gaps: vec!["g1".into()], // only bounds
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
        Permission::UNS,
        "A6: bounding token cannot satisfy ClosedRequired profile; InClass unmet profile → UNS"
    );
}

#[test]
fn a6_bounding_token_satisfies_bounded_required() {
    // Same setup but profile only needs BOUNDED → should succeed.
    let mut ctx = base_ctx("a6b", "use");
    ctx.gaps
        .push(GapRecord::bounded("g1", "proxy_gap", Bound::numeric(0.05)));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    });

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ctx.tokens.push(ProofToken {
        token_id: "tok-bound-ok".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec!["g1".into()],
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
        "A6: bounding token satisfies BoundedRequired profile"
    );
}

// ── A7: Coupling omission ─────────────────────────────────────────────────────
// Attacker: close all gaps except a required coupling gap.
// Expected: profile unsatisfied → OOC (T6).

#[test]
fn a7_missing_required_coupling_gap_blocks_permission() {
    let mut ctx = base_ctx("a7", "use");
    ctx.gaps
        .push(GapRecord::closed("g-calibration", "calibration_gap"));
    ctx.gaps.push(GapRecord::open("g-coupling", "coupling_gap")); // required but open
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-calibration".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-coupling".into(),
                minimum_status: RequiredStatus::ClosedRequired, // attacker forgot this
            },
        ],
    });
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    // Token that closes calibration but not coupling
    ctx.tokens.push(ProofToken {
        token_id: "tok-a7".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g-calibration".into()],
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
        Permission::UNS,
        "A7: open required coupling gap must block permission; InClass unmet profile → UNS"
    );
}

// ── A8: Negative-control ritualization ───────────────────────────────────────
// Attacker: attach NC token but it's stale at runtime.
// Expected: REF in strict mode (T17).

#[test]
fn a8_stale_nc_token_floors_to_ref_in_strict_mode() {
    let mut ctx = base_ctx("a8", "use");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
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
    let nc_tok = ProofToken {
        token_id: "nc-tok-a8".into(),
        token_type: "NEGATIVE_CONTROL".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    };
    ctx.tokens.push(nc_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "compiles to DIA before runtime check"
    );

    // Strict mode: NC token is stale in runtime
    let mut nc_states = std::collections::HashMap::new();
    nc_states.insert("nc-tok-a8".to_string(), NegativeControlStatus::Stale);
    let rt = RuntimeContext::with_nc_states(Utc::now(), "fp-a8", nc_states, true);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::REF,
        "A8: stale NC token in strict mode must floor to REF"
    );
}

#[test]
fn a8_missing_nc_token_floors_to_ref_in_strict_mode() {
    let mut ctx = base_ctx("a8m", "use");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
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
        token_id: "nc-tok-a8m".into(),
        token_type: "NC".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    });

    let j = compile(ctx).unwrap();
    // Empty NC states map → NC token is "missing" in strict mode
    let rt = RuntimeContext::new(Utc::now(), "fp-a8m");
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::REF,
        "A8: missing NC token must floor to REF in strict mode"
    );
}

#[test]
fn a8_nc_token_passes_when_live_in_strict_mode() {
    let mut ctx = base_ctx("a8p", "use");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
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
        token_id: "nc-tok-a8p".into(),
        token_type: "NC".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    });

    let j = compile(ctx).unwrap();
    let mut nc_states = std::collections::HashMap::new();
    nc_states.insert("nc-tok-a8p".to_string(), NegativeControlStatus::Live);
    let rt = RuntimeContext::with_nc_states(Utc::now(), "fp-a8p", nc_states, true);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "A8: live NC token in strict mode must pass"
    );
}

// ── A9: Authority-gap laundering ─────────────────────────────────────────────
// Attacker: hope authority_ceiling is not enforced after composition.
// Expected: authority ceiling is always the meet (T10).

#[test]
fn a9_authority_ceiling_always_caps_after_composition() {
    // ctx1 has ceiling DIA
    let mut ctx1 = base_ctx("a9a", "use");
    ctx1.authority_ceiling = Permission::DIA;
    ctx1.gaps.push(GapRecord::closed("g1", "t"));
    ctx1.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok1 = valid_token("tok-a9a", vec!["g1".into()], &ctx1);
    ctx1.tokens.push(tok1);

    // ctx2 has ceiling AAA (no ceiling) but tries to unlock AEX
    let mut ctx2 = base_ctx("a9b", "use");
    ctx2.authority_ceiling = Permission::AAA;
    ctx2.gaps.push(GapRecord::closed("g2", "t"));
    ctx2.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![GapRequirement {
            gap_id: "g2".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok2 = valid_token("tok-a9b", vec!["g2".into()], &ctx2);
    ctx2.tokens.push(tok2);

    let composed = compose(ctx1, ctx2).unwrap();
    // Composed authority ceiling must be meet(DIA, AAA) = DIA
    assert_eq!(
        composed.authority_ceiling,
        Permission::DIA,
        "A9: composed ceiling is meet of inputs"
    );

    let j = compile(composed).unwrap();
    assert!(
        j.permission <= Permission::DIA,
        "A9: outcome must be ≤ DIA after composition"
    );
    assert!(
        j.permission < Permission::AEX,
        "A9: AEX must be blocked by DIA ceiling"
    );
}

#[test]
fn a9_n_contexts_ceiling_is_meet_of_all() {
    let ceilings = [
        Permission::AEX,
        Permission::DIA,
        Permission::AAA,
        Permission::ROL,
    ];
    let expected_meet = ceilings.iter().copied().min().unwrap();

    let contexts: Vec<ProofContext> = ceilings
        .iter()
        .enumerate()
        .map(|(i, &ceiling)| {
            let mut ctx = base_ctx(&format!("a9n-{i}"), "use");
            ctx.authority_ceiling = ceiling;
            ctx
        })
        .collect();

    let composed = turnstile_core::compose_n(contexts).unwrap();
    assert_eq!(
        composed.authority_ceiling, expected_meet,
        "A9: N-ary composed authority ceiling is meet of all inputs"
    );
}

// ── A10: Domain-certifier overreach ──────────────────────────────────────────
// Attacker: manipulate derivation/audit trail to claim a higher permission.
// Expected: derivation is read-only explanation; it does not grant authority (T18).

#[test]
fn a10_audit_derivation_does_not_grant_authority() {
    // Context with no profile that would satisfy AEX
    let mut ctx = base_ctx("a10", "use");
    ctx.gaps.push(GapRecord::open("g1", "truth_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired, // will not be met
        }],
    });
    // No tokens — gap stays open

    let j = compile(ctx).unwrap();
    // Derivation says DIA profile was not satisfied; InClass candidate with unmet profile → UNS.
    assert_eq!(
        j.permission,
        Permission::UNS,
        "A10: no satisfied profile on InClass candidate means UNS"
    );

    // The derivation steps never fabricate a higher permission
    for step in &j.derivation.steps {
        assert!(
            step.permission_after <= j.permission || step.phase == "descending_search",
            "A10: derivation step permission_after must not exceed final permission (except descending search)"
        );
    }
}

#[test]
fn a10_judgment_permission_equals_last_derivation_step() {
    let mut ctx = base_ctx("a10f", "use");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-a10f", vec!["g1".into()], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    // The last derivation step must agree with the emitted permission
    if let Some(last) = j.derivation.steps.last() {
        assert_eq!(
            last.permission_after, j.permission,
            "A10: last derivation step must match emitted permission"
        );
    }
}
