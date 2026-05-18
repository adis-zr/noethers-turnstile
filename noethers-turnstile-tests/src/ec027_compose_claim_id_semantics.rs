/// EC-027 — Compose claim_id / candidate_id semantics.
///
/// `compose(g1, g2)` inherits `g1`'s `claim_id`, `candidate_id`, and
/// `context_id`.  This means tokens issued for g2's claim tuple will have
/// the wrong provenance hash in the composed context and will be silently
/// rejected by `compile()`.
///
/// This suite documents and tests this exact behaviour so callers know what
/// to expect when composing contexts that differ in identity fields:
///
///   C1 — Composing two contexts with the same allowed_use succeeds regardless
///         of differing claim_id/candidate_id (allowed_use is the composition gate).
///   C2 — After compose, the result inherits g1's claim_id.
///   C3 — After compose, the result inherits g1's candidate_id.
///   C4 — After compose, the result inherits g1's context_id.
///   C5 — A token issued for g1's claim tuple is valid after composition.
///   C6 — A token issued for g2's claim tuple is rejected (wrong provenance)
///         after composition (because claim_id changed to g1's).
///   C7 — Compose of two identical contexts (same all fields) is idempotent
///         w.r.t. claim identity.
///   C8 — Context fingerprint is the concatenation of both fingerprints.
use noethers_turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

use chrono::Utc;

