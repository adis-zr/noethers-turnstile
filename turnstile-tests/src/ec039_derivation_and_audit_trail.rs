/// EC-039 — Derivation trail integrity and audit correctness (EC-001 §23, T18).
///
/// EC-001 §23 states that derivation is authoritative while audit is explanatory.
/// The derivation trail must:
///   - Record every decision phase
///   - Be monotone non-increasing in permission_after values
///   - Have the final step match the emitted permission
///   - Contain the correct provenance hash
///   - Be read-only (audit entries cannot alter permission)
///
/// Coverage:
///   D1  — OOC membership: single step "membership_check" with permission OOC
///   D2  — Satisfied profile: "descending_search" step appears after compile
///   D3  — Authority ceiling applied: "authority_ceiling" step appears
///   D4  — Expiry blocker applied: "expiry_blocker" step appears
///   D5  — Structural blocker applied: "structural_blockers" step appears
///   D6  — NC registration: "negative_control_registration" step appears
///   D7  — Derivation steps are non-increasing in permission_after
///   D8  — Final derivation step matches judgment.permission
///   D9  — compiled_at is Some(_) after compilation
///   D10 — Derivation provenance_hash matches context provenance hash
///   D11 — T18: audit record writes do not alter judgment permission
///   D12 — Derivation token_ids are accurate (consulted tokens appear)
use chrono::{Duration, Utc};
use turnstile_core::{
    audit::{AuditEntry, AuditStore, InMemoryAuditStore},
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
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

// ── D1: OOC membership produces single "membership_check" step ───────────────

#[test]
fn d1_ooc_membership_produces_single_step() {
    let mut ctx = base_ctx("d1");
    ctx.membership = Membership::OutOfClassExact;

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
    assert_eq!(
        j.derivation.steps.len(),
        1,
        "D1: OOC must produce exactly one step"
    );
    assert_eq!(
        j.derivation.steps[0].phase, "membership_check",
        "D1: single step must be membership_check"
    );
    assert_eq!(
        j.derivation.steps[0].permission_after,
        Permission::OOC,
        "D1: membership_check step must record OOC"
    );
}

// ── D2: Satisfied profile → descending_search step appears ───────────────────

#[test]
fn d2_satisfied_profile_produces_descending_search_step() {
    let mut ctx = base_ctx("d2");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-d2", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    let phases: Vec<&str> = j
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    assert!(
        phases.contains(&"descending_search"),
        "D2: descending_search phase must appear in derivation"
    );
}

// ── D3: Authority ceiling applied → "authority_ceiling" step appears ──────────

#[test]
fn d3_authority_ceiling_step_appears_when_active() {
    let mut ctx = base_ctx("d3");
    ctx.authority_ceiling = Permission::DIA; // lower than AAA
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::AEX, // would compile to AEX without ceiling
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-d3", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "D3: ceiling must cap at DIA");

    let phases: Vec<&str> = j
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    assert!(
        phases.contains(&"authority_ceiling"),
        "D3: authority_ceiling phase must appear when ceiling is active"
    );
}

// ── D4: Expiry blocker → "expiry_blocker" step appears ───────────────────────

#[test]
fn d4_expiry_blocker_step_appears_when_token_expired() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("d4");
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
        token_id: "tok-d4-expired".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "D4: expired token must floor to EXP"
    );

    let phases: Vec<&str> = j
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    assert!(
        phases.contains(&"expiry_blocker"),
        "D4: expiry_blocker phase must appear when token is expired"
    );
}

// ── D5: Structural blocker → "structural_blockers" step appears ──────────────

#[test]
fn d5_structural_blockers_step_appears_when_disallowed_uses_present() {
    let mut ctx = base_ctx("d5");
    ctx.disallowed_uses = vec!["dangerous-write".into()];
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::AEX, // AEX would be blocked by disallowed_uses
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-d5", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert!(
        j.permission <= Permission::ROL,
        "D5: disallowed_uses must cap at ROL"
    );

    let phases: Vec<&str> = j
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    assert!(
        phases.contains(&"structural_blockers"),
        "D5: structural_blockers phase must appear when disallowed_uses present"
    );
}

// ── D6: NC registration step appears when NC token present ───────────────────

#[test]
fn d6_nc_registration_step_appears_when_nc_token_present() {
    let mut ctx = base_ctx("d6");
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
        token_id: "nc-tok-d6".into(),
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
    let phases: Vec<&str> = j
        .derivation
        .steps
        .iter()
        .map(|s| s.phase.as_str())
        .collect();
    assert!(
        phases.contains(&"negative_control_registration"),
        "D6: negative_control_registration step must appear when NC token present"
    );
}

// ── D7: Derivation steps are non-increasing in permission_after ───────────────

