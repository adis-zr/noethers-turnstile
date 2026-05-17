/// The permission total order for EC-001.
///
/// Variants are listed OOC → AAA so that `#[derive(Ord)]` gives the correct
/// total order: OOC is the bottom element and AAA is the top element.
///
/// Meet = min.  Composition is non-promoting (meet of components).
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum Permission {
    /// Out-of-class — bottom of the lattice.
    OOC,
    /// Expired — token expiry blocks all advancement.
    EXP,
    /// Refused — evidence insufficient.
    REF,
    /// Unsupported — no applicable profile exists.
    UNS,
    /// Estimate-only action allowed.
    ETA,
    /// Escalation permitted.
    ESC,
    /// Role-limited automatic action.
    ROL,
    /// Diagnostic action.
    DIA,
    /// Reversible action.
    REV,
    /// Automatic execution permitted.
    AEX,
    /// Automated-and-logged action.
    ALR,
    /// Unrestricted (top of the lattice).
    AAA,
}

impl Permission {
    /// Meet (min) of two permissions in the total order.
    #[inline]
    pub fn meet(self, other: Self) -> Self {
        self.min(other)
    }

    /// Meet of an iterable of permissions.  Returns `None` if the iterator is empty.
    pub fn meet_n(perms: impl IntoIterator<Item = Self>) -> Option<Self> {
        perms.into_iter().reduce(Self::meet)
    }

    /// Iterator over all permission values from AAA down to OOC (descending order).
    pub fn descending() -> impl Iterator<Item = Self> {
        use Permission::*;
        [AAA, ALR, AEX, REV, DIA, ROL, ESC, ETA, UNS, REF, EXP, OOC]
            .iter()
            .copied()
    }

    /// Parse from a string (case-insensitive for the 3-letter codes).  Returns
    /// `None` for unknown strings.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_uppercase().as_str() {
            "OOC" => Some(Permission::OOC),
            "EXP" => Some(Permission::EXP),
            "REF" => Some(Permission::REF),
            "UNS" => Some(Permission::UNS),
            "ETA" => Some(Permission::ETA),
            "ESC" => Some(Permission::ESC),
            "ROL" => Some(Permission::ROL),
            "DIA" => Some(Permission::DIA),
            "REV" => Some(Permission::REV),
            "AEX" => Some(Permission::AEX),
            "ALR" => Some(Permission::ALR),
            "AAA" => Some(Permission::AAA),
            _ => None,
        }
    }

    /// Name as a static string.
    pub fn as_str(self) -> &'static str {
        match self {
            Permission::OOC => "OOC",
            Permission::EXP => "EXP",
            Permission::REF => "REF",
            Permission::UNS => "UNS",
            Permission::ETA => "ETA",
            Permission::ESC => "ESC",
            Permission::ROL => "ROL",
            Permission::DIA => "DIA",
            Permission::REV => "REV",
            Permission::AEX => "AEX",
            Permission::ALR => "ALR",
            Permission::AAA => "AAA",
        }
    }
}

impl std::fmt::Display for Permission {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn total_order_is_correct() {
        assert!(Permission::OOC < Permission::EXP);
        assert!(Permission::EXP < Permission::REF);
        assert!(Permission::REF < Permission::UNS);
        assert!(Permission::UNS < Permission::ETA);
        assert!(Permission::ETA < Permission::ESC);
        assert!(Permission::ESC < Permission::ROL);
        assert!(Permission::ROL < Permission::DIA);
        assert!(Permission::DIA < Permission::REV);
        assert!(Permission::REV < Permission::AEX);
        assert!(Permission::AEX < Permission::ALR);
        assert!(Permission::ALR < Permission::AAA);
    }

    #[test]
    fn meet_is_min() {
        assert_eq!(Permission::AAA.meet(Permission::OOC), Permission::OOC);
        assert_eq!(Permission::DIA.meet(Permission::REV), Permission::DIA);
        assert_eq!(Permission::EXP.meet(Permission::EXP), Permission::EXP);
    }

    #[test]
    fn meet_n_empty_is_none() {
        assert_eq!(Permission::meet_n(std::iter::empty()), None);
    }

    #[test]
    fn meet_n_singleton() {
        assert_eq!(
            Permission::meet_n(std::iter::once(Permission::DIA)),
            Some(Permission::DIA)
        );
    }

    #[test]
    fn descending_first_is_aaa() {
        let mut it = Permission::descending();
        assert_eq!(it.next(), Some(Permission::AAA));
    }

    #[test]
    fn descending_last_is_ooc() {
        let last = Permission::descending().last();
        assert_eq!(last, Some(Permission::OOC));
    }

    #[test]
    fn descending_has_all_12() {
        assert_eq!(Permission::descending().count(), 12);
    }

    #[test]
    fn round_trip_str() {
        for p in Permission::descending() {
            assert_eq!(Permission::from_str(p.as_str()), Some(p));
        }
    }
}
