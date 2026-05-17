/// EC-034 — Permission tier semantics and action-set interpretation (EC-001 §16–20).
///
/// EC-001 §16–20 defines a priority tier table with five tiers and specifies
/// which outcomes license action vs. license nothing.  This suite verifies
/// that the total order on Permission correctly encodes those tiers and that
/// the meet operator preserves tier semantics.
///
/// Coverage areas:
///   T1  — Out-of-class tier (tier 5) absorbs everything
///   T2  — Expiry tier (tier 4) dominates approval/control/diagnostic
///   T3  — Refusal tier (tier 3) dominates control and approval
///   T4  — Control tier (tier 2) encodes ROL/ESC as non-action outcomes
///   T5  — Diagnostic tier (tier 1): DIA licenses no automatic action
///   T6  — Approval tier (tier 0): AEX/ALR/AAA are positive action outcomes
///   T7  — Cross-tier meet always selects the higher tier
///   T8  — Within approval chain: meet = greatest lower bound
///   T9  — Action set interpretation via non-promotion law
///   T10 — Tier 5 (OOC) is absorbing in the meet operator
use turnstile_core::permission::Permission;

// ── T1: OOC is absorbing ──────────────────────────────────────────────────────

#[test]
fn t1_ooc_meets_every_permission_to_ooc() {
    for p in Permission::descending() {
        assert_eq!(
            Permission::OOC.meet(p),
            Permission::OOC,
            "OOC.meet({p}) must be OOC"
        );
        assert_eq!(
            p.meet(Permission::OOC),
            Permission::OOC,
            "{p}.meet(OOC) must be OOC"
        );
    }
}

// ── T2: EXP dominates all positive/diagnostic/control outcomes ─────────────

#[test]
fn t2_exp_dominates_approval_and_diagnostic() {
    let approval = [
        Permission::AEX, Permission::ALR, Permission::AAA, Permission::REV,
    ];
    let diagnostic = [Permission::DIA];
    let control = [Permission::ROL, Permission::ESC];
    let refusal = [Permission::REF, Permission::UNS];

    for &p in approval.iter().chain(diagnostic.iter()).chain(control.iter()).chain(refusal.iter()) {
        let m = Permission::EXP.meet(p);
        assert!(
            m <= Permission::EXP,
            "EXP.meet({p}) = {m} must be ≤ EXP (EXP dominates higher tiers)"
        );
    }
}

// ── T3: REF and UNS dominate approval/control/diagnostic ─────────────────────

#[test]
fn t3_ref_dominates_approval_and_control() {
    let dominated = [
        Permission::DIA,
        Permission::ROL,
        Permission::ESC,
        Permission::ETA,
        Permission::REV,
        Permission::AEX,
        Permission::ALR,
        Permission::AAA,
    ];

    for &p in &dominated {
        let m = Permission::REF.meet(p);
        assert!(
            m <= Permission::REF,
            "REF.meet({p}) = {m}: result must be ≤ REF"
        );
    }
}

#[test]
fn t3_uns_dominates_approval_tier() {
    let approval = [Permission::REV, Permission::AEX, Permission::ALR, Permission::AAA];
    for &p in &approval {
        let m = Permission::UNS.meet(p);
        assert!(m <= Permission::UNS, "UNS.meet({p}) must be ≤ UNS");
    }
}

// ── T4: ROL and ESC are below DIA — they license no positive action ───────────
// (In turnstile's total order: OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA)

#[test]
fn t4_rol_and_esc_are_below_dia() {
    assert!(Permission::ROL < Permission::DIA, "ROL must be below DIA");
    assert!(Permission::ESC < Permission::DIA, "ESC must be below DIA");
}

#[test]
fn t4_eta_is_below_esc() {
    assert!(Permission::ETA < Permission::ESC, "ETA must be below ESC");
}

// ── T5: DIA is the boundary between action and non-action ────────────────────
// Action permissions (REV, AEX, ALR, AAA) are all above DIA.
// Non-action (OOC, EXP, REF, UNS, ETA, ESC, ROL) are all below or at DIA.

#[test]
fn t5_dia_separates_action_from_non_action() {
    let action_permissions = [Permission::REV, Permission::AEX, Permission::ALR, Permission::AAA];
    let non_action_permissions = [
        Permission::OOC, Permission::EXP, Permission::REF,
        Permission::UNS, Permission::ETA, Permission::ESC, Permission::ROL,
    ];

    for &p in &action_permissions {
        assert!(p > Permission::DIA, "{p} must be above DIA (action permission)");
    }
    for &p in &non_action_permissions {
        assert!(p <= Permission::DIA, "{p} must be at or below DIA (non-action)");
    }
}

// ── T6: AEX, ALR, AAA are positive action outcomes ───────────────────────────

#[test]
fn t6_action_permissions_are_above_rev() {
    assert!(Permission::AEX > Permission::REV, "AEX must be above REV");
    assert!(Permission::ALR > Permission::AEX, "ALR must be above AEX");
    assert!(Permission::AAA > Permission::ALR, "AAA must be above ALR");
}

