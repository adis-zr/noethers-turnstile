//! Default-chain level constants — for TESTS, EXAMPLES, and the Python binding only.
//!
//! Library code in `compiler.rs` and `composition.rs` MUST NOT import this module.
//! Use `chain.role(ChainRole::X)` instead. The CI grep gates (see
//! `docs/specs/permission_chain_refactor_spec.md` §7.7) enforce this.
//!
//! Constants here are accessor functions that return owned `Permission` values
//! (each named level is cloned from a one-time-initialized cell). The function
//! form (rather than `static` of `Permission`) keeps the API stable across Rust
//! version changes and avoids exposing a non-`Copy` `Permission` as a static.

use std::sync::OnceLock;

use crate::permission::{Permission, PermissionChain};

fn level(name: &'static str) -> Permission {
    PermissionChain::default_chain()
        .parse(name)
        .unwrap_or_else(|| panic!("default chain missing level {:?}", name))
}

// Each accessor caches the parsed level so repeated calls are O(1). Permission
// is Copy, so the returned value is a cheap pointer copy.
macro_rules! level_fn {
    ($name:ident, $literal:expr) => {
        #[allow(non_snake_case)]
        pub fn $name() -> Permission {
            static CACHE: OnceLock<Permission> = OnceLock::new();
            *CACHE.get_or_init(|| level($literal))
        }
    };
}

level_fn!(OOC, "OOC");
level_fn!(EXP, "EXP");
level_fn!(REF, "REF");
level_fn!(UNS, "UNS");
level_fn!(ETA, "ETA");
level_fn!(ESC, "ESC");
level_fn!(ROL, "ROL");
level_fn!(DIA, "DIA");
level_fn!(REV, "REV");
level_fn!(AEX, "AEX");
level_fn!(ALR, "ALR");
level_fn!(AAA, "AAA");

// Default-chain named-level associated functions on `Permission` itself —
// `Permission::DIA()` etc. — so test code can keep the historical syntax.
// Library code in compile() / compose() MUST NOT use these; it goes through
// chain.role(...) instead. CI Gate 1 enforces.
macro_rules! permission_assoc {
    ($name:ident, $literal:expr) => {
        impl Permission {
            #[allow(non_snake_case)]
            pub fn $name() -> Permission {
                level($literal)
            }
        }
    };
}

permission_assoc!(OOC, "OOC");
permission_assoc!(EXP, "EXP");
permission_assoc!(REF, "REF");
permission_assoc!(UNS, "UNS");
permission_assoc!(ETA, "ETA");
permission_assoc!(ESC, "ESC");
permission_assoc!(ROL, "ROL");
permission_assoc!(DIA, "DIA");
permission_assoc!(REV, "REV");
permission_assoc!(AEX, "AEX");
permission_assoc!(ALR, "ALR");
permission_assoc!(AAA, "AAA");

/// Top of the default chain. Convenience alias for `AAA()`. Useful as a default
/// for `Option<Permission>` fields where `None` means "no ceiling".
pub fn top() -> Permission {
    AAA()
}

// -----------------------------------------------------------------------------
// Test/example convenience: default-chain ordering and meet
// -----------------------------------------------------------------------------
//
// These helpers exist so test code can compare and meet levels without
// threading the default chain everywhere. Library code in compiler.rs /
// composition.rs MUST NOT use these — see CI Gate 1.

/// Compare two levels under the default chain's order. Panics if either is
/// not in the default chain.
pub fn cmp(a: &Permission, b: &Permission) -> std::cmp::Ordering {
    PermissionChain::default_chain()
        .cmp(a, b)
        .unwrap_or_else(|| panic!("level not in default chain: {} or {}", a, b))
}

/// `a <= b` under the default chain's order.
pub fn le(a: &Permission, b: &Permission) -> bool {
    cmp(a, b) != std::cmp::Ordering::Greater
}

/// `a < b` under the default chain's order.
pub fn lt(a: &Permission, b: &Permission) -> bool {
    cmp(a, b) == std::cmp::Ordering::Less
}

/// Meet (min) under the default chain's order.
pub fn meet(a: &Permission, b: &Permission) -> Permission {
    PermissionChain::default_chain()
        .meet(a, b)
        .expect("default chain meet failed")
}

/// Meet of an iterator of levels. `None` if the iterator is empty.
pub fn meet_n<I>(iter: I) -> Option<Permission>
where
    I: IntoIterator<Item = Permission>,
{
    iter.into_iter().reduce(|a, b| meet(&a, &b))
}

/// All twelve default levels, ordered OOC..AAA.
pub fn ascending() -> [Permission; 12] {
    [
        OOC(), EXP(), REF(), UNS(), ETA(), ESC(), ROL(), DIA(), REV(), AEX(), ALR(), AAA(),
    ]
}

/// All twelve default levels, ordered AAA..OOC.
pub fn descending() -> [Permission; 12] {
    [
        AAA(), ALR(), AEX(), REV(), DIA(), ROL(), ESC(), ETA(), UNS(), REF(), EXP(), OOC(),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_default_levels_parse() {
        for f in [OOC, EXP, REF, UNS, ETA, ESC, ROL, DIA, REV, AEX, ALR, AAA] {
            let p = f();
            assert!(PermissionChain::default_chain().contains(&p));
        }
    }

    #[test]
    fn default_levels_distinct() {
        let levels = [
            OOC(), EXP(), REF(), UNS(), ETA(), ESC(), ROL(), DIA(), REV(), AEX(), ALR(), AAA(),
        ];
        let mut names: Vec<&str> = levels.iter().map(|p| p.as_str()).collect();
        names.sort();
        names.dedup();
        assert_eq!(names.len(), 12);
    }

    #[test]
    fn round_trip_via_chain_parse() {
        let chain = PermissionChain::default_chain();
        for f in [OOC, EXP, REF, UNS, ETA, ESC, ROL, DIA, REV, AEX, ALR, AAA] {
            let p = f();
            let reparsed = chain.parse(p.as_str()).unwrap();
            assert_eq!(p, reparsed);
        }
    }
}
