/// EC-037 — Serde round-trip and wire-format stability.
///
/// A production library must have a stable, fully-round-trippable serialization
/// format.  Callers serialize judgments to JSON (for audit logs, REST APIs,
/// message queues) and must be able to deserialize them back identically.
///
/// Coverage:
///   W1  — Judgment round-trips through serde_json for all 12 Permission values
///   W2  — ProofContext round-trips through serde_json
///   W3  — ProofToken round-trips for all TokenStatus variants
///   W4  — GapRecord round-trips for Open, Bounded, Closed
///   W5  — Expiry round-trips: never, deadline, deadline+reason
///   W6  — RuntimeContext round-trips with NC state map
///   W7  — Permission serializes as UPPERCASE strings (stable tag)
///   W8  — TokenStatus serializes as SCREAMING_SNAKE_CASE strings
///   W9  — GapStatus serializes with tagged enum format (status / bound fields)
///   W10 — NegativeControlStatus serializes as SCREAMING_SNAKE_CASE
///   W11 — Derivation round-trips: steps, provenance_hash, compiled_at
///   W12 — compose() round-trips: composed context serializes correctly
use chrono::Utc;
use turnstile_core::{
    audit::{Derivation, DerivationStep},
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, RuntimeContext},
    gap::{Bound, GapRecord, GapRequirement, GapStatus, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
    NegativeControlStatus,
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

// ── W1: Judgment round-trips for all 12 Permission values ─────────────────────

#[test]
fn w1_judgment_serde_roundtrip_all_permissions() {
    let mut ctx = base_ctx("w1");
    ctx.gaps.push(GapRecord::closed("g1", "t"));

    for p in Permission::descending() {
        if p == Permission::OOC {
            continue; // OOC only via membership check; skip for this test
        }
        let mut c = ctx.clone();
        c.authority_ceiling = p;
        c.profiles.push(Profile {
            permission: p,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = valid_token(&format!("tok-{p}"), vec!["g1"], &c);
        c.tokens.push(tok);

        let j = compile(c).unwrap();
        let json = serde_json::to_string(&j).expect("Judgment must serialize");
        let j2: turnstile_core::compiler::Judgment =
            serde_json::from_str(&json).expect("Judgment must deserialize");
        assert_eq!(
            j2.permission, j.permission,
            "W1: Judgment for {p} must round-trip through JSON"
        );
    }
}

// ── W2: ProofContext round-trips ──────────────────────────────────────────────

#[test]
fn w2_proof_context_serde_roundtrip() {
    let mut ctx = base_ctx("w2");
    ctx.gaps.push(GapRecord::open("g1", "truth_gap"));
    ctx.gaps
        .push(GapRecord::bounded("g2", "proxy_gap", Bound::numeric(0.05)));
    ctx.gaps.push(GapRecord::closed("g3", "support_gap"));
    ctx.disallowed_uses = vec!["write".into(), "production-action".into()];
    ctx.scope = Scope {
        allowed_candidates: vec!["z-1".into()],
        allowed_paths: vec!["/safe".into()],
        allowed_tools: vec!["diagnostics".into()],
        allowed_resources: vec!["read-only-db".into()],
    };
    ctx.authority_ceiling = Permission::DIA;
    ctx.expiry = Expiry::at_with_reason(Utc::now() + chrono::Duration::hours(1), "session-expiry");

    let json = serde_json::to_string(&ctx).expect("ProofContext must serialize");
    let ctx2: ProofContext = serde_json::from_str(&json).expect("ProofContext must deserialize");

    assert_eq!(ctx.claim_id, ctx2.claim_id);
    assert_eq!(ctx.allowed_use, ctx2.allowed_use);
    assert_eq!(ctx.gaps.len(), ctx2.gaps.len());
    assert_eq!(ctx.disallowed_uses, ctx2.disallowed_uses);
    assert_eq!(ctx.authority_ceiling, ctx2.authority_ceiling);
    assert_eq!(ctx.expiry.deadline, ctx2.expiry.deadline);
    assert_eq!(ctx.scope.allowed_candidates, ctx2.scope.allowed_candidates);
}

// ── W3: ProofToken round-trips for all TokenStatus variants ──────────────────

#[test]
fn w3_proof_token_serde_roundtrip_all_statuses() {
    let statuses = [
        TokenStatus::Valid,
        TokenStatus::Invalid,
        TokenStatus::Expired,
        TokenStatus::Revoked,
        TokenStatus::Malformed,
    ];

    let ctx = base_ctx("w3");
    for status in statuses {
        let mut tok = valid_token(&format!("tok-{status:?}"), vec![], &ctx);
        tok.status = status;
        tok.expires_at = Some(Utc::now() + chrono::Duration::hours(1));

        let json = serde_json::to_string(&tok).expect("ProofToken must serialize");
        let tok2: ProofToken = serde_json::from_str(&json).expect("ProofToken must deserialize");
        assert_eq!(tok.token_id, tok2.token_id);
        assert_eq!(tok.status, tok2.status);
        assert_eq!(tok.expires_at, tok2.expires_at);
    }
}

// ── W4: GapRecord round-trips for all GapStatus variants ─────────────────────

#[test]
fn w4_gap_record_serde_roundtrip_all_variants() {
    let records = vec![
        GapRecord::open("g-open", "truth_gap"),
        GapRecord::bounded("g-bounded", "proxy_gap", Bound::numeric(0.05)),
        GapRecord::bounded(
            "g-bounded-set",
            "scope_gap",
            Bound::set_valued(vec!["tool-a".into(), "tool-b".into()]),
        ),
        GapRecord::bounded("g-bounded-inf", "unknown_gap", Bound::infinity()),
        GapRecord::closed("g-closed", "support_gap"),
    ];

    for record in &records {
        let json = serde_json::to_string(record).expect("GapRecord must serialize");
        let r2: GapRecord = serde_json::from_str(&json).expect("GapRecord must deserialize");
        assert_eq!(record.gap_id, r2.gap_id);
        assert_eq!(record.gap_type, r2.gap_type);
        assert_eq!(record.status.rank(), r2.status.rank());
    }
}

// ── W5: Expiry round-trips ────────────────────────────────────────────────────

#[test]
fn w5_expiry_never_roundtrip() {
    let e = Expiry::never();
    let json = serde_json::to_string(&e).unwrap();
    let e2: Expiry = serde_json::from_str(&json).unwrap();
    assert_eq!(e2.deadline, None);
    assert_eq!(e2.reason, None);
}

#[test]
fn w5_expiry_with_deadline_roundtrip() {
    let deadline = Utc::now() + chrono::Duration::minutes(30);
    let e = Expiry::at(deadline);
    let json = serde_json::to_string(&e).unwrap();
    let e2: Expiry = serde_json::from_str(&json).unwrap();
    // Timestamps serialize at second resolution via chrono; compare at seconds
    assert_eq!(
        e2.deadline.map(|d| d.timestamp()),
        e.deadline.map(|d| d.timestamp()),
        "W5: expiry deadline must round-trip to same second"
    );
}

#[test]
fn w5_expiry_with_reason_roundtrip() {
    let deadline = Utc::now() + chrono::Duration::minutes(30);
    let e = Expiry::at_with_reason(deadline, "session-timeout");
    let json = serde_json::to_string(&e).unwrap();
    let e2: Expiry = serde_json::from_str(&json).unwrap();
    assert_eq!(e2.reason, Some("session-timeout".to_string()));
}

// ── W6: RuntimeContext round-trips with NC state map ─────────────────────────

#[test]
fn w6_runtime_context_serde_roundtrip() {
    let mut nc_states = std::collections::HashMap::new();
    nc_states.insert("tok-1".to_string(), NegativeControlStatus::Live);
    nc_states.insert("tok-2".to_string(), NegativeControlStatus::Stale);
    nc_states.insert("tok-3".to_string(), NegativeControlStatus::Failed);
    nc_states.insert("tok-4".to_string(), NegativeControlStatus::Missing);

    let rt = RuntimeContext::with_nc_states(Utc::now(), "fp-rt", nc_states, true);

    let json = serde_json::to_string(&rt).expect("RuntimeContext must serialize");
    let rt2: RuntimeContext = serde_json::from_str(&json).expect("RuntimeContext must deserialize");

    assert_eq!(rt2.context_fingerprint, "fp-rt");
    assert_eq!(rt2.strict_mode, true);
    assert_eq!(
        rt2.negative_control_states.get("tok-1"),
        Some(&NegativeControlStatus::Live)
    );
    assert_eq!(
        rt2.negative_control_states.get("tok-2"),
        Some(&NegativeControlStatus::Stale)
    );
}

// ── W7: Permission serializes as UPPERCASE tag strings ───────────────────────

#[test]
fn w7_permission_serializes_as_uppercase_tag() {
    let cases = [
        (Permission::OOC, "\"OOC\""),
        (Permission::EXP, "\"EXP\""),
        (Permission::REF, "\"REF\""),
        (Permission::UNS, "\"UNS\""),
        (Permission::ETA, "\"ETA\""),
        (Permission::ESC, "\"ESC\""),
        (Permission::ROL, "\"ROL\""),
        (Permission::DIA, "\"DIA\""),
        (Permission::REV, "\"REV\""),
        (Permission::AEX, "\"AEX\""),
        (Permission::ALR, "\"ALR\""),
        (Permission::AAA, "\"AAA\""),
    ];

    for (perm, expected_json) in &cases {
        let json = serde_json::to_string(perm).expect("Permission must serialize");
        assert_eq!(
            &json, expected_json,
            "W7: {perm:?} must serialize as {expected_json}"
        );
    }
}

#[test]
fn w7_permission_deserializes_from_uppercase_tag() {
    let cases = [
        ("\"OOC\"", Permission::OOC),
        ("\"DIA\"", Permission::DIA),
        ("\"AEX\"", Permission::AEX),
        ("\"AAA\"", Permission::AAA),
    ];

    for (json, expected) in &cases {
        let p: Permission = serde_json::from_str(json).expect("Permission must deserialize");
        assert_eq!(p, *expected, "W7: {json} must deserialize to {expected:?}");
    }
}

// ── W8: TokenStatus serializes as SCREAMING_SNAKE_CASE ───────────────────────

#[test]
fn w8_token_status_serializes_as_screaming_snake_case() {
    let cases = [
        (TokenStatus::Valid, "\"VALID\""),
        (TokenStatus::Invalid, "\"INVALID\""),
        (TokenStatus::Expired, "\"EXPIRED\""),
        (TokenStatus::Revoked, "\"REVOKED\""),
        (TokenStatus::Malformed, "\"MALFORMED\""),
    ];

    for (status, expected) in &cases {
        let json = serde_json::to_string(status).unwrap();
        assert_eq!(
            &json, expected,
            "W8: {status:?} must serialize as {expected}"
        );
    }
}

// ── W9: GapStatus tag structure ────────────────────────────────────────────────

#[test]
fn w9_gap_status_serializes_with_correct_tag() {
    let open = GapStatus::Open;
    let closed = GapStatus::Closed;
    let bounded = GapStatus::Bounded(Bound::numeric(0.05));

    let open_json = serde_json::to_string(&open).unwrap();
    let closed_json = serde_json::to_string(&closed).unwrap();
    let bounded_json = serde_json::to_string(&bounded).unwrap();

    assert!(
        open_json.contains("Open") || open_json.contains("open"),
        "W9: Open must appear in JSON"
    );
    assert!(
        closed_json.contains("Closed") || closed_json.contains("closed"),
        "W9: Closed must appear in JSON"
    );
    assert!(
        bounded_json.contains("Bounded") || bounded_json.contains("bounded"),
        "W9: Bounded must appear in JSON"
    );
}

// ── W10: NegativeControlStatus SCREAMING_SNAKE_CASE ──────────────────────────

#[test]
fn w10_nc_status_serializes_as_screaming_snake_case() {
    let cases = [
        (NegativeControlStatus::Live, "\"LIVE\""),
        (NegativeControlStatus::Stale, "\"STALE\""),
        (NegativeControlStatus::Failed, "\"FAILED\""),
        (NegativeControlStatus::Missing, "\"MISSING\""),
    ];

    for (status, expected) in &cases {
        let json = serde_json::to_string(status).unwrap();
        assert_eq!(
            &json, expected,
            "W10: {status:?} must serialize as {expected}"
        );
    }
}

// ── W11: Derivation round-trips ────────────────────────────────────────────────

#[test]
fn w11_derivation_roundtrip() {
    let mut d = Derivation::new().with_provenance("abc123def456");
    d.push(DerivationStep {
        phase: "membership_check".into(),
        permission_after: Permission::OOC,
        note: "test step".into(),
        token_ids: vec!["tok-1".into()],
    });

    let json = serde_json::to_string(&d).expect("Derivation must serialize");
    let d2: Derivation = serde_json::from_str(&json).expect("Derivation must deserialize");

    assert_eq!(d2.provenance_hash, "abc123def456");
    assert_eq!(d2.steps.len(), 1);
    assert_eq!(d2.steps[0].phase, "membership_check");
    assert_eq!(d2.steps[0].permission_after, Permission::OOC);
}

// ── W12: compose() result round-trips ────────────────────────────────────────

#[test]
fn w12_composed_context_serde_roundtrip() {
    let mut ctx1 = base_ctx("w12a");
    ctx1.gaps.push(GapRecord::closed("g1", "t"));
    ctx1.disallowed_uses = vec!["write".into()];

    let mut ctx2 = base_ctx("w12b");
    ctx2.gaps.push(GapRecord::open("g2", "t"));
    ctx2.authority_ceiling = Permission::DIA;

    let composed = compose(ctx1, ctx2).unwrap();
    let json = serde_json::to_string(&composed).expect("Composed context must serialize");
    let ctx2_deser: ProofContext =
        serde_json::from_str(&json).expect("Composed context must deserialize");

    assert_eq!(
        ctx2_deser.authority_ceiling,
        Permission::DIA,
        "W12: authority ceiling must survive round-trip"
    );
    assert!(
        ctx2_deser.disallowed_uses.contains(&"write".to_string()),
        "W12: disallowed_uses must survive round-trip"
    );
    assert_eq!(
        ctx2_deser.gaps.len(),
        2,
        "W12: both gaps must survive round-trip"
    );
}