#[test]
fn d7_derivation_steps_are_non_increasing() {
    let mut ctx = base_ctx("d7");
    ctx.authority_ceiling = Permission::DIA;
    ctx.disallowed_uses = vec!["write".into()];
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::AEX,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-d7", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();

    let steps = &j.derivation.steps;
    for window in steps.windows(2) {
        let earlier = window[0].permission_after;
        let later = window[1].permission_after;
        assert!(
            later <= earlier,
            "D7: derivation step permission_after must be non-increasing: {} → {}",
            earlier,
            later
        );
    }
}

// ── D8: Final derivation step matches judgment.permission ─────────────────────

#[test]
fn d8_final_step_matches_emitted_permission() {
    let scenarios: Vec<(ProofContext, Permission)> = {
        let mut scenarios = vec![];

        // OOC scenario
        let mut ctx = base_ctx("d8-ooc");
        ctx.membership = Membership::OutOfClassExact;
        scenarios.push((ctx, Permission::OOC));

        // DIA scenario
        let mut ctx = base_ctx("d8-dia");
        ctx.gaps.push(GapRecord::closed("g1", "t"));
        ctx.profiles.push(Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = valid_token("tok-d8-dia", vec!["g1"], &ctx);
        ctx.tokens.push(tok);
        scenarios.push((ctx, Permission::DIA));

        scenarios
    };

    for (ctx, expected_perm) in scenarios {
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, expected_perm);

        if let Some(last) = j.derivation.steps.last() {
            assert_eq!(
                last.permission_after, j.permission,
                "D8: last derivation step must match emitted permission"
            );
        }
    }
}

// ── D9: compiled_at is Some(_) after compilation ─────────────────────────────

#[test]
fn d9_compiled_at_is_set_after_compilation() {
    let ctx = base_ctx("d9");
    let j = compile(ctx).unwrap();
    assert!(
        j.derivation.compiled_at.is_some(),
        "D9: compiled_at must be set after compilation"
    );
}

// ── D10: Derivation provenance_hash matches context provenance ────────────────

#[test]
fn d10_derivation_provenance_hash_matches_context() {
    let mut ctx = base_ctx("d10");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-d10", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let expected_hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.derivation.provenance_hash, expected_hash,
        "D10: derivation provenance_hash must match context provenance"
    );
}

// ── D11: T18 — audit writes do not alter judgment permission ──────────────────

#[test]
fn d11_t18_audit_record_does_not_alter_permission() {
    let mut ctx = base_ctx("d11");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = valid_token("tok-d11", vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    let permission_before_audit = j.permission;

    // Record audit entries
    let store = InMemoryAuditStore::default();
    let entry = AuditEntry {
        candidate_id: j.context.candidate_id.clone(),
        claim_id: j.context.claim_id.clone(),
        context_id: j.context.context_id.clone(),
        membership: format!("{:?}", j.context.membership),
        permission: j.permission,
        expiry_deadline: j.expiry.deadline,
        token_ids: j
            .context
            .tokens
            .iter()
            .map(|t| t.token_id.clone())
            .collect(),
        provenance_hash: j.derivation.provenance_hash.clone(),
        derivation: j.derivation.clone(),
        emitted_at: Utc::now(),
    };
    store.record(entry);

    // Audit writing must not change the permission
    assert_eq!(
        j.permission, permission_before_audit,
        "D11/T18: recording audit must not change permission"
    );

    // Reading audit back must show the same permission
    let entries = store.entries();
    assert_eq!(entries.len(), 1);
    assert_eq!(
        entries[0].permission, permission_before_audit,
        "D11/T18: audit entry must record original permission"
    );
}

// ── D12: Derivation token_ids reference tokens that were actually consulted ───

#[test]
fn d12_derivation_token_ids_are_consulted_tokens() {
    let mut ctx = base_ctx("d12");
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok_id = "tok-d12-consulted";
    let tok = valid_token(tok_id, vec!["g1"], &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();

    // Collect all token_ids across all derivation steps
    let all_token_ids: Vec<&str> = j
        .derivation
        .steps
        .iter()
        .flat_map(|s| s.token_ids.iter().map(|id| id.as_str()))
        .collect();

    // The consulted token must appear in the derivation
    assert!(
        all_token_ids.contains(&tok_id),
        "D12: consulted token {tok_id} must appear in derivation token_ids"
    );

    // All token_ids in derivation must reference tokens present in the context
    let ctx_token_ids: Vec<&str> = j
        .context
        .tokens
        .iter()
        .map(|t| t.token_id.as_str())
        .collect();
    for tid in &all_token_ids {
        assert!(
            ctx_token_ids.contains(tid),
            "D12: derivation references token {tid} not present in context"
        );
    }
}