fn make_ctx(
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    fp: &str,
    allowed_use: &str,
) -> ProofContext {
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: fp.into(),
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
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn closing_token(
    id: &str,
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
) -> ProofToken {
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    ProofToken {
        token_id: id.into(),
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
    }
}

// ── C1: Compose succeeds with differing claim_id / candidate_id ───────────────

#[test]
fn c1_compose_succeeds_with_differing_claim_ids() {
    let g1 = make_ctx("claim-A", "z-1", "ctx-1", "fp-1", "shared-use");
    let g2 = make_ctx("claim-B", "z-2", "ctx-2", "fp-2", "shared-use");
    let result = compose(g1, g2);
    assert!(
        result.is_ok(),
        "C1: compose must succeed when allowed_use matches, even with different claim_ids"
    );
}

// ── C2: Result inherits g1's claim_id ────────────────────────────────────────

#[test]
fn c2_composed_context_inherits_g1_claim_id() {
    let g1 = make_ctx("claim-G1", "z-1", "ctx-1", "fp-1", "shared-use");
    let g2 = make_ctx("claim-G2", "z-2", "ctx-2", "fp-2", "shared-use");
    let composed = compose(g1, g2).unwrap();
    assert_eq!(
        composed.claim_id, "claim-G1",
        "C2: composed context must inherit g1's claim_id"
    );
}

// ── C3: Result inherits g1's candidate_id ────────────────────────────────────

#[test]
fn c3_composed_context_inherits_g1_candidate_id() {
    let g1 = make_ctx("claim-1", "z-G1", "ctx-1", "fp-1", "shared-use");
    let g2 = make_ctx("claim-2", "z-G2", "ctx-2", "fp-2", "shared-use");
    let composed = compose(g1, g2).unwrap();
    assert_eq!(
        composed.candidate_id, "z-G1",
        "C3: composed context must inherit g1's candidate_id"
    );
}

// ── C4: Result inherits g1's context_id ──────────────────────────────────────

#[test]
fn c4_composed_context_inherits_g1_context_id() {
    let g1 = make_ctx("claim-1", "z-1", "ctx-G1", "fp-1", "shared-use");
    let g2 = make_ctx("claim-2", "z-2", "ctx-G2", "fp-2", "shared-use");
    let composed = compose(g1, g2).unwrap();
    assert_eq!(
        composed.context_id, "ctx-G1",
        "C4: composed context must inherit g1's context_id"
    );
}

// ── C5: Token issued for g1 is valid after composition ───────────────────────
//
// After composition, the composed context inherits g1's identity.  A token
// hashed for g1's claim tuple has correct provenance in the composed context
// and is accepted (does NOT trigger PROVENANCE_MISMATCH → REF).
//
// However, T9 (non-promotion) caps the composed result at
// meet(compile(g1), compile(g2)).  g2 has a profile but no token, so
// compile(g2) = UNS.  Therefore the composed result is capped at
// meet(DIA, UNS) = UNS — the token is accepted (no REF), but the
// non-promotion ceiling limits the outcome.
//
// Contrast with C6: the g2 token IS rejected (REF), because g2's token is
// wrong-provenance in the composed context.

#[test]
fn c5_g1_token_remains_valid_after_composition() {
    let mut g1 = make_ctx("claim-G1", "z-G1", "ctx-G1", "fp-1", "c5-use");
    let g2 = make_ctx("claim-G2", "z-G2", "ctx-G2", "fp-2", "c5-use");

    // Token correctly hashed for g1.
    let tok = closing_token("c5-tok", "claim-G1", "z-G1", "ctx-G1", "c5-use");
    g1.tokens.push(tok);

    let composed = compose(g1, g2).unwrap();
    let j = compile(composed).unwrap();
    // Token is accepted (correct provenance → no REF from PROVENANCE_MISMATCH).
    // T9 non-promotion ceiling = meet(DIA, UNS) = UNS caps the outcome.
    assert_ne!(
        j.permission,
        Permission::REF,
        "C5: token with correct provenance must not trigger PROVENANCE_MISMATCH"
    );
    assert_eq!(
        j.permission,
        Permission::UNS,
        "C5: composed result is UNS because non-promotion ceiling = meet(DIA, UNS) = UNS"
    );
}

// ── C6: Token issued for g2 is silently rejected after composition ────────────

#[test]
fn c6_g2_token_rejected_after_composition() {
    let g1 = make_ctx("claim-G1", "z-G1", "ctx-G1", "fp-1", "c6-use");
    let mut g2 = make_ctx("claim-G2", "z-G2", "ctx-G2", "fp-2", "c6-use");

    // Token correctly hashed for g2, but wrong after composition (claim_id → g1).
    let tok = closing_token("c6-tok", "claim-G2", "z-G2", "ctx-G2", "c6-use");
    g2.tokens.push(tok);

    let composed = compose(g1, g2).unwrap();
    let j = compile(composed).unwrap();
    // The token's provenance doesn't match the composed context (g1's identity),
    // so it is rejected (PROVENANCE_MISMATCH) → REF meet applied.
    // InClass candidate with profile defined but unmet → REF (not OOC).
    assert_eq!(
        j.permission,
        Permission::REF,
        "C6: token issued for g2 must be rejected (provenance mismatch) after composition → REF"
    );
}

// ── C7: Same-claim composition is idempotent on claim identity ────────────────

#[test]
fn c7_same_claim_composition_idempotent() {
    let g1 = make_ctx("claim-same", "z-same", "ctx-same", "fp-same", "c7-use");
    let g2 = g1.clone();
    let composed = compose(g1.clone(), g2).unwrap();
    assert_eq!(
        composed.claim_id, g1.claim_id,
        "C7: composing identical contexts must preserve claim_id"
    );
    assert_eq!(
        composed.candidate_id, g1.candidate_id,
        "C7: composing identical contexts must preserve candidate_id"
    );
}

// ── C8: Fingerprint is the concatenation of both fingerprints ─────────────────

#[test]
fn c8_fingerprint_is_concatenated() {
    let g1 = make_ctx("c1", "z1", "ctx1", "fp-alpha", "c8-use");
    let g2 = make_ctx("c2", "z2", "ctx2", "fp-beta", "c8-use");
    let composed = compose(g1, g2).unwrap();
    assert_eq!(
        composed.context_fingerprint, "fp-alpha+fp-beta",
        "C8: composed fingerprint must be 'fp-alpha+fp-beta'"
    );
}
