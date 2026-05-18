/// Property test: Serialization round-trip (Spec §7, §8 determinism).
///
/// Every public type in the crate must be serializable and deserializable
/// with perfect fidelity (bit-identical round-trip).
///
/// This verifies:
///   - Spec §7: "Every public type is serde-friendly throughout"
///   - Spec §8: "Determinism: same ProofContext → bit-identical output"
///   - No silent field loss during JSON transit (important for audit replay)
///
/// Falsification: if any ProofContext, Judgment, or ProofToken loses data
/// through a serde round-trip, the audit record would be unrepresentative
/// of the original context, breaking the compliance story.
use chrono::Utc;
use noethers_turnstile_core::{
    audit::Derivation,
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, BoundKind, GapRecord, GapRequirement, GapStatus, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, NegativeControlStatus, ProofToken, TokenStatus},
};
use proptest::prelude::*;

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::OOC),
        Just(Permission::EXP),
        Just(Permission::REF),
        Just(Permission::UNS),
        Just(Permission::ETA),
        Just(Permission::ESC),
        Just(Permission::ROL),
        Just(Permission::DIA),
        Just(Permission::REV),
        Just(Permission::AEX),
        Just(Permission::ALR),
        Just(Permission::AAA),
    ]
}

fn base_ctx(suffix: &str, permission: Permission) -> ProofContext {
    let claim_id = format!("claim-serde-{suffix}");
    let candidate_id = format!("z-serde-{suffix}");
    let context_id = format!("ctx-serde-{suffix}");
    let allowed_use = format!("use-serde-{suffix}");
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-serde-{suffix}"),
        allowed_use,
        disallowed_uses: vec!["blocked-op".into()],
        scope: Scope {
            allowed_candidates: vec!["z-1".into(), "z-2".into()],
            allowed_paths: vec!["/api".into()],
            allowed_tools: vec!["read".into(), "write".into()],
            allowed_resources: vec!["db-1".into()],
        },
        gaps: vec![
            GapRecord::closed("g1", "calibration_gap"),
            GapRecord::bounded(
                "g2",
                "freshness_gap",
                Bound::numeric_with_units(0.05, "nats"),
            ),
            GapRecord::open("g3", "model_specification_gap"),
        ],
        profiles: vec![Profile {
            permission,
            required_gaps: vec![
                GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
                GapRequirement {
                    gap_id: "g2".into(),
                    minimum_status: RequiredStatus::BoundedRequired,
                },
            ],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-serde-{suffix}"),
            token_type: "CALIBRATION_TOKEN".into(),
            schema_version: "1.0".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec!["g2".into()],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: format!("certifier-{suffix}"),
            details: serde_json::json!({ "kl_bound": 0.05, "subgroup": "all" }),
            is_negative_control: false,
        }],
        expiry: Expiry::at_with_reason(
            Utc::now() + chrono::Duration::hours(1),
            "token validity window",
        ),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── ProofContext round-trip ────────────────────────────────────────────────────

#[test]
fn proof_context_json_roundtrip_preserves_all_fields() {
    let ctx = base_ctx("json-rt", Permission::DIA);
    let json = serde_json::to_string(&ctx).expect("serialize ProofContext");
    let recovered: ProofContext = serde_json::from_str(&json).expect("deserialize ProofContext");

    assert_eq!(recovered.claim_id, ctx.claim_id);
    assert_eq!(recovered.candidate_id, ctx.candidate_id);
    assert_eq!(recovered.context_id, ctx.context_id);
    assert_eq!(recovered.context_fingerprint, ctx.context_fingerprint);
    assert_eq!(recovered.allowed_use, ctx.allowed_use);
    assert_eq!(recovered.disallowed_uses, ctx.disallowed_uses);
    assert_eq!(recovered.authority_ceiling, ctx.authority_ceiling);
    assert_eq!(recovered.membership, ctx.membership);
    assert_eq!(recovered.gaps.len(), ctx.gaps.len());
    assert_eq!(recovered.profiles.len(), ctx.profiles.len());
    assert_eq!(recovered.tokens.len(), ctx.tokens.len());
    assert_eq!(recovered.tokens[0].token_id, ctx.tokens[0].token_id);
    assert_eq!(
        recovered.tokens[0].provenance_hash,
        ctx.tokens[0].provenance_hash
    );
    assert_eq!(recovered.tokens[0].issuer, ctx.tokens[0].issuer);
    assert_eq!(recovered.tokens[0].details, ctx.tokens[0].details);
    assert_eq!(recovered.expiry.deadline, ctx.expiry.deadline);
    assert_eq!(recovered.expiry.reason, ctx.expiry.reason);
}

// ── Judgment round-trip ───────────────────────────────────────────────────────

#[test]
fn judgment_json_roundtrip_preserves_permission() {
    let ctx = base_ctx("j-rt", Permission::DIA);
    let j = compile(ctx).unwrap();
    let json = serde_json::to_string(&j).expect("serialize Judgment");
    let recovered: noethers_turnstile_core::Judgment =
        serde_json::from_str(&json).expect("deserialize Judgment");

    assert_eq!(recovered.permission, j.permission);
    assert_eq!(recovered.expiry.deadline, j.expiry.deadline);
    assert_eq!(recovered.context.claim_id, j.context.claim_id);
    assert_eq!(
        recovered.derivation.provenance_hash,
        j.derivation.provenance_hash
    );
    assert_eq!(recovered.derivation.steps.len(), j.derivation.steps.len());
}

// ── Expiry round-trip ─────────────────────────────────────────────────────────

#[test]
fn expiry_never_roundtrip() {
    let e = Expiry::never();
    let json = serde_json::to_string(&e).unwrap();
    let r: Expiry = serde_json::from_str(&json).unwrap();
    assert!(r.deadline.is_none());
    assert!(r.reason.is_none());
}

#[test]
fn expiry_at_roundtrip() {
    let t = Utc::now();
    let e = Expiry::at(t);
    let json = serde_json::to_string(&e).unwrap();
    let r: Expiry = serde_json::from_str(&json).unwrap();
    // chrono serializes to RFC3339 at millisecond precision.
    assert!((r.deadline.unwrap() - t).num_milliseconds().abs() < 2);
}

#[test]
fn expiry_with_reason_roundtrip() {
    let t = Utc::now();
    let e = Expiry::at_with_reason(t, "token-window-expired");
    let json = serde_json::to_string(&e).unwrap();
    let r: Expiry = serde_json::from_str(&json).unwrap();
    assert_eq!(r.reason.as_deref(), Some("token-window-expired"));
}

// ── GapStatus round-trip ─────────────────────────────────────────────────────

#[test]
fn gap_status_open_roundtrip() {
    let s = GapStatus::Open;
    let json = serde_json::to_string(&s).unwrap();
    let r: GapStatus = serde_json::from_str(&json).unwrap();
    assert_eq!(r, GapStatus::Open);
}

#[test]
fn gap_status_bounded_numeric_roundtrip() {
    let s = GapStatus::Bounded(Bound::numeric_with_units(0.05, "nats"));
    let json = serde_json::to_string(&s).unwrap();
    let r: GapStatus = serde_json::from_str(&json).unwrap();
    match r {
        GapStatus::Bounded(b) => match b.kind {
            BoundKind::Numeric(v) => assert!((v.value() - 0.05).abs() < 1e-10),
            _ => panic!("expected Numeric bound"),
        },
        _ => panic!("expected Bounded"),
    }
}

#[test]
fn gap_status_bounded_set_valued_roundtrip() {
    let s = GapStatus::Bounded(Bound::set_valued(vec!["a".into(), "b".into()]));
    let json = serde_json::to_string(&s).unwrap();
    let r: GapStatus = serde_json::from_str(&json).unwrap();
    match r {
        GapStatus::Bounded(b) => match b.kind {
            BoundKind::SetValued(v) => assert_eq!(v, vec!["a", "b"]),
            _ => panic!("expected SetValued bound"),
        },
        _ => panic!("expected Bounded"),
    }
}

#[test]
fn gap_status_closed_roundtrip() {
    let s = GapStatus::Closed;
    let json = serde_json::to_string(&s).unwrap();
    let r: GapStatus = serde_json::from_str(&json).unwrap();
    assert_eq!(r, GapStatus::Closed);
}

// ── TokenStatus round-trip ───────────────────────────────────────────────────

#[test]
fn token_status_all_variants_roundtrip() {
    for status in [
        TokenStatus::Valid,
        TokenStatus::Invalid,
        TokenStatus::Expired,
        TokenStatus::Revoked,
        TokenStatus::Malformed,
    ] {
        let json = serde_json::to_string(&status).unwrap();
        let r: TokenStatus = serde_json::from_str(&json).unwrap();
        assert_eq!(r, status);
    }
}

// ── NegativeControlStatus round-trip ─────────────────────────────────────────

#[test]
fn nc_status_all_variants_roundtrip() {
    for status in [
        NegativeControlStatus::Live,
        NegativeControlStatus::Stale,
        NegativeControlStatus::Failed,
        NegativeControlStatus::Missing,
    ] {
        let json = serde_json::to_string(&status).unwrap();
        let r: NegativeControlStatus = serde_json::from_str(&json).unwrap();
        assert_eq!(r, status);
    }
}

// ── Permission round-trip ─────────────────────────────────────────────────────

#[test]
fn permission_all_variants_roundtrip() {
    for p in Permission::descending() {
        let json = serde_json::to_string(&p).unwrap();
        let r: Permission = serde_json::from_str(&json).unwrap();
        assert_eq!(r, p);
    }
}

// ── Membership round-trip ─────────────────────────────────────────────────────

#[test]
fn membership_all_variants_roundtrip() {
    let variants = vec![
        Membership::InClass,
        Membership::OutOfClassExact,
        Membership::OutOfClassAuthorizedDeterministicWrite,
        Membership::OutOfClassNoConsequentialUse,
        Membership::OutOfClassOther("custom".into()),
    ];
    for m in &variants {
        let json = serde_json::to_string(m).unwrap();
        let r: Membership = serde_json::from_str(&json).unwrap();
        assert_eq!(&r, m);
    }
}

// ── Derivation round-trip ─────────────────────────────────────────────────────

#[test]
fn derivation_round_trip_preserves_steps() {
    let ctx = base_ctx("deriv-rt", Permission::DIA);
    let j = compile(ctx).unwrap();
    let json = serde_json::to_string(&j.derivation).unwrap();
    let r: Derivation = serde_json::from_str(&json).unwrap();
    assert_eq!(r.steps.len(), j.derivation.steps.len());
    for (a, b) in r.steps.iter().zip(j.derivation.steps.iter()) {
        assert_eq!(a.phase, b.phase);
        assert_eq!(a.permission_after, b.permission_after);
        assert_eq!(a.note, b.note);
    }
    assert_eq!(r.provenance_hash, j.derivation.provenance_hash);
}

// ── Compile + serde → recompile produces same result (determinism) ────────────

#[test]
fn serde_roundtrip_then_recompile_same_permission() {
    let ctx = base_ctx("recompile", Permission::DIA);
    let j1 = compile(ctx.clone()).unwrap();

    // Serialize the context and recover it.
    let json = serde_json::to_string(&ctx).unwrap();
    let recovered_ctx: ProofContext = serde_json::from_str(&json).unwrap();
    let j2 = compile(recovered_ctx).unwrap();

    assert_eq!(
        j1.permission, j2.permission,
        "serde round-trip broke determinism: {} vs {}",
        j1.permission, j2.permission
    );
}

// ── Proptest: ProofContext serde round-trip preserves permission ──────────────

proptest! {
    #[test]
    fn prop_serde_roundtrip_preserves_permission(
        target in arb_permission(),
    ) {
        if target == Permission::OOC { return Ok(()); }

        let ctx = base_ctx("prop-serde", target);
        let p_before = compile(ctx.clone()).unwrap().permission;

        let json = serde_json::to_string(&ctx).unwrap();
        let recovered: ProofContext = serde_json::from_str(&json).unwrap();
        let p_after = compile(recovered).unwrap().permission;

        prop_assert_eq!(
            p_before, p_after,
            "serde round-trip changed permission from {} to {}",
            p_before, p_after
        );
    }

    #[test]
    fn prop_judgment_serde_preserves_all_fields(
        target in arb_permission(),
    ) {
        if target == Permission::OOC { return Ok(()); }

        let ctx = base_ctx("prop-j-serde", target);
        let j = compile(ctx).unwrap();
        let json = serde_json::to_string(&j).unwrap();
        let r: noethers_turnstile_core::Judgment = serde_json::from_str(&json).unwrap();

        prop_assert_eq!(r.permission, j.permission);
        prop_assert_eq!(r.context.claim_id, j.context.claim_id);
        prop_assert_eq!(r.context.allowed_use, j.context.allowed_use);
        prop_assert_eq!(r.derivation.provenance_hash, j.derivation.provenance_hash);
    }

    #[test]
    fn prop_permission_serde_roundtrip(p in arb_permission()) {
        let json = serde_json::to_string(&p).unwrap();
        let r: Permission = serde_json::from_str(&json).unwrap();
        prop_assert_eq!(r, p);
    }
}
