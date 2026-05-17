/// EC-035 — Multi-profile descending search and strongest-admissible selection.
///
/// EC-001 §30 requires the compiler to emit the *strongest admissible* outcome
/// under the available evidence.  The descending search iterates from AAA to OOC
/// and returns the first satisfied profile.  This suite verifies that the search:
///
///   S1  — Returns the strongest satisfied profile, not just any profile
///   S2  — Skips unsatisfied profiles and continues descending
///   S3  — Falls through to OOC when no profile is satisfied
///   S4  — With two profiles (DIA+AEX), evidence for AEX compiles to AEX
///   S5  — With two profiles (DIA+AEX), evidence for DIA only compiles to DIA
///   S6  — Adding evidence can only raise permission (monotonicity, T evid-mono)
///   S7  — Profile order in context does not affect outcome (determinism)
///   S8  — Profile for the lowest permission (OOC) is never emitted via profile
///   S9  — Gap requirement: BOUNDED_REQUIRED satisfied by Closed but not Open
///   S10 — A profile with no required gaps is always satisfied (empty conjunction)
///   S11 — Two profiles for same permission level are a MalformedContext error
///   S12 — All 12 permission levels can be targeted via profiles
use chrono::Utc;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(id: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{id}"),
        candidate_id: format!("z-{id}"),
        context_id: format!("ctx-{id}"),
        context_fingerprint: format!("fp-{id}"),
        allowed_use: "test-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn closing_token(id: &str, closes: Vec<&str>, ctx: &ProofContext) -> ProofToken {
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

// ── S1: Strongest satisfied profile wins ─────────────────────────────────────

#[test]
fn s1_strongest_satisfied_profile_wins() {
    let mut ctx = base_ctx("s1");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.gaps.push(GapRecord::closed("g2", "t"));

    // DIA requires only g1; AEX requires g1+g2
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g2".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    });

    let tok = closing_token("tok-s1", vec!["g1", "g2"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::AEX,
        "S1: must select AEX (strongest satisfied)"
    );
}

// ── S2: Skips unsatisfied profiles and continues ──────────────────────────────

#[test]
fn s2_skips_unsatisfied_profiles() {
    let mut ctx = base_ctx("s2");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.gaps.push(GapRecord::open("g2", "t")); // g2 is open

    // AEX needs g2 (open → not satisfied)
    ctx.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g2".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    });
    // DIA only needs g1
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });

    let tok = closing_token("tok-s2", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "S2: must skip AEX and select DIA"
    );
    assert!(j.permission < Permission::AEX, "S2: AEX must be skipped");
}

// ── S3: Falls through to OOC when nothing is satisfied ───────────────────────

#[test]
fn s3_no_satisfied_profile_produces_ooc() {
    let mut ctx = base_ctx("s3");
    ctx.gaps.push(GapRecord::open("g1", "t")); // open — nothing satisfied
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // No tokens → gap stays open → profile not satisfied

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "S3: no satisfied profile must produce OOC"
    );
}

// ── S4: With DIA+AEX profiles, full evidence compiles to AEX ─────────────────

