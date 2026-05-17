/// EC-047 — Step 11 assembler truth table (T8/T11, EC-001 §30).
///
/// Ported from: test_ec003f_step11_assembler.py (16 explicit critical combinations)
///
/// The final permission assembly via meet_n respects a tier hierarchy:
///   OOC > EXP > [REF/UNS] > [ETA/ESC/ROL] > [DIA/REV/AEX/ALR/AAA]
///
/// Each test is pre-registered ("call-the-shots") with the expected outcome.
///
///   S1  — UNSUPPORTED + ETA → UNSUPPORTED (refusal tier > control tier)
///   S2  — UNSUPPORTED + ESC → UNSUPPORTED
///   S3  — AAA + REFUSED(REF) → REF
///   S4  — AAA + ETA → ETA (control ceiling)
///   S5  — AAA + REF + ETA → REF (refusal > control)
///   S6  — DIA + ROL → ROL (control > diagnostic)
///   S7  — EXP + ESC → EXP (expiry tier > control)
///   S8  — EXP + REF → EXP (expiry tier > refusal)
///   S9  — OOC + anything → OOC (absorbing element, 6 cases)
///   S10 — Control tier ordering: ETA > ESC > ROL
///   S11 — REF + ESC → REF (refusal > control)
///   S12 — AAA meet AEX → AEX (within approval tier)
///   S13 — REV meet DIA → DIA (within diagnostic tier, weaker wins)
///   S14 — All 12 idempotence cases: meet_n([p]) = p
///   S15 — All 3!=6 permutations of [OOC, ESC, AAA] → OOC
///   S16 — Cross-tier conflict matrix: UNS vs each tier
///   S17 — EXP absorbs all non-OOC tiers
///   S18 — OOC absorbs N-ary compose_n across all 12 values
use turnstile_core::permission::Permission;

const ALL: [Permission; 12] = [
    Permission::OOC,
    Permission::EXP,
    Permission::REF,
    Permission::UNS,
    Permission::ETA,
    Permission::ESC,
    Permission::ROL,
    Permission::DIA,
    Permission::REV,
    Permission::AEX,
    Permission::ALR,
    Permission::AAA,
];

// ── S1: UNSUPPORTED + ETA → UNSUPPORTED ──────────────────────────────────────

#[test]
fn s1_unsupported_plus_eta_is_unsupported() {
    // Refusal tier (UNS rank 3) > control tier (ETA rank 4)
    let result = Permission::meet_n([Permission::UNS, Permission::ETA]).unwrap();
    assert_eq!(result, Permission::UNS, "S1: UNS+ETA must be UNS");
}

// ── S2: UNSUPPORTED + ESC → UNSUPPORTED ──────────────────────────────────────

#[test]
fn s2_unsupported_plus_esc_is_unsupported() {
    let result = Permission::meet_n([Permission::UNS, Permission::ESC]).unwrap();
    assert_eq!(result, Permission::UNS, "S2: UNS+ESC must be UNS");
}

// ── S3: AAA + REF → REF (refusal wins over approval) ─────────────────────────

#[test]
fn s3_aaa_plus_ref_is_ref() {
    let result = Permission::meet_n([Permission::AAA, Permission::REF]).unwrap();
    assert_eq!(result, Permission::REF, "S3: AAA+REF must be REF");
}

// ── S4: AAA + ETA → ETA (control ceiling) ────────────────────────────────────

#[test]
fn s4_aaa_plus_eta_is_eta() {
    let result = Permission::meet_n([Permission::AAA, Permission::ETA]).unwrap();
    assert_eq!(result, Permission::ETA, "S4: AAA+ETA must be ETA");
}

// ── S5: AAA + REF + ETA → REF (refusal > control) ────────────────────────────

#[test]
fn s5_aaa_plus_ref_plus_eta_is_ref() {
    let result =
        Permission::meet_n([Permission::AAA, Permission::REF, Permission::ETA]).unwrap();
    assert_eq!(result, Permission::REF, "S5: AAA+REF+ETA must be REF");
}

// ── S6: DIA + ROL → ROL (control > diagnostic) ───────────────────────────────

#[test]
fn s6_dia_plus_rol_is_rol() {
    let result = Permission::meet_n([Permission::DIA, Permission::ROL]).unwrap();
    assert_eq!(result, Permission::ROL, "S6: DIA+ROL must be ROL");
}

// ── S7: EXP + ESC → EXP (expiry > control) ───────────────────────────────────

#[test]
fn s7_exp_plus_esc_is_exp() {
    let result = Permission::meet_n([Permission::EXP, Permission::ESC]).unwrap();
    assert_eq!(result, Permission::EXP, "S7: EXP+ESC must be EXP");
}

// ── S8: EXP + REF → EXP (expiry > refusal) ───────────────────────────────────

#[test]
fn s8_exp_plus_ref_is_exp() {
    let result = Permission::meet_n([Permission::EXP, Permission::REF]).unwrap();
    assert_eq!(result, Permission::EXP, "S8: EXP+REF must be EXP");
}

// ── S9: OOC + anything → OOC (6 representative cases) ───────────────────────

#[test]
fn s9_ooc_absorbs_all_six_representative_cases() {
    let cases = [
        Permission::ESC,
        Permission::ROL,
        Permission::AAA,
        Permission::DIA,
        Permission::REF,
        Permission::EXP,
    ];
    for p in cases {
        let result = Permission::meet_n([Permission::OOC, p]).unwrap();
        assert_eq!(result, Permission::OOC, "S9: OOC+{p:?} must be OOC");
    }
}