#[test]
fn t6_rev_is_minimum_action_permission() {
    // REV is the lowest action-level permission
    assert!(Permission::REV > Permission::DIA, "REV must be above DIA");
    assert!(Permission::REV < Permission::AEX, "REV must be below AEX");
}

// ── T7: Cross-tier meet always returns the lower-tier value ──────────────────

#[test]
fn t7_cross_tier_meet_returns_lower_tier() {
    // Tier 5 (OOC) vs tier 4 (EXP): OOC wins
    assert_eq!(Permission::OOC.meet(Permission::EXP), Permission::OOC);
    // Tier 4 (EXP) vs tier 0 (AAA): EXP wins
    assert_eq!(Permission::EXP.meet(Permission::AAA), Permission::EXP);
    // Tier 3 (REF) vs tier 0 (AEX): REF wins
    assert_eq!(Permission::REF.meet(Permission::AEX), Permission::REF);
    // Tier 3 (UNS) vs tier 1 (DIA): UNS wins
    assert_eq!(Permission::UNS.meet(Permission::DIA), Permission::UNS);
    // Tier 2 (ROL) vs tier 0 (REV): ROL wins (ROL < REV in total order → meet = ROL)
    assert_eq!(Permission::ROL.meet(Permission::REV), Permission::ROL);
}

// ── T8: Within approval chain, meet is greatest lower bound ──────────────────

#[test]
fn t8_approval_chain_meet_is_lower_bound() {
    // AAA ∧ ALR = ALR
    assert_eq!(Permission::AAA.meet(Permission::ALR), Permission::ALR);
    // ALR ∧ AEX = AEX
    assert_eq!(Permission::ALR.meet(Permission::AEX), Permission::AEX);
    // AEX ∧ REV = REV
    assert_eq!(Permission::AEX.meet(Permission::REV), Permission::REV);
    // REV ∧ DIA = DIA (DIA is below REV in total order)
    assert_eq!(Permission::REV.meet(Permission::DIA), Permission::DIA);
}

// ── T9: Non-promotion law via total order ────────────────────────────────────

#[test]
fn t9_meet_never_promotes() {
    let all: Vec<Permission> = Permission::descending().collect();
    for (i, &p) in all.iter().enumerate() {
        for &q in &all[i..] {
            let m = p.meet(q);
            assert!(
                m <= p,
                "meet({p}, {q}) = {m}: must be ≤ {p}"
            );
            assert!(
                m <= q,
                "meet({p}, {q}) = {m}: must be ≤ {q}"
            );
        }
    }
}

// ── T10: meet_n on all 12 values produces OOC ────────────────────────────────

#[test]
fn t10_meet_n_over_all_permissions_produces_ooc() {
    let all: Vec<Permission> = Permission::descending().collect();
    let result = Permission::meet_n(all.iter().copied()).unwrap();
    assert_eq!(result, Permission::OOC, "meet_n of all permissions must be OOC (bottom)");
}

#[test]
fn t10_meet_n_identity_element() {
    // meet_n of single AAA is AAA
    assert_eq!(
        Permission::meet_n(std::iter::once(Permission::AAA)),
        Some(Permission::AAA)
    );
}

#[test]
fn t10_meet_n_empty_is_none() {
    assert_eq!(Permission::meet_n(std::iter::empty()), None);
}

// ── Full 12×12 meet exhaustiveness ───────────────────────────────────────────

#[test]
fn all_144_meet_pairs_are_non_promoting() {
    let all: Vec<Permission> = Permission::descending().collect();
    let mut checked = 0_u32;
    for &p in &all {
        for &q in &all {
            let m = p.meet(q);
            assert!(m <= p, "meet({p},{q})={m} promotes above {p}");
            assert!(m <= q, "meet({p},{q})={m} promotes above {q}");
            checked += 1;
        }
    }
    assert_eq!(checked, 144, "must check all 144 pairs");
}

// ── Commutativity of meet ─────────────────────────────────────────────────────

#[test]
fn meet_is_commutative_exhaustive() {
    let all: Vec<Permission> = Permission::descending().collect();
    for &p in &all {
        for &q in &all {
            assert_eq!(
                p.meet(q),
                q.meet(p),
                "meet({p},{q}) must equal meet({q},{p})"
            );
        }
    }
}

// ── Associativity of meet ─────────────────────────────────────────────────────

#[test]
fn meet_is_associative_spot_check() {
    let triples = [
        (Permission::AAA, Permission::DIA, Permission::REF),
        (Permission::AEX, Permission::ROL, Permission::EXP),
        (Permission::ALR, Permission::OOC, Permission::UNS),
        (Permission::REV, Permission::ETA, Permission::ESC),
    ];
    for (a, b, c) in triples {
        let lhs = a.meet(b).meet(c);
        let rhs = a.meet(b.meet(c));
        assert_eq!(lhs, rhs, "meet({a},{b},{c}): associativity failed");
    }
}

// ── Idempotence of meet ────────────────────────────────────────────────────────

#[test]
fn meet_is_idempotent_all_12() {
    for p in Permission::descending() {
        assert_eq!(p.meet(p), p, "meet({p},{p}) must equal {p}");
    }
}
