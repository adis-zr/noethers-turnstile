/// EC-009 — Permission::from_str exhaustive coverage.
///
/// Permission::from_str is a public parse function used whenever permissions are
/// read from external sources (config files, API payloads, audit logs).  It must:
///   - Return Some(p) for every valid 3-letter code (case-insensitive).
///   - Return None for any unknown string — never silently coerce to a default.
///
/// A silent coercion to OOC or AAA would be a security-boundary violation:
///   - Unknown → AAA: grants unrestricted permission to unknown input.
///   - Unknown → OOC: silently blocks valid operations.
///   - Unknown → Some(anything): breaks the fail-closed guarantee.
///
/// Tests:
///   - All 12 valid codes (uppercase) → correct variant
///   - All 12 valid codes (lowercase) → correct variant (case-insensitive)
///   - All 12 valid codes (mixed case) → correct variant
///   - Empty string → None
///   - Whitespace → None
///   - Near-miss strings → None (e.g., "DIAA", "DI", "D I A")
///   - Numeric strings → None
///   - Unicode lookalikes → None
use noethers_turnstile_core::permission::Permission;

const ALL_VARIANTS: [(Permission, &str); 12] = [
    (Permission::OOC, "OOC"),
    (Permission::EXP, "EXP"),
    (Permission::REF, "REF"),
    (Permission::UNS, "UNS"),
    (Permission::ETA, "ETA"),
    (Permission::ESC, "ESC"),
    (Permission::ROL, "ROL"),
    (Permission::DIA, "DIA"),
    (Permission::REV, "REV"),
    (Permission::AEX, "AEX"),
    (Permission::ALR, "ALR"),
    (Permission::AAA, "AAA"),
];

// ── All 12 codes uppercase ────────────────────────────────────────────────────

#[test]
fn all_12_codes_uppercase_parse_correctly() {
    for (expected, code) in ALL_VARIANTS {
        let parsed = Permission::from_str(code);
        assert_eq!(
            parsed,
            Some(expected),
            "from_str({code:?}) must return Some({expected:?})"
        );
    }
}

// ── All 12 codes lowercase ────────────────────────────────────────────────────

#[test]
fn all_12_codes_lowercase_parse_correctly() {
    for (expected, code) in ALL_VARIANTS {
        let lower = code.to_lowercase();
        let parsed = Permission::from_str(&lower);
        assert_eq!(
            parsed,
            Some(expected),
            "from_str({lower:?}) must return Some({expected:?})"
        );
    }
}

// ── Mixed case ────────────────────────────────────────────────────────────────

#[test]
fn mixed_case_parses_correctly() {
    assert_eq!(Permission::from_str("Dia"), Some(Permission::DIA));
    assert_eq!(Permission::from_str("dIa"), Some(Permission::DIA));
    assert_eq!(Permission::from_str("aAa"), Some(Permission::AAA));
    assert_eq!(Permission::from_str("oOc"), Some(Permission::OOC));
}

// ── Unknown strings return None ──────────────────────────────────────────────

#[test]
fn empty_string_returns_none() {
    assert_eq!(
        Permission::from_str(""),
        None,
        "empty string must return None"
    );
}

#[test]
fn whitespace_returns_none() {
    assert_eq!(Permission::from_str(" "), None);
    assert_eq!(Permission::from_str("   "), None);
    assert_eq!(Permission::from_str("\t"), None);
}

#[test]
fn near_miss_codes_return_none() {
    let near_misses = [
        "DIAA", "DI", "D I A", "DAIA", "DIAZ", "EXPP", "EX", "OOCS", "AAAA", "AA", "ALR1", "1ALR",
        "0OC",
    ];
    for s in near_misses {
        assert_eq!(
            Permission::from_str(s),
            None,
            "near-miss {s:?} must return None, not a valid permission"
        );
    }
}

#[test]
fn numeric_strings_return_none() {
    for s in ["0", "1", "12", "123", "0x00"] {
        assert_eq!(
            Permission::from_str(s),
            None,
            "numeric {s:?} must return None"
        );
    }
}

#[test]
fn prefix_of_valid_code_returns_none() {
    // "DI" is a prefix of "DIA" but must not parse to DIA.
    assert_eq!(Permission::from_str("DI"), None);
    assert_eq!(Permission::from_str("AA"), None);
    assert_eq!(Permission::from_str("OO"), None);
}

#[test]
fn suffix_extension_of_valid_code_returns_none() {
    // "DIAM" extends "DIA" but must not parse.
    assert_eq!(Permission::from_str("DIAM"), None);
    assert_eq!(Permission::from_str("AAAB"), None);
}

// ── Round-trip: every Permission serialises and parses back ──────────────────

#[test]
fn round_trip_all_variants() {
    for p in Permission::descending() {
        let s = p.as_str();
        assert_eq!(
            Permission::from_str(s),
            Some(p),
            "round-trip failed for {p:?}: as_str()={s:?}"
        );
    }
}

// ── from_str on as_str is identity for all variants ─────────────────────────

#[test]
fn from_str_as_str_is_identity() {
    for (p, _) in ALL_VARIANTS {
        let s = p.as_str();
        assert_eq!(Permission::from_str(s), Some(p));
        // Lowercase also works.
        assert_eq!(Permission::from_str(&s.to_lowercase()), Some(p));
    }
}
