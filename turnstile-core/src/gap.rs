/// Gap types: GapStatus, GapRecord, GapSet, Profile, GapRequirement.
use serde::{Deserialize, Serialize};

use crate::permission::Permission;

/// Numeric or set-valued bound on a gap.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "value")]
pub enum BoundKind {
    /// A finite numeric bound (e.g. KL-divergence ≤ 0.05).
    Numeric(f64),
    /// A set-valued bound (e.g. allowed tool names).
    SetValued(Vec<String>),
    /// Conceptually unbounded — the gap is acknowledged but not quantified.
    Infinity,
}

/// A structured bound on a gap.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Bound {
    pub kind: BoundKind,
    pub units: Option<String>,
}

impl Bound {
    pub fn numeric(value: f64) -> Self {
        Self { kind: BoundKind::Numeric(value), units: None }
    }

    pub fn numeric_with_units(value: f64, units: impl Into<String>) -> Self {
        Self { kind: BoundKind::Numeric(value), units: Some(units.into()) }
    }

    pub fn set_valued(values: Vec<String>) -> Self {
        Self { kind: BoundKind::SetValued(values), units: None }
    }

    pub fn infinity() -> Self {
        Self { kind: BoundKind::Infinity, units: None }
    }
}

/// Status of a single gap in the proof context.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "status", content = "bound")]
pub enum GapStatus {
    /// No evidence has been supplied for this gap.
    Open,
    /// The gap has been bounded but not fully closed.
    Bounded(Bound),
    /// The gap has been fully discharged.
    Closed,
}

impl GapStatus {
    /// Total order rank: Open < Bounded < Closed.
    pub fn rank(&self) -> u8 {
        match self {
            GapStatus::Open => 0,
            GapStatus::Bounded(_) => 1,
            GapStatus::Closed => 2,
        }
    }

    /// Returns the minimum status (worst-case when composing).
    pub fn min_status(self, other: Self) -> Self {
        if self.rank() <= other.rank() { self } else { other }
    }
}

/// A single gap record in a proof context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GapRecord {
    /// Unique gap identifier within this context.
    pub gap_id: String,
    /// The gap type (e.g. "calibration_gap", "freshness_gap").
    pub gap_type: String,
    /// Current status of this gap.
    pub status: GapStatus,
}

impl GapRecord {
    pub fn open(gap_id: impl Into<String>, gap_type: impl Into<String>) -> Self {
        Self {
            gap_id: gap_id.into(),
            gap_type: gap_type.into(),
            status: GapStatus::Open,
        }
    }

    pub fn bounded(
        gap_id: impl Into<String>,
        gap_type: impl Into<String>,
        bound: Bound,
    ) -> Self {
        Self {
            gap_id: gap_id.into(),
            gap_type: gap_type.into(),
            status: GapStatus::Bounded(bound),
        }
    }

    pub fn closed(gap_id: impl Into<String>, gap_type: impl Into<String>) -> Self {
        Self {
            gap_id: gap_id.into(),
            gap_type: gap_type.into(),
            status: GapStatus::Closed,
        }
    }
}

/// Minimum status required by a profile for a given gap.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RequiredStatus {
    /// Gap must be at least Bounded (Bounded or Closed).
    BoundedRequired,
    /// Gap must be fully Closed.
    ClosedRequired,
}

impl RequiredStatus {
    /// Check whether an actual GapStatus satisfies this requirement.
    pub fn satisfied_by(self, status: &GapStatus) -> bool {
        match self {
            RequiredStatus::BoundedRequired => {
                matches!(status, GapStatus::Bounded(_) | GapStatus::Closed)
            }
            RequiredStatus::ClosedRequired => matches!(status, GapStatus::Closed),
        }
    }
}

/// A single gap requirement within a profile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GapRequirement {
    /// The gap_id this requirement applies to.
    pub gap_id: String,
    /// The minimum status required.
    pub minimum_status: RequiredStatus,
}

/// A permission profile: the set of gap requirements that must be met for a
/// given permission level to be emitted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Profile {
    /// The permission this profile unlocks.
    pub permission: Permission,
    /// Gap requirements that must all be satisfied.
    pub required_gaps: Vec<GapRequirement>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn required_status_bounded_accepts_bounded_and_closed() {
        let bound = Bound::numeric(0.05);
        assert!(RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Bounded(bound.clone())));
        assert!(RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Closed));
        assert!(!RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Open));
    }

    #[test]
    fn required_status_closed_only_accepts_closed() {
        let bound = Bound::numeric(0.05);
        assert!(!RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Bounded(bound)));
        assert!(RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Closed));
        assert!(!RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Open));
    }

    #[test]
    fn gap_status_min() {
        assert_eq!(
            GapStatus::Open.min_status(GapStatus::Closed).rank(),
            GapStatus::Open.rank()
        );
        assert_eq!(
            GapStatus::Closed.min_status(GapStatus::Bounded(Bound::numeric(1.0))).rank(),
            GapStatus::Bounded(Bound::numeric(1.0)).rank()
        );
    }
}