// ── S10: Control tier ordering: ETA < ESC < ROL in the lattice ───────────────

#[test]
fn s10_control_tier_ordering() {
    // Lattice order: OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < ...
    // So meet(p, q) = min(p, q); ETA is the weakest control tier element.
    assert_eq!(
        Permission::ETA.meet(Permission::ESC),
        Permission::ETA,
        "S10: meet(ETA, ESC) must be ETA (ETA < ESC in lattice)"
    );
    assert_eq!(
        Permission::ESC.meet(Permission::ROL),
        Permission::ESC,
        "S10: meet(ESC, ROL) must be ESC (ESC < ROL in lattice)"
    );
    assert_eq!(
        Permission::ETA.meet(Permission::ROL),
        Permission::ETA,
        "S10: meet(ETA, ROL) must be ETA (ETA < ROL in lattice)"
    );
}

// ── S11: REF + ESC → REF (refusal > control) ─────────────────────────────────

#[test]
fn s11_ref_plus_esc_is_ref() {
    let result = Permission::meet_n([Permission::REF, Permission::ESC]).unwrap();
    assert_eq!(result, Permission::REF, "S11: REF+ESC must be REF");
}

// ── S12: AAA meet AEX → AEX (within approval tier) ───────────────────────────

#[test]
fn s12_aaa_meet_aex_is_aex() {
    assert_eq!(
        Permission::AAA.meet(Permission::AEX),
        Permission::AEX,
        "S12: meet(AAA, AEX) must be AEX"
    );
}

// ── S13: REV meet DIA → DIA (within diagnostic tier, weaker wins) ─────────────

#[test]
fn s13_rev_meet_dia_is_dia() {
    assert_eq!(
        Permission::REV.meet(Permission::DIA),
        Permission::DIA,
        "S13: meet(REV, DIA) must be DIA"
    );
}

// ── S14: All 12 idempotence cases ────────────────────────────────────────────

#[test]
fn s14_idempotence_all_12_permissions() {
    for &p in &ALL {
        let result = Permission::meet_n([p]).unwrap();
        assert_eq!(result, p, "S14: meet_n([{p:?}]) must equal {p:?}");
    }
}

// ── S15: All 6 permutations of [OOC, ESC, AAA] → OOC ─────────────────────────

#[test]
fn s15_all_6_permutations_ooc_esc_aaa_yield_ooc() {
    let perms = [
        [Permission::OOC, Permission::ESC, Permission::AAA],
        [Permission::OOC, Permission::AAA, Permission::ESC],
        [Permission::ESC, Permission::OOC, Permission::AAA],
        [Permission::ESC, Permission::AAA, Permission::OOC],
        [Permission::AAA, Permission::OOC, Permission::ESC],
        [Permission::AAA, Permission::ESC, Permission::OOC],
    ];
    for perm in perms {
        let result = Permission::meet_n(perm).unwrap();
        assert_eq!(
            result,
            Permission::OOC,
            "S15: any permutation of [OOC, ESC, AAA] must yield OOC"
        );
    }
}

// ── S16: Cross-tier conflict matrix: UNS vs each other permission ─────────────

#[test]
fn s16_uns_beats_every_higher_tier() {
    // UNS is in refusal tier; it beats everything except OOC and EXP
    let uns_beats = [
        Permission::ETA,
        Permission::ESC,
        Permission::ROL,
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::ALR,
        Permission::AAA,
    ];
    for &p in &uns_beats {
        let result = Permission::UNS.meet(p);
        assert_eq!(result, Permission::UNS, "S16: UNS.meet({p:?}) must be UNS");
    }

    // OOC and EXP beat UNS
    assert_eq!(
        Permission::UNS.meet(Permission::OOC),
        Permission::OOC,
        "S16: UNS.meet(OOC) must be OOC"
    );
    assert_eq!(
        Permission::UNS.meet(Permission::EXP),
        Permission::EXP,
        "S16: UNS.meet(EXP) must be EXP"
    );
}

// ── S17: EXP absorbs all non-OOC permissions ──────────────────────────────────

#[test]
fn s17_exp_absorbs_all_non_ooc() {
    for &p in &ALL {
        if p == Permission::OOC {
            // OOC beats EXP
            assert_eq!(
                Permission::EXP.meet(p),
                Permission::OOC,
                "S17: EXP.meet(OOC) must be OOC"
            );
        } else {
            assert_eq!(
                Permission::EXP.meet(p),
                Permission::EXP,
                "S17: EXP.meet({p:?}) must be EXP"
            );
        }
    }
}

// ── S18: OOC absorbs meet_n across all 12 values ─────────────────────────────

#[test]
fn s18_ooc_absorbs_meet_n_of_all_12() {
    // meet_n of all 12 permissions (including OOC) must be OOC
    let result = Permission::meet_n(ALL).unwrap();
    assert_eq!(result, Permission::OOC, "S18: meet_n of all 12 must be OOC");
}

#[test]
fn s18_ooc_at_end_still_absorbs() {
    // OOC at last position in meet_n still wins
    let result = Permission::meet_n([
        Permission::AAA,
        Permission::ALR,
        Permission::AEX,
        Permission::REV,
        Permission::DIA,
        Permission::ROL,
        Permission::ESC,
        Permission::ETA,
        Permission::UNS,
        Permission::REF,
        Permission::EXP,
        Permission::OOC,
    ])
    .unwrap();
    assert_eq!(
        result,
        Permission::OOC,
        "S18: OOC at end of meet_n must still absorb"
    );
}