#[test]
fn s4_full_evidence_for_aex_compiles_to_aex() {
    let mut ctx = base_ctx("s4");
    ctx.gaps.push(GapRecord::closed("g-dia", "t"));
    ctx.gaps.push(GapRecord::closed("g-aex", "t"));

    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g-dia".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-dia".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-aex".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    });

    let tok = closing_token("tok-s4", vec!["g-dia", "g-aex"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::AEX,
        "S4: full evidence must reach AEX"
    );
}

// ── S5: Partial evidence compiles to DIA only ────────────────────────────────

#[test]
fn s5_dia_evidence_only_compiles_to_dia() {
    let mut ctx = base_ctx("s5");
    ctx.gaps.push(GapRecord::closed("g-dia", "t"));
    ctx.gaps.push(GapRecord::open("g-aex", "t")); // not provided

    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g-dia".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-dia".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-aex".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    });

    let tok = closing_token("tok-s5", vec!["g-dia"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "S5: partial evidence must compile to DIA, not AEX"
    );
}

// ── S6: Adding evidence can only raise or maintain permission ─────────────────
// (Evidence monotonicity — adding a valid token never lowers permission)

#[test]
fn s6_adding_evidence_never_lowers_permission() {
    let mut ctx_no_tok = base_ctx("s6");
    ctx_no_tok.gaps.push(GapRecord::closed("g1", "t"));
    ctx_no_tok.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // No token
    let p_before = compile(ctx_no_tok.clone()).unwrap().permission;

    // Now add a valid token
    let tok = closing_token("tok-s6", vec!["g1"], &ctx_no_tok);
    let mut ctx_with_tok = ctx_no_tok;
    ctx_with_tok.tokens.push(tok);
    let p_after = compile(ctx_with_tok).unwrap().permission;

    assert!(
        p_after >= p_before,
        "S6: adding a valid token must not lower permission ({p_before} → {p_after})"
    );
}

// ── S7: Profile order in context does not affect outcome ──────────────────────

#[test]
fn s7_profile_order_is_irrelevant_to_outcome() {
    fn make_ctx_with_profile_order(id: &str, dia_first: bool) -> ProofContext {
        let mut ctx = base_ctx(id);
        ctx.gaps.push(GapRecord::closed("g1", "t"));
        ctx.gaps.push(GapRecord::open("g2", "t"));

        let dia_profile = Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        };
        let aex_profile = Profile {
            permission: Permission::AEX,
            required_gaps: vec![
                GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
                GapRequirement {
                    gap_id: "g2".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
            ],
        };

        if dia_first {
            ctx.profiles.push(dia_profile);
            ctx.profiles.push(aex_profile);
        } else {
            ctx.profiles.push(aex_profile);
            ctx.profiles.push(dia_profile);
        }

        let tok = closing_token("tok-s7", vec!["g1"], &ctx);
        ctx.tokens.push(tok);
        ctx
    }

    let ctx_a = make_ctx_with_profile_order("s7a", true);
    let ctx_b = make_ctx_with_profile_order("s7b", false);

    let j_a = compile(ctx_a).unwrap();
    let j_b = compile(ctx_b).unwrap();

    assert_eq!(
        j_a.permission, j_b.permission,
        "S7: profile order must not affect compiled permission"
    );
    assert_eq!(
        j_a.permission,
        Permission::DIA,
        "S7: must compile to DIA (g2 open)"
    );
}

// ── S8: OOC cannot be targeted via a profile ──────────────────────────────────

#[test]
fn s8_profile_for_permission_below_ooc_does_not_exist() {
    // A profile for OOC is meaningless (OOC is only emitted by membership check
    // or as a fallthrough). If someone constructs one, the result is still OOC
    // but only because of the descending search fallthrough.
    let mut ctx = base_ctx("s8");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    // No profiles → descending search finds nothing → OOC
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "S8: no profiles → OOC fallthrough"
    );
}

// ── S9: BOUNDED_REQUIRED satisfied by Closed but not Open ────────────────────

#[test]
fn s9_bounded_required_satisfied_by_closed() {
    let mut ctx = base_ctx("s9c");
    ctx.gaps.push(GapRecord::closed("g1", "t")); // Closed > Bounded
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    });
    let tok = closing_token("tok-s9c", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "S9: Closed must satisfy BoundedRequired"
    );
}

#[test]
fn s9_bounded_required_not_satisfied_by_open() {
    let mut ctx = base_ctx("s9o");
    ctx.gaps.push(GapRecord::open("g1", "t")); // Open < Bounded
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "S9: Open must not satisfy BoundedRequired"
    );
}

#[test]
fn s9_bounded_required_satisfied_by_bounded_status_with_token() {
    let mut ctx = base_ctx("s9b");
    ctx.gaps
        .push(GapRecord::bounded("g1", "t", Bound::numeric(0.1)));
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
        token_id: "tok-s9b".into(),
        token_type: "BOUND_TOKEN".into(),
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
        "S9: Bounded token must satisfy BoundedRequired"
    );
}

// ── S10: Empty required_gaps profile is always satisfied ─────────────────────

#[test]
fn s10_profile_with_no_required_gaps_is_always_satisfied() {
    let mut ctx = base_ctx("s10");
    // Profile with zero required gaps → trivially satisfied
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![], // empty conjunction = true
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "S10: empty required_gaps profile must be satisfied"
    );
}

// ── S11: Duplicate permission levels are MalformedContext ────────────────────

#[test]
fn s11_duplicate_permission_levels_are_malformed() {
    let mut ctx = base_ctx("s11");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::DIA, // duplicate
        required_gaps: vec![],
    });

    let result = compile(ctx);
    assert!(
        result.is_err(),
        "S11: duplicate permission levels must be MalformedContext"
    );
    let err_msg = format!("{:?}", result.unwrap_err());
    assert!(
        err_msg.contains("duplicate") || err_msg.contains("Malformed"),
        "S11: error must mention duplicate or malformed"
    );
}

// ── S12: All 12 permission levels can be targeted via profiles ────────────────
// (Except OOC which is not profile-driven; here we test EXP through AAA)

#[test]
fn s12_all_non_ooc_permissions_are_reachable_via_profiles() {
    for p in Permission::descending() {
        if p == Permission::OOC {
            continue; // OOC is emitted by membership check or fallthrough, not profile
        }

        let mut ctx = base_ctx(&format!("s12-{p}"));
        ctx.gaps.push(GapRecord::closed("g1", "t"));
        ctx.profiles.push(Profile {
            permission: p,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = closing_token(&format!("tok-{p}"), vec!["g1"], &ctx);
        ctx.tokens.push(tok);

        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission, p,
            "S12: permission {p} must be reachable via profile"
        );
    }
}
