/// EC-032 — Positive families P1–P10 (EC-001 §34).
///
/// EC-001 §34 defines ten positive families of approximate consequential systems
/// that should be in class and require admissibility judgments.  Each test here
/// calls its shot before constructing the scenario (pre-registration discipline).
///
/// Every positive family must:
///   - Be classified IN_CLASS
///   - Induce gaps that correspond to the domain
///   - Provide sufficient proof tokens
///   - Compile to the expected permission outcome
///
/// Families tested:
///   P1  — Approximate probabilistic inference (KL-divergence bound)
///   P2  — Off-policy evaluation / causal inference
///   P3  — Marketplace allocation
///   P4  — Medical triage / clinical risk scoring
///   P5  — Fraud and trust decisions
///   P6  — Cybersecurity response
///   P7  — Trading and portfolio risk
///   P8  — LLM agent deployment decisions
///   P9  — Scientific simulation and surrogate modeling
///   P10 — Resource-constrained planning
use chrono::Utc;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn build_ctx(
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
    authority_ceiling: Permission,
    gaps: Vec<GapRecord>,
    profiles: Vec<Profile>,
    tokens: Vec<ProofToken>,
) -> ProofContext {
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: format!("fp-{claim_id}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles,
        tokens,
        expiry: Expiry::never(),
        authority_ceiling,
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
        issuer: "test-certifier".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn bounding_token(id: &str, bounds: Vec<&str>, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: id.into(),
        token_type: "KL_BOUND".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: bounds.into_iter().map(String::from).collect(),
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "inference-certifier".into(),
        details: serde_json::json!({"kl_divergence_bound": 0.05}),
        is_negative_control: false,
    }
}

// ── P1: Approximate probabilistic inference ───────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes (approximate posterior used as evidence for downstream action)
//   Gaps: calibration_gap (BOUNDED), support_gap (CLOSED)
//   Tokens: KL-bound token (bounds calibration), support witness (closes support)
//   Expected: DIA (diagnostic-only action licensed)

#[test]
fn p1_approximate_inference_with_kl_bound_compiles_to_dia() {
    let gaps = vec![
        GapRecord::bounded("g-calibration", "calibration_gap", Bound::numeric(0.05)),
        GapRecord::closed("g-support", "support_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-calibration".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            },
            GapRequirement {
                gap_id: "g-support".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p1-claim", "z-posterior", "ctx-inference", "diagnostic-use",
        Permission::DIA, gaps, profiles, vec![],
    );

    let kl_tok = bounding_token("tok-kl", vec!["g-calibration"], &ctx);
    let support_tok = closing_token("tok-support", vec!["g-support"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(kl_tok);
    ctx.tokens.push(support_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "P1: inference with KL bound must compile to DIA");
}

#[test]
fn p1_inference_without_calibration_bound_stays_ooc() {
    let gaps = vec![
        GapRecord::open("g-calibration", "calibration_gap"), // not bounded
        GapRecord::closed("g-support", "support_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-calibration".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            },
            GapRequirement {
                gap_id: "g-support".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p1-no-cal", "z-posterior-2", "ctx-inf-2", "diagnostic-use",
        Permission::DIA, gaps, profiles, vec![],
    );
    let support_tok = closing_token("tok-s2", vec!["g-support"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(support_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "P1: open calibration gap must block DIA profile"
    );
}

// ── P2: Off-policy evaluation / causal inference ──────────────────────────────
// Pre-registration:
//   IN_CLASS: yes
//   Gaps: proxy_gap (CLOSED), interference_gap (CLOSED)
//   Tokens: OPE certificate, coupling witness
//   Expected: REV (reversible action)

#[test]
fn p2_ope_causal_claim_compiles_to_rev() {
    let gaps = vec![
        GapRecord::closed("g-proxy", "proxy_gap"),
        GapRecord::closed("g-interference", "interference_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::REV,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-proxy".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-interference".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p2-claim", "z-ope", "ctx-causal", "ope-use",
        Permission::REV, gaps, profiles, vec![],
    );
    let ope_tok = closing_token("tok-ope", vec!["g-proxy", "g-interference"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(ope_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REV, "P2: OPE with coupling witness must compile to REV");
}

// ── P3: Marketplace allocation ────────────────────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes
//   Gaps: guardrail_gap (CLOSED), negative_control_gap (CLOSED)
//   Expected: ROL (role-limited automatic action)

#[test]
fn p3_marketplace_allocation_with_guardrail_compiles_to_rol() {
    let gaps = vec![
        GapRecord::closed("g-guardrail", "guardrail_gap"),
        GapRecord::closed("g-nc", "negative_control_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::ROL,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-guardrail".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-nc".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p3-claim", "z-marketplace", "ctx-mkt", "allocation-use",
        Permission::ROL, gaps, profiles, vec![],
    );
    let g_tok = closing_token("tok-guardrail", vec!["g-guardrail", "g-nc"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(g_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::ROL, "P3: marketplace with guardrail must compile to ROL");
}

// ── P4: Medical triage / clinical risk scoring ────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes (approximate risk score → clinical action)
//   Authority ceiling: DIA (diagnostic-only, no autonomous action)
//   Gaps: calibration_gap (BOUNDED), boundary_gap (CLOSED)
//   Expected: DIA

#[test]
fn p4_medical_triage_with_diagnostic_ceiling_compiles_to_dia() {
    let gaps = vec![
        GapRecord::bounded("g-cal", "calibration_gap", Bound::numeric(0.03)),
        GapRecord::closed("g-boundary", "boundary_gap"),
    ];
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![
                GapRequirement {
                    gap_id: "g-cal".into(),
                    minimum_status: RequiredStatus::BoundedRequired,
                },
                GapRequirement {
                    gap_id: "g-boundary".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
            ],
        },
        Profile {
            permission: Permission::AEX, // full auto — but authority_ceiling = DIA blocks this
            required_gaps: vec![
                GapRequirement {
                    gap_id: "g-cal".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
                GapRequirement {
                    gap_id: "g-boundary".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
            ],
        },
    ];

    let ctx = build_ctx(
        "p4-claim", "z-triage", "ctx-clinical", "triage-use",
        Permission::DIA, // ceiling: no autonomous clinical action
        gaps, profiles, vec![],
    );
    let kl_tok = bounding_token("tok-p4-kl", vec!["g-cal"], &ctx);
    let boundary_tok = closing_token("tok-p4-b", vec!["g-boundary"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(kl_tok);
    ctx.tokens.push(boundary_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "P4: medical triage must compile to DIA with ceiling");
    assert!(j.permission < Permission::AEX, "P4: AEX must be blocked by DIA ceiling");
}

// ── P5: Fraud and trust decisions ────────────────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes
//   Gaps: drift_gap (CLOSED), query_projection_gap (BOUNDED)
//   Expected: ESC (escalation — human review required)

#[test]
fn p5_fraud_score_with_drift_compiles_to_esc() {
    let gaps = vec![
        GapRecord::closed("g-drift", "drift_gap"),
        GapRecord::bounded("g-query", "query_projection_gap", Bound::infinity()),
    ];
    let profiles = vec![Profile {
        permission: Permission::ESC,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-drift".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-query".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p5-claim", "z-fraud", "ctx-trust", "fraud-use",
        Permission::ESC, gaps, profiles, vec![],
    );
    let drift_tok = closing_token("tok-drift", vec!["g-drift"], &ctx);
    let query_tok = bounding_token("tok-query", vec!["g-query"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(drift_tok);
    ctx.tokens.push(query_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::ESC, "P5: fraud score with bounded query gap must compile to ESC");
}

// ── P6: Cybersecurity response ────────────────────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes (threat score → quarantine/observe)
//   Gaps: truth_gap (CLOSED), rollback_gap (CLOSED)
//   Expected: ROL (role-limited automatic action)

#[test]
fn p6_cybersecurity_threat_with_rollback_compiles_to_rol() {
    let gaps = vec![
        GapRecord::closed("g-threat", "truth_gap"),
        GapRecord::closed("g-rollback", "rollback_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::ROL,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-threat".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-rollback".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p6-claim", "z-quarantine", "ctx-security", "security-use",
        Permission::ROL, gaps, profiles, vec![],
    );
    let tok = closing_token("tok-p6", vec!["g-threat", "g-rollback"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::ROL, "P6: cybersecurity with rollback must compile to ROL");
}

// ── P7: Trading and portfolio risk ────────────────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes (portfolio signal → position change/risk hold)
//   Gaps: missing_data_gap (BOUNDED), authority_gap (CLOSED)
//   Expected: ETA (estimate-only, capped by missing data)

#[test]
fn p7_trading_signal_with_missing_data_compiles_to_eta() {
    let gaps = vec![
        GapRecord::bounded("g-data", "missing_data_gap", Bound::infinity()),
        GapRecord::closed("g-authority", "authority_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::ETA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-data".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            },
            GapRequirement {
                gap_id: "g-authority".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p7-claim", "z-portfolio", "ctx-trading", "trading-use",
        Permission::ETA, gaps, profiles, vec![],
    );
    let data_tok = bounding_token("tok-data", vec!["g-data"], &ctx);
    let auth_tok = closing_token("tok-auth", vec!["g-authority"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(data_tok);
    ctx.tokens.push(auth_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::ETA, "P7: trading signal with missing data must compile to ETA");
}

// ── P8: LLM agent deployment decisions ───────────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes (LLM plan → execute/deploy/refuse)
//   Gaps: test_coverage_gap (CLOSED), execution_gap (CLOSED), rollback_gap (CLOSED)
//   Expected: AEX (automatic execution)

#[test]
fn p8_llm_agent_with_full_evidence_compiles_to_aex() {
    let gaps = vec![
        GapRecord::closed("g-coverage", "test_coverage_gap"),
        GapRecord::closed("g-execution", "execution_gap"),
        GapRecord::closed("g-rollback", "rollback_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::AEX,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-coverage".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-execution".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-rollback".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p8-claim", "z-deploy", "ctx-llm", "agent-deployment",
        Permission::AEX, gaps, profiles, vec![],
    );
    let tok = closing_token("tok-p8", vec!["g-coverage", "g-execution", "g-rollback"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::AEX, "P8: LLM agent with full evidence must compile to AEX");
}

#[test]
fn p8_llm_agent_with_missing_rollback_stays_below_aex() {
    let gaps = vec![
        GapRecord::closed("g-coverage", "test_coverage_gap"),
        GapRecord::closed("g-execution", "execution_gap"),
        GapRecord::open("g-rollback", "rollback_gap"), // missing!
    ];
    let profiles = vec![Profile {
        permission: Permission::AEX,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-coverage".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-execution".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-rollback".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p8-no-rb", "z-deploy-2", "ctx-llm-2", "agent-deployment",
        Permission::AEX, gaps, profiles, vec![],
    );
    let tok = closing_token("tok-p8b", vec!["g-coverage", "g-execution"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert!(
        j.permission < Permission::AEX,
        "P8: missing rollback gap must block AEX"
    );
}

// ── P9: Scientific simulation and surrogate modeling ─────────────────────────
// Pre-registration:
//   IN_CLASS: yes (surrogate model output → design decision)
//   Gaps: truth_gap (BOUNDED), boundary_gap (CLOSED)
//   Expected: DIA

#[test]
fn p9_scientific_surrogate_with_boundary_compiles_to_dia() {
    let gaps = vec![
        GapRecord::bounded("g-truth", "truth_gap", Bound::numeric(0.1)),
        GapRecord::closed("g-boundary", "boundary_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-truth".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            },
            GapRequirement {
                gap_id: "g-boundary".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p9-claim", "z-surrogate", "ctx-science", "simulation-use",
        Permission::DIA, gaps, profiles, vec![],
    );
    let truth_tok = bounding_token("tok-truth", vec!["g-truth"], &ctx);
    let boundary_tok = closing_token("tok-boundary", vec!["g-boundary"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(truth_tok);
    ctx.tokens.push(boundary_tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "P9: surrogate model with boundary must compile to DIA");
}

// ── P10: Resource-constrained planning ───────────────────────────────────────
// Pre-registration:
//   IN_CLASS: yes (constrained optimizer output → allocation decision)
//   Gaps: support_gap (CLOSED), composition_gap (CLOSED)
//   Expected: REV (reversible action)

#[test]
fn p10_constrained_planning_with_composition_gap_compiles_to_rev() {
    let gaps = vec![
        GapRecord::closed("g-support", "support_gap"),
        GapRecord::closed("g-composition", "composition_gap"),
    ];
    let profiles = vec![Profile {
        permission: Permission::REV,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g-support".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g-composition".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let ctx = build_ctx(
        "p10-claim", "z-planner", "ctx-planning", "planning-use",
        Permission::REV, gaps, profiles, vec![],
    );
    let tok = closing_token("tok-p10", vec!["g-support", "g-composition"], &ctx);
    let mut ctx = ctx;
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REV, "P10: constrained planner with full evidence must compile to REV");
}
