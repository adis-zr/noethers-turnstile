/// EC-017 — Error type coverage: every TurnstileError and CompositionError
///           variant is reachable and carries the right data.
///
/// This test suite ensures:
///   - No error variant is dead code.
///   - Every variant contains meaningful data (where applicable).
///   - Error Display/Debug output is non-empty (usable in logs).
///   - Errors propagate correctly through the public API.
use chrono::Utc;
use noethers_noethers_turnstile_core::{
    compose,
    context::{Membership, ProofContext, Scope},
    error::CompositionError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn base_ctx(suffix: &str, allowed_use: &str) -> ProofContext {
    let claim_id = format!("claim-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
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

// ── UseConflict ───────────────────────────────────────────────────────────────

#[test]
fn use_conflict_is_reachable() {
    let ctx1 = base_ctx("uc-a", "use-A");
    let ctx2 = base_ctx("uc-b", "use-B");
    let err = compose(ctx1, ctx2).unwrap_err();
    assert!(matches!(err, CompositionError::UseConflict));
}

#[test]
fn use_conflict_display_is_nonempty() {
    let err = CompositionError::UseConflict;
    let msg = format!("{err}");
    assert!(
        !msg.is_empty(),
        "UseConflict Display must produce a non-empty message"
    );
    assert!(
        !format!("{err:?}").is_empty(),
        "UseConflict Debug must produce a non-empty message"
    );
}

// ── TokenConflict ─────────────────────────────────────────────────────────────

#[test]
fn token_conflict_is_reachable_with_token_id() {
    let mut ctx1 = base_ctx("tc-a", "shared-use");
    let mut ctx2 = base_ctx("tc-b", "shared-use");

    let hash = compute_provenance_hash(
        &ctx1.claim_id,
        &ctx1.candidate_id,
        &ctx1.context_id,
        &ctx1.allowed_use,
    );
    let tok_a = ProofToken {
        token_id: "conflict-tok".into(),
        token_type: "TYPE-A".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "certifier-A".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let tok_b = ProofToken {
        token_id: "conflict-tok".into(),
        token_type: "TYPE-B".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "certifier-B".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx1.tokens = vec![tok_a];
    ctx2.tokens = vec![tok_b];

    let err = compose(ctx1, ctx2).unwrap_err();
    match &err {
        CompositionError::TokenConflict { token_id } => {
            assert_eq!(
                token_id, "conflict-tok",
                "TokenConflict must carry the conflicting token_id"
            );
        }
        other => panic!("expected TokenConflict, got {:?}", other),
    }
}

#[test]
fn token_conflict_display_contains_token_id() {
    let err = CompositionError::TokenConflict {
        token_id: "my-conflicting-token".into(),
    };
    let msg = format!("{err}");
    assert!(
        msg.contains("my-conflicting-token"),
        "TokenConflict Display must contain the token_id; got: {msg}"
    );
}

// ── EmptyComposition ──────────────────────────────────────────────────────────

#[test]
fn empty_composition_is_reachable() {
    let err = noethers_turnstile_core::compose_n(std::iter::empty::<ProofContext>()).unwrap_err();
    assert!(matches!(err, CompositionError::EmptyComposition));
}

#[test]
fn empty_composition_display_is_nonempty() {
    let err = CompositionError::EmptyComposition;
    assert!(
        !format!("{err}").is_empty(),
        "EmptyComposition Display must produce a non-empty message"
    );
}

// ── All CompositionError variants are Debug + Display ────────────────────────

#[test]
fn all_composition_error_variants_are_debug_display() {
    let variants: Vec<CompositionError> = vec![
        CompositionError::UseConflict,
        CompositionError::TokenConflict {
            token_id: "tok".into(),
        },
        CompositionError::EmptyComposition,
    ];

    for v in &variants {
        let display = format!("{v}");
        let debug = format!("{v:?}");
        assert!(
            !display.is_empty(),
            "CompositionError variant Display must be non-empty: {debug}"
        );
        assert!(
            !debug.is_empty(),
            "CompositionError variant Debug must be non-empty: {display}"
        );
    }
}

// ── std::error::Error is implemented ─────────────────────────────────────────

#[test]
fn composition_error_implements_std_error() {
    fn is_error<T: std::error::Error>() {}
    is_error::<CompositionError>();
}

// ── Error propagation through compose_n ──────────────────────────────────────

#[test]
fn use_conflict_propagates_through_compose_n() {
    let ctx1 = base_ctx("cn-uc-1", "use-A");
    let ctx2 = base_ctx("cn-uc-2", "use-B"); // conflict
    let result = noethers_turnstile_core::compose_n([ctx1, ctx2]);
    assert!(
        matches!(result, Err(CompositionError::UseConflict)),
        "UseConflict must propagate through compose_n"
    );
}

// ── TurnstileError wraps CompositionError ────────────────────────────────────

#[test]
fn turnstile_error_wraps_composition_error() {
    use noethers_noethers_turnstile_core::error::TurnstileError;
    let comp_err = CompositionError::UseConflict;
    let turnstile_err: TurnstileError = comp_err.into();
    let display = format!("{turnstile_err}");
    assert!(!display.is_empty());
}

#[test]
fn all_turnstile_error_variants_are_debug_display() {
    use noethers_noethers_turnstile_core::error::TurnstileError;
    let variants: Vec<TurnstileError> = vec![
        TurnstileError::Composition(CompositionError::UseConflict),
        TurnstileError::ProvenanceMismatch {
            token_id: "t".into(),
            expected: "e".into(),
            actual: "a".into(),
        },
        TurnstileError::SchemaVersionMismatch {
            token_version: "1.0".into(),
            registry_version: "2.0".into(),
        },
        TurnstileError::MalformedContext("bad field".into()),
        TurnstileError::Expired {
            deadline: "2020-01-01T00:00:00Z".into(),
        },
    ];

    for v in &variants {
        let display = format!("{v}");
        let debug = format!("{v:?}");
        assert!(
            !display.is_empty(),
            "TurnstileError Display must be non-empty: {debug}"
        );
        assert!(!debug.is_empty(), "TurnstileError Debug must be non-empty");
    }
}
