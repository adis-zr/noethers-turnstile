/// EC-003N — Certifier interface contract: issuer, validator, error paths.
///
/// The Certifier trait is the boundary between domain-specific evidence and
/// the structural algebra. Turnstile does not run certifiers; it consumes
/// their output (ProofToken). These tests verify:
///
///   1. A domain certifier can implement the Certifier trait
///   2. Issued tokens have correct structure (provenance hash, schema version)
///   3. Validation passes/fails based on provenance equality
///   4. Certifier-issued tokens work with the compiler end-to-end
///
/// Covers:
///   T3  — Provenance soundness: issued hash must bind (claim, candidate, ctx, use)
///   Spec §4 — The certifier interface
use chrono::Utc;
use serde_json::json;
use turnstile_core::{
    certifier::{Certifier, Evidence, IssueError, ValidationResult},
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Minimal concrete certifier for testing ───────────────────────────────────

struct CalibrationCertifier {
    gap_id: String,
}

impl CalibrationCertifier {
    fn for_gap(gap_id: impl Into<String>) -> Self {
        Self {
            gap_id: gap_id.into(),
        }
    }
}

impl Certifier for CalibrationCertifier {
    fn name(&self) -> &str {
        "calibration-certifier"
    }

    fn issue(&self, evidence: Evidence) -> Result<ProofToken, IssueError> {
        // Extract claim/candidate/context/use from the evidence payload.
        let claim_id = evidence.payload["claim_id"]
            .as_str()
            .ok_or_else(|| IssueError::InsufficientEvidence("missing claim_id".into()))?;
        let candidate_id = evidence.payload["candidate_id"]
            .as_str()
            .ok_or_else(|| IssueError::InsufficientEvidence("missing candidate_id".into()))?;
        let context_id = evidence.payload["context_id"]
            .as_str()
            .ok_or_else(|| IssueError::InsufficientEvidence("missing context_id".into()))?;
        let allowed_use = evidence.payload["allowed_use"]
            .as_str()
            .ok_or_else(|| IssueError::InsufficientEvidence("missing allowed_use".into()))?;

        if claim_id.is_empty() {
            return Err(IssueError::InsufficientEvidence(
                "claim_id must not be empty".into(),
            ));
        }

        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

        Ok(ProofToken {
            token_id: format!("cert-{}-{}", claim_id, candidate_id),
            token_type: format!("CERT_{}", self.gap_id.to_uppercase()),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![self.gap_id.clone()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "calibration-certifier".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        })
    }

    fn validate(&self, token: &ProofToken, ctx: &ProofContext) -> ValidationResult {
        let expected = compute_provenance_hash(
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        );
        if token.provenance_hash != expected {
            return ValidationResult::fail("provenance mismatch");
        }
        if token.schema_version != "0.1" {
            return ValidationResult::fail("schema version mismatch");
        }
        ValidationResult::ok()
    }
}

fn make_evidence(
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
) -> Evidence {
    Evidence {
        payload: json!({
            "claim_id": claim_id,
            "candidate_id": candidate_id,
            "context_id": context_id,
            "allowed_use": allowed_use,
        }),
        source: "test".into(),
    }
}

// ── Certifier issue happy path ────────────────────────────────────────────────

#[test]
fn certifier_issues_token_with_correct_provenance() {
    let certifier = CalibrationCertifier::for_gap("calibration_gap");
    let ev = make_evidence("claim-cert", "z-cert", "ctx-cert", "cert-use");
    let token = certifier.issue(ev).unwrap();

    let expected_hash = compute_provenance_hash("claim-cert", "z-cert", "ctx-cert", "cert-use");
    assert_eq!(token.provenance_hash, expected_hash);
    assert_eq!(token.status, TokenStatus::Valid);
    assert_eq!(token.schema_version, "0.1");
    assert!(token.closes_gaps.contains(&"calibration_gap".to_string()));
}

// ── Certifier validation: correct context → ok ────────────────────────────────

#[test]
fn certifier_validates_correctly_issued_token() {
    let certifier = CalibrationCertifier::for_gap("g1");
    let ev = make_evidence("claim-v", "z-v", "ctx-v", "v-use");
    let token = certifier.issue(ev).unwrap();

    let ctx = ProofContext {
        claim_id: "claim-v".into(),
        candidate_id: "z-v".into(),
        context_id: "ctx-v".into(),
        context_fingerprint: "fp-v".into(),
        allowed_use: "v-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let result = certifier.validate(&token, &ctx);
    assert!(result.valid, "correctly issued token must validate");
    assert!(result.reason.is_none());
}

// ── Certifier validation: wrong candidate → fail ──────────────────────────────

#[test]
fn certifier_validation_fails_wrong_candidate() {
    let certifier = CalibrationCertifier::for_gap("g1");
    let ev = make_evidence("claim", "z-orig", "ctx", "use");
    let token = certifier.issue(ev).unwrap();

    let wrong_ctx = ProofContext {
        claim_id: "claim".into(),
        candidate_id: "z-DIFFERENT".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let result = certifier.validate(&token, &wrong_ctx);
    assert!(!result.valid, "token must not validate for wrong candidate");
}

// ── Certifier rejects insufficient evidence ───────────────────────────────────

#[test]
fn certifier_rejects_missing_claim_id() {
    let certifier = CalibrationCertifier::for_gap("g1");
    let ev = Evidence {
        payload: json!({ "candidate_id": "z", "context_id": "ctx", "allowed_use": "use" }),
        source: "test".into(),
    };
    let result = certifier.issue(ev);
    assert!(matches!(result, Err(IssueError::InsufficientEvidence(_))));
}

#[test]
fn certifier_rejects_empty_claim_id() {
    let certifier = CalibrationCertifier::for_gap("g1");
    let ev = make_evidence("", "z", "ctx", "use"); // empty claim_id
    let result = certifier.issue(ev);
    assert!(matches!(result, Err(IssueError::InsufficientEvidence(_))));
}

// ── Certifier is Send + Sync ──────────────────────────────────────────────────

#[test]
fn certifier_trait_object_is_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<CalibrationCertifier>();
}

// ── End-to-end: certifier issues token, compiler accepts it ──────────────────

#[test]
fn certifier_issued_token_accepted_by_compiler() {
    let claim_id = "claim-e2e";
    let candidate_id = "z-e2e";
    let context_id = "ctx-e2e";
    let allowed_use = "e2e-use";
    let gap_id = "calibration_gap";

    let certifier = CalibrationCertifier::for_gap(gap_id);
    let ev = make_evidence(claim_id, candidate_id, context_id, allowed_use);
    let token = certifier.issue(ev).unwrap();

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-e2e".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, gap_id)],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![token],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "certifier-issued token must compile to DIA"
    );
}

// ── End-to-end: token issued for z1 rejected for z2 ──────────────────────────

#[test]
fn token_for_z1_not_accepted_for_z2_end_to_end() {
    let gap_id = "g1";
    let certifier = CalibrationCertifier::for_gap(gap_id);

    let token_for_z1 = certifier
        .issue(make_evidence("claim", "z-1", "ctx", "use"))
        .unwrap();

    let ctx_z2 = ProofContext {
        claim_id: "claim".into(),
        candidate_id: "z-2".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![token_for_z1],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx_z2).unwrap();
    // z1 token has wrong provenance for z2 → PROVENANCE_MISMATCH → REF
    assert_eq!(
        j.permission,
        Permission::REF,
        "z1 token must not license z2; PROVENANCE_MISMATCH floors to REF"
    );
}

// ── ValidationResult API ──────────────────────────────────────────────────────

#[test]
fn validation_result_ok_is_valid() {
    let r = ValidationResult::ok();
    assert!(r.valid);
    assert!(r.reason.is_none());
}

#[test]
fn validation_result_fail_carries_reason() {
    let r = ValidationResult::fail("test reason");
    assert!(!r.valid);
    assert_eq!(r.reason.as_deref(), Some("test reason"));
}
