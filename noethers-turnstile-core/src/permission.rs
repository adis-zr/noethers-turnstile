//! Permission levels, chains, and chain identity.
//!
//! The compiler is parameterized over a `PermissionChain`: a validated, ordered
//! list of named levels plus a mapping from `ChainRole` → level. The default
//! chain (the historical 12-level OOC..AAA) lives at [`PermissionChain::default_chain`].
//!
//! See `docs/specs/permission_chain_refactor_spec.md` for the full rules.

use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// A named permission level. Identity is the (case-sensitive) name string.
///
/// `Permission` is `Copy`: the inner name is always an interned `&'static str`
/// pointer. Default-chain literals are static strings; runtime-constructed
/// names are interned on first use via a global string-intern table.
///
/// Display, serde, comparison-for-equality all key off the name. Order is NOT
/// carried by the level itself — it is carried by the [`PermissionChain`] that
/// contains it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Permission {
    name: &'static str,
}

impl Serialize for Permission {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(self.name)
    }
}

impl<'de> Deserialize<'de> for Permission {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        Ok(Permission::new(s))
    }
}

/// Global string intern table. Names are leaked as `&'static str` on first
/// insertion. Bounded by the number of distinct permission names a process
/// ever sees — in practice <100 even for stress tests.
static INTERN: OnceLock<Mutex<HashMap<String, &'static str>>> = OnceLock::new();

fn intern(s: &str) -> &'static str {
    let table = INTERN.get_or_init(|| Mutex::new(HashMap::new()));
    let mut guard = table.lock().expect("intern table poisoned");
    if let Some(&existing) = guard.get(s) {
        return existing;
    }
    let leaked: &'static str = Box::leak(s.to_owned().into_boxed_str());
    guard.insert(leaked.to_owned(), leaked);
    leaked
}

impl Permission {
    /// Construct a permission level from a name. Does NOT validate the L2
    /// charset; chain construction validates. Name is interned on first use.
    pub fn new<S: AsRef<str>>(name: S) -> Self {
        Self {
            name: intern(name.as_ref()),
        }
    }

    /// Const constructor for static-string names. Used by `default_levels`.
    /// The provided string MUST already be a `&'static str` — no interning.
    pub const fn from_static(name: &'static str) -> Self {
        Self { name }
    }

    pub fn as_str(&self) -> &str {
        self.name
    }

    pub fn name(&self) -> &str {
        self.name
    }
}

impl std::fmt::Display for Permission {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.name)
    }
}

// PartialOrd / Ord under the DEFAULT CHAIN ONLY.
//
// This impl exists to make tests, examples, and downstream user code ergonomic
// when working with the default 12-level chain. Library code in compile() and
// compose() MUST NOT rely on these traits — it uses chain.rank() / chain.meet()
// against an explicit chain (see the all-meets discipline in
// docs/specs/permission_chain_refactor_spec.md §2.1, enforced by CI grep gates).
//
// Foreign levels (names not in the default chain) panic. This is intentional:
// a level value compared through these operators is implicitly asserting it
// is a default-chain level. Code working on custom chains must use chain.cmp()
// and chain.meet() directly, never the operators.
impl PartialOrd for Permission {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        let chain = PermissionChain::default_chain();
        chain.cmp(self, other)
    }
}

impl Ord for Permission {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.partial_cmp(other).unwrap_or_else(|| {
            panic!(
                "Permission::cmp called with a level not in the default chain: {} or {}. \
                Use chain.cmp(&a, &b) against an explicit chain for non-default chains.",
                self, other
            )
        })
    }
}

impl Permission {
    /// Meet of two levels under the **default chain**. Panics if either level
    /// is not in the default chain. For custom chains, use `chain.meet()`.
    ///
    /// Accepts either owned or borrowed `Permission` via `impl Borrow<Permission>`
    /// so test code can write `a.meet(b)` or `a.meet(&b)` interchangeably.
    ///
    /// Library code in compile() / compose() MUST NOT use this — it works
    /// against an explicit chain. CI grep gates verify this discipline.
    pub fn meet<P: std::borrow::Borrow<Permission>>(&self, other: P) -> Permission {
        PermissionChain::default_chain()
            .meet(self, other.borrow())
            .unwrap_or_else(|e| panic!("Permission::meet: {}", e))
    }

    /// Meet of an iterator of levels under the **default chain**. Returns
    /// `None` if empty. Panics if any level is not in the default chain.
    pub fn meet_n<I: IntoIterator<Item = Permission>>(iter: I) -> Option<Permission> {
        iter.into_iter().reduce(|a, b| a.meet(&b))
    }

    /// Top of the default chain. For custom chains, use `chain.role(ChainRole::Top)`.
    pub fn top() -> Permission {
        PermissionChain::default_chain()
            .role(ChainRole::Top)
            .clone()
    }

    /// Iterator over the default chain's levels from top to bottom.
    /// For custom chains, use `chain.descending()`.
    pub fn descending() -> impl Iterator<Item = Permission> {
        let chain = PermissionChain::default_chain();
        chain
            .descending()
            .cloned()
            .collect::<Vec<_>>()
            .into_iter()
    }

    /// Parse a default-chain level name. **Case-insensitive** for backward
    /// compatibility — accepts "DIA", "dia", "Dia", etc. Returns `None` if
    /// the name is not in the default chain. For custom chains, use
    /// `chain.parse(name)` (case-sensitive).
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(name: &str) -> Option<Permission> {
        let upper = name.to_uppercase();
        PermissionChain::default_chain().parse(&upper)
    }
}

// Default-chain named-level associated functions (Permission::DIA() etc.) are
// defined in `default_levels.rs`, not here, so the CI Gate 1 grep can
// straightforwardly enforce "no variant references in core src outside
// default_levels.rs".

impl From<&str> for Permission {
    fn from(s: &str) -> Self {
        Self::new(s)
    }
}

impl From<String> for Permission {
    fn from(s: String) -> Self {
        Self::new(s)
    }
}

// -----------------------------------------------------------------------------
// ChainRole
// -----------------------------------------------------------------------------

/// Roles the compiler must be able to address by chain position.
///
/// Each role is a structural anchor — the compiler reads `chain.role(R)` instead
/// of naming a level by literal. See §2 of the spec for what each role does.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ChainRole {
    /// Bottom of the lattice. membership ≠ InClass, no-profiles-defined, compose
    /// meet seed.
    Bottom,
    /// Expiry floor. Context expiry already fired or expired-token meet target.
    ExpiryFloor,
    /// Structural-blocker meet target (PROVENANCE_MISMATCH / DEAD_CREDENTIAL).
    Refused,
    /// Descending-search initial value when profiles exist but none are satisfied.
    Unsatisfied,
    /// Ceiling applied when `disallowed_uses` is non-empty. Domain choice;
    /// historically `ROL` in the default chain. May coincide with other
    /// below-threshold roles in collapsed chains.
    DisallowedUsesCeiling,
    /// Threshold below which structural blockers (provenance / dead credential)
    /// fire. The guard is `outcome < BlockerThreshold`.
    BlockerThreshold,
    /// Top of the lattice. Default value for unconstrained ceilings.
    Top,
}

impl ChainRole {
    pub const ALL: [ChainRole; 7] = [
        ChainRole::Bottom,
        ChainRole::ExpiryFloor,
        ChainRole::Refused,
        ChainRole::Unsatisfied,
        ChainRole::DisallowedUsesCeiling,
        ChainRole::BlockerThreshold,
        ChainRole::Top,
    ];
}

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------

/// Why a level name was rejected by L2 charset validation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum NameRejectionReason {
    /// Name is empty.
    Empty,
    /// Name exceeds the 64-byte length limit.
    TooLong { length: usize, max: usize },
    /// Name contains a character outside `[A-Za-z0-9_-]`, or starts with `-`.
    CharsetViolation { offending_char: char, position: usize },
}

/// Errors returned by `PermissionChain::new`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChainError {
    /// L1: fewer than 2 levels.
    TooFewLevels { count: usize },
    /// L1: more than MAX_LEVELS levels.
    TooManyLevels { count: usize, max: usize },
    /// L2: name failed charset validation.
    InvalidName {
        name: String,
        reason: NameRejectionReason,
    },
    /// L3: duplicate level name in the chain.
    DuplicateName(String),
    /// L4: a `ChainRole` was not mapped to any level.
    MissingRole(ChainRole),
    /// L4: a role's index is out of bounds.
    RoleIndexOutOfBounds {
        role: ChainRole,
        index: usize,
        len: usize,
    },
    /// L5/L6/L7/L8/L9: role placed in violation of the structural order.
    RoleOrderViolation {
        role: ChainRole,
        index: usize,
        constraint: String,
    },
    /// `chain.meet(a, b)` or other operation with a level not in this chain.
    ForeignLevel { name: String },
}

impl std::fmt::Display for ChainError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ChainError::TooFewLevels { count } => {
                write!(f, "chain has too few levels: {} (minimum 2)", count)
            }
            ChainError::TooManyLevels { count, max } => {
                write!(f, "chain has too many levels: {} (maximum {})", count, max)
            }
            ChainError::InvalidName { name, reason } => {
                write!(f, "invalid level name {:?}: {:?}", name, reason)
            }
            ChainError::DuplicateName(name) => {
                write!(f, "duplicate level name {:?}", name)
            }
            ChainError::MissingRole(role) => {
                write!(f, "chain is missing role {:?}", role)
            }
            ChainError::RoleIndexOutOfBounds { role, index, len } => write!(
                f,
                "role {:?} maps to index {} but chain has only {} levels",
                role, index, len
            ),
            ChainError::RoleOrderViolation {
                role,
                index,
                constraint,
            } => write!(
                f,
                "role {:?} at index {} violates structural constraint: {}",
                role, index, constraint
            ),
            ChainError::ForeignLevel { name } => {
                write!(f, "level {:?} is not in this chain", name)
            }
        }
    }
}

impl std::error::Error for ChainError {}

// -----------------------------------------------------------------------------
// ChainHash
// -----------------------------------------------------------------------------

/// SHA-256 over a canonical encoding of `(ordered names, role bindings)`.
///
/// Two chains have the same hash iff they have the same ordered list of level
/// names AND the same role→index mapping.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ChainHash([u8; 32]);

impl ChainHash {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }

    pub fn to_hex(&self) -> String {
        hex::encode(self.0)
    }

    pub fn from_hex(s: &str) -> Option<Self> {
        let bytes = hex::decode(s).ok()?;
        if bytes.len() != 32 {
            return None;
        }
        let mut arr = [0u8; 32];
        arr.copy_from_slice(&bytes);
        Some(Self(arr))
    }
}

impl std::fmt::Display for ChainHash {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.to_hex())
    }
}

impl Serialize for ChainHash {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_hex())
    }
}

impl<'de> Deserialize<'de> for ChainHash {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        ChainHash::from_hex(&s).ok_or_else(|| serde::de::Error::custom("invalid ChainHash hex"))
    }
}

// -----------------------------------------------------------------------------
// PermissionChain
// -----------------------------------------------------------------------------

/// Hard cap on chain length. Limited by the `u8` rank type.
pub const MAX_LEVELS: usize = 256;

/// Maximum length of a level name in bytes.
pub const MAX_NAME_LEN: usize = 64;

/// A validated permission chain.
///
/// Construction goes through `PermissionChain::new`, which enforces L1–L9 in
/// `docs/specs/permission_chain_refactor_spec.md`. Once constructed, the chain
/// is immutable.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(try_from = "RawChain", into = "RawChain")]
pub struct PermissionChain {
    /// Levels in ascending order. `levels[0]` is bottom, `levels.last()` is top.
    levels: Vec<Permission>,
    /// Role → index into `levels`.
    roles: HashMap<ChainRole, usize>,
    /// Name → index into `levels`. Built at construction for O(1) lookup.
    name_index: HashMap<&'static str, usize>,
    /// Cached chain hash.
    chain_hash: ChainHash,
}

/// Serde representation: just the ordered names + the role map.
/// Validation happens on deserialization via `TryFrom`.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct RawChain {
    levels: Vec<String>,
    roles: Vec<(ChainRole, usize)>,
}

impl TryFrom<RawChain> for PermissionChain {
    type Error = ChainError;
    fn try_from(raw: RawChain) -> Result<Self, ChainError> {
        let levels: Vec<Permission> = raw.levels.into_iter().map(Permission::new).collect();
        let roles: HashMap<ChainRole, usize> = raw.roles.into_iter().collect();
        PermissionChain::new(levels, roles)
    }
}

impl From<PermissionChain> for RawChain {
    fn from(c: PermissionChain) -> Self {
        let mut roles: Vec<(ChainRole, usize)> =
            c.roles.into_iter().collect();
        // Sort by ChainRole for deterministic serialization.
        roles.sort_by_key(|(r, _)| match r {
            ChainRole::Bottom => 0u8,
            ChainRole::ExpiryFloor => 1,
            ChainRole::Refused => 2,
            ChainRole::Unsatisfied => 3,
            ChainRole::DisallowedUsesCeiling => 4,
            ChainRole::BlockerThreshold => 5,
            ChainRole::Top => 6,
        });
        Self {
            levels: c.levels.into_iter().map(|p| p.name.to_string()).collect(),
            roles,
        }
    }
}

impl PermissionChain {
    /// Construct a permission chain. Enforces L1–L9.
    pub fn new(
        levels: Vec<Permission>,
        roles: HashMap<ChainRole, usize>,
    ) -> Result<Self, ChainError> {
        // L1: 2 ≤ len ≤ MAX_LEVELS.
        if levels.len() < 2 {
            return Err(ChainError::TooFewLevels {
                count: levels.len(),
            });
        }
        if levels.len() > MAX_LEVELS {
            return Err(ChainError::TooManyLevels {
                count: levels.len(),
                max: MAX_LEVELS,
            });
        }

        // L2: validate names. L3: detect duplicates.
        let mut name_index: HashMap<&'static str, usize> = HashMap::with_capacity(levels.len());
        for (i, level) in levels.iter().enumerate() {
            validate_name(level.name)?;
            if name_index.insert(level.name, i).is_some() {
                return Err(ChainError::DuplicateName(level.name.to_string()));
            }
        }

        // L4: every ChainRole is mapped, and the index is in bounds.
        for role in ChainRole::ALL.iter().copied() {
            match roles.get(&role) {
                None => return Err(ChainError::MissingRole(role)),
                Some(&idx) if idx >= levels.len() => {
                    return Err(ChainError::RoleIndexOutOfBounds {
                        role,
                        index: idx,
                        len: levels.len(),
                    });
                }
                Some(_) => {}
            }
        }

        let last = levels.len() - 1;
        let bottom = roles[&ChainRole::Bottom];
        let top = roles[&ChainRole::Top];
        let expiry = roles[&ChainRole::ExpiryFloor];
        let refused = roles[&ChainRole::Refused];
        let unsatisfied = roles[&ChainRole::Unsatisfied];
        let disallowed_uses = roles[&ChainRole::DisallowedUsesCeiling];
        let threshold = roles[&ChainRole::BlockerThreshold];

        // L5: Bottom == 0.
        if bottom != 0 {
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::Bottom,
                index: bottom,
                constraint: "Bottom must be index 0".into(),
            });
        }

        // L6: Top == last.
        if top != last {
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::Top,
                index: top,
                constraint: format!("Top must be index {} (last)", last),
            });
        }

        // L7: ExpiryFloor < BlockerThreshold (non-strict at Bottom; the
        // collapsed-anchor case Q5 permits ExpiryFloor==Bottom).
        if expiry >= threshold {
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::ExpiryFloor,
                index: expiry,
                constraint: format!(
                    "ExpiryFloor index ({}) must be strictly less than BlockerThreshold index ({})",
                    expiry, threshold
                ),
            });
        }

        // L8: Refused < BlockerThreshold.
        if refused >= threshold {
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::Refused,
                index: refused,
                constraint: format!(
                    "Refused index ({}) must be strictly less than BlockerThreshold index ({})",
                    refused, threshold
                ),
            });
        }

        // L9: Unsatisfied < BlockerThreshold.
        if unsatisfied >= threshold {
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::Unsatisfied,
                index: unsatisfied,
                constraint: format!(
                    "Unsatisfied index ({}) must be strictly less than BlockerThreshold index ({})",
                    unsatisfied, threshold
                ),
            });
        }

        // L9b: DisallowedUsesCeiling < Top (the ceiling must NOT equal the top
        // — otherwise disallowed_uses has no effect). May sit anywhere strictly
        // below the top.
        if disallowed_uses >= levels.len() - 1 + 1 {
            // index < len always holds since we checked earlier; the real
            // constraint is just < top, i.e. ≤ last - 1. But top == last and
            // we want disallowed_uses < top:
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::DisallowedUsesCeiling,
                index: disallowed_uses,
                constraint: format!(
                    "DisallowedUsesCeiling index ({}) must be strictly less than Top index ({})",
                    disallowed_uses,
                    last
                ),
            });
        }
        if disallowed_uses >= top {
            return Err(ChainError::RoleOrderViolation {
                role: ChainRole::DisallowedUsesCeiling,
                index: disallowed_uses,
                constraint: format!(
                    "DisallowedUsesCeiling index ({}) must be strictly less than Top index ({})",
                    disallowed_uses, top
                ),
            });
        }

        let chain_hash = compute_chain_hash(&levels, &roles);

        Ok(Self {
            levels,
            roles,
            name_index,
            chain_hash,
        })
    }

    /// The default chain: historical OOC..AAA, 12 levels.
    pub fn default_chain() -> &'static PermissionChain {
        static DEFAULT: OnceLock<PermissionChain> = OnceLock::new();
        DEFAULT.get_or_init(|| {
            let names = [
                "OOC", "EXP", "REF", "UNS", "ETA", "ESC", "ROL", "DIA", "REV", "AEX", "ALR", "AAA",
            ];
            let levels: Vec<Permission> = names.iter().map(|n| Permission::new(*n)).collect();
            let mut roles = HashMap::new();
            roles.insert(ChainRole::Bottom, 0); // OOC
            roles.insert(ChainRole::ExpiryFloor, 1); // EXP
            roles.insert(ChainRole::Refused, 2); // REF
            roles.insert(ChainRole::Unsatisfied, 3); // UNS
            roles.insert(ChainRole::DisallowedUsesCeiling, 6); // ROL
            roles.insert(ChainRole::BlockerThreshold, 7); // DIA
            roles.insert(ChainRole::Top, 11); // AAA
            PermissionChain::new(levels, roles).expect("default chain must validate")
        })
    }

    /// Level at the given role.
    pub fn role(&self, role: ChainRole) -> &Permission {
        let idx = self.roles[&role];
        &self.levels[idx]
    }

    /// Rank of a level within this chain. `None` if the level is not present.
    pub fn rank(&self, p: &Permission) -> Option<u8> {
        self.name_index.get(p.name).map(|&i| i as u8)
    }

    /// Compare two levels under this chain's order. `None` if either is foreign.
    pub fn cmp(&self, a: &Permission, b: &Permission) -> Option<std::cmp::Ordering> {
        Some(self.rank(a)?.cmp(&self.rank(b)?))
    }

    /// Meet (min) of two levels under this chain's order.
    ///
    /// Returns `Err(ChainError::ForeignLevel)` if either level is not in the chain.
    /// This is the load-bearing operation for the "all-meets discipline": every
    /// structural step in the compiler is `outcome = chain.meet(outcome, ...)`.
    pub fn meet(&self, a: &Permission, b: &Permission) -> Result<Permission, ChainError> {
        let ra = self.rank(a).ok_or_else(|| ChainError::ForeignLevel {
            name: a.name.to_string(),
        })?;
        let rb = self.rank(b).ok_or_else(|| ChainError::ForeignLevel {
            name: b.name.to_string(),
        })?;
        Ok(self.levels[ra.min(rb) as usize])
    }

    /// Iterate over levels from top down to bottom.
    pub fn descending(&self) -> impl Iterator<Item = &Permission> {
        self.levels.iter().rev()
    }

    /// Iterate over levels from bottom to top.
    pub fn ascending(&self) -> impl Iterator<Item = &Permission> {
        self.levels.iter()
    }

    /// Whether the chain contains a level with the given name.
    pub fn contains(&self, p: &Permission) -> bool {
        self.name_index.contains_key(p.name)
    }

    /// Look up a level by name. Equivalent to `chain.parse(name)`.
    pub fn get(&self, name: &str) -> Option<&Permission> {
        self.name_index.get(name).map(|&i| &self.levels[i])
    }

    /// Parse a level name. Case-sensitive. Returns `None` if not in chain.
    pub fn parse(&self, name: &str) -> Option<Permission> {
        self.get(name).copied()
    }

    /// Number of levels in the chain.
    pub fn len(&self) -> usize {
        self.levels.len()
    }

    /// Levels as a slice.
    pub fn levels(&self) -> &[Permission] {
        &self.levels
    }

    /// SHA-256 over the canonical encoding of `(ordered names, role bindings)`.
    pub fn chain_hash(&self) -> ChainHash {
        self.chain_hash
    }
}

impl PartialEq for PermissionChain {
    fn eq(&self, other: &Self) -> bool {
        self.chain_hash == other.chain_hash
    }
}

impl Eq for PermissionChain {}

// -----------------------------------------------------------------------------
// Chain hash and name validation
// -----------------------------------------------------------------------------

fn validate_name(name: &str) -> Result<(), ChainError> {
    if name.is_empty() {
        return Err(ChainError::InvalidName {
            name: name.to_string(),
            reason: NameRejectionReason::Empty,
        });
    }
    if name.len() > MAX_NAME_LEN {
        return Err(ChainError::InvalidName {
            name: name.to_string(),
            reason: NameRejectionReason::TooLong {
                length: name.len(),
                max: MAX_NAME_LEN,
            },
        });
    }
    // Charset: [A-Za-z0-9_][A-Za-z0-9_-]*
    for (i, c) in name.chars().enumerate() {
        let ok = if i == 0 {
            c.is_ascii_alphanumeric() || c == '_'
        } else {
            c.is_ascii_alphanumeric() || c == '_' || c == '-'
        };
        if !ok {
            return Err(ChainError::InvalidName {
                name: name.to_string(),
                reason: NameRejectionReason::CharsetViolation {
                    offending_char: c,
                    position: i,
                },
            });
        }
    }
    Ok(())
}

fn compute_chain_hash(
    levels: &[Permission],
    roles: &HashMap<ChainRole, usize>,
) -> ChainHash {
    let mut hasher = Sha256::new();
    // Levels in order, null-delimited.
    for level in levels {
        hasher.update(level.name.as_bytes());
        hasher.update(b"\x00");
    }
    hasher.update(b"\xff"); // boundary marker between levels and roles
    // Roles in fixed order (ChainRole::ALL) so the hash is deterministic.
    for role in ChainRole::ALL.iter().copied() {
        let idx = roles[&role];
        hasher.update(&(idx as u32).to_be_bytes());
    }
    let out = hasher.finalize();
    let mut arr = [0u8; 32];
    arr.copy_from_slice(&out);
    ChainHash(arr)
}

// -----------------------------------------------------------------------------
// ChainRegistry — mechanically verified publication (§3.3 mechanism 4)
// -----------------------------------------------------------------------------

/// A registry mapping `ChainHash` → `PermissionChain`. Auditors consult a
/// registry to resolve a judgment's `chain_hash` back to the chain that
/// authorized the decision.
pub trait ChainRegistry {
    fn lookup(&self, hash: &ChainHash) -> Option<&PermissionChain>;
}

/// Simple in-memory registry. Useful for tests and single-process deployments.
#[derive(Debug, Default, Clone)]
pub struct InMemoryChainRegistry {
    chains: HashMap<ChainHash, PermissionChain>,
}

impl InMemoryChainRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Publish a chain. Returns the chain's hash.
    pub fn publish(&mut self, chain: PermissionChain) -> ChainHash {
        let h = chain.chain_hash();
        self.chains.insert(h, chain);
        h
    }

    pub fn len(&self) -> usize {
        self.chains.len()
    }

    pub fn is_empty(&self) -> bool {
        self.chains.is_empty()
    }
}

impl ChainRegistry for InMemoryChainRegistry {
    fn lookup(&self, hash: &ChainHash) -> Option<&PermissionChain> {
        self.chains.get(hash)
    }
}

/// Audit-time error: a judgment's chain_hash does not resolve in the registry,
/// or the resolved chain re-hashes to a different value (registry tampering).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuditError {
    /// `judgment.chain_hash` is not present in the registry.
    NotPublished { hash: ChainHash },
    /// The chain published at this hash re-hashes to a different value.
    /// Indicates registry tampering or hash collision.
    HashMismatch {
        expected: ChainHash,
        actual: ChainHash,
    },
}

impl std::fmt::Display for AuditError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AuditError::NotPublished { hash } => {
                write!(f, "chain hash {} is not published in the registry", hash)
            }
            AuditError::HashMismatch { expected, actual } => write!(
                f,
                "chain hash mismatch: expected {}, registered chain hashes to {}",
                expected, actual
            ),
        }
    }
}

impl std::error::Error for AuditError {}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn default() -> &'static PermissionChain {
        PermissionChain::default_chain()
    }

    #[test]
    fn default_chain_validates() {
        let chain = default();
        assert_eq!(chain.len(), 12);
        // All roles present.
        for role in ChainRole::ALL {
            let _ = chain.role(role);
        }
    }

    #[test]
    fn default_chain_role_mapping() {
        let chain = default();
        assert_eq!(chain.role(ChainRole::Bottom).as_str(), "OOC");
        assert_eq!(chain.role(ChainRole::ExpiryFloor).as_str(), "EXP");
        assert_eq!(chain.role(ChainRole::Refused).as_str(), "REF");
        assert_eq!(chain.role(ChainRole::Unsatisfied).as_str(), "UNS");
        assert_eq!(chain.role(ChainRole::BlockerThreshold).as_str(), "DIA");
        assert_eq!(chain.role(ChainRole::Top).as_str(), "AAA");
    }

    #[test]
    fn default_chain_descending_order() {
        let chain = default();
        let names: Vec<&str> = chain.descending().map(|p| p.as_str()).collect();
        assert_eq!(
            names,
            vec![
                "AAA", "ALR", "AEX", "REV", "DIA", "ROL", "ESC", "ETA", "UNS", "REF", "EXP", "OOC"
            ]
        );
    }

    #[test]
    fn meet_is_min_under_rank() {
        let chain = default();
        let dia = chain.parse("DIA").unwrap();
        let aaa = chain.parse("AAA").unwrap();
        let ref_ = chain.parse("REF").unwrap();
        assert_eq!(chain.meet(&dia, &aaa).unwrap().as_str(), "DIA");
        assert_eq!(chain.meet(&dia, &ref_).unwrap().as_str(), "REF");
        assert_eq!(chain.meet(&aaa, &ref_).unwrap().as_str(), "REF");
    }

    #[test]
    fn foreign_level_meet_fails() {
        let chain = default();
        let dia = chain.parse("DIA").unwrap();
        let alien = Permission::new("ALIEN");
        match chain.meet(&dia, &alien) {
            Err(ChainError::ForeignLevel { name }) => assert_eq!(name, "ALIEN"),
            other => panic!("expected ForeignLevel, got {:?}", other),
        }
    }

    #[test]
    fn rank_of_foreign_is_none() {
        let chain = default();
        assert!(chain.rank(&Permission::new("ALIEN")).is_none());
        assert_eq!(chain.rank(&Permission::new("DIA")), Some(7));
    }

    #[test]
    fn too_few_levels_rejected() {
        let mut roles = HashMap::new();
        for r in ChainRole::ALL {
            roles.insert(r, 0);
        }
        let res = PermissionChain::new(vec![Permission::new("A")], roles);
        assert!(matches!(res, Err(ChainError::TooFewLevels { count: 1 })));
    }

    #[test]
    fn too_many_levels_rejected() {
        let levels: Vec<Permission> = (0..MAX_LEVELS + 1)
            .map(|i| Permission::new(format!("L{:04}", i)))
            .collect();
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, MAX_LEVELS);
        roles.insert(ChainRole::Top, MAX_LEVELS);
        let res = PermissionChain::new(levels, roles);
        assert!(matches!(res, Err(ChainError::TooManyLevels { .. })));
    }

    #[test]
    fn duplicate_name_rejected() {
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        roles.insert(ChainRole::Top, 2);
        let res = PermissionChain::new(
            vec![
                Permission::new("DUP"),
                Permission::new("DUP"),
                Permission::new("TOP"),
            ],
            roles,
        );
        assert!(matches!(res, Err(ChainError::DuplicateName(_))));
    }

    #[test]
    fn empty_name_rejected() {
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        roles.insert(ChainRole::Top, 1);
        let res = PermissionChain::new(
            vec![Permission::new(""), Permission::new("TOP")],
            roles,
        );
        match res {
            Err(ChainError::InvalidName {
                reason: NameRejectionReason::Empty,
                ..
            }) => {}
            other => panic!("expected Empty, got {:?}", other),
        }
    }

    #[test]
    fn missing_role_rejected() {
        // Omit Top.
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        let res = PermissionChain::new(
            vec![Permission::new("A"), Permission::new("B")],
            roles,
        );
        assert!(matches!(res, Err(ChainError::MissingRole(ChainRole::Top))));
    }

    #[test]
    fn bottom_not_index_zero_rejected() {
        // Put bottom at index 1.
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 1);
        roles.insert(ChainRole::ExpiryFloor, 1);
        roles.insert(ChainRole::Refused, 1);
        roles.insert(ChainRole::Unsatisfied, 1);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 2);
        roles.insert(ChainRole::Top, 2);
        let res = PermissionChain::new(
            vec![
                Permission::new("A"),
                Permission::new("B"),
                Permission::new("C"),
            ],
            roles,
        );
        match res {
            Err(ChainError::RoleOrderViolation {
                role: ChainRole::Bottom,
                ..
            }) => {}
            other => panic!("expected Bottom violation, got {:?}", other),
        }
    }

    #[test]
    fn top_not_last_rejected() {
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        roles.insert(ChainRole::Top, 1); // should be 2
        let res = PermissionChain::new(
            vec![
                Permission::new("A"),
                Permission::new("B"),
                Permission::new("C"),
            ],
            roles,
        );
        match res {
            Err(ChainError::RoleOrderViolation {
                role: ChainRole::Top,
                ..
            }) => {}
            other => panic!("expected Top violation, got {:?}", other),
        }
    }

    #[test]
    fn expiry_floor_above_threshold_rejected() {
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 2); // bad: ≥ threshold
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        roles.insert(ChainRole::Top, 2);
        let res = PermissionChain::new(
            vec![
                Permission::new("A"),
                Permission::new("B"),
                Permission::new("C"),
            ],
            roles,
        );
        match res {
            Err(ChainError::RoleOrderViolation {
                role: ChainRole::ExpiryFloor,
                ..
            }) => {}
            other => panic!("expected ExpiryFloor violation, got {:?}", other),
        }
    }

    #[test]
    fn paper_5_level_chain_collapsed_below_threshold() {
        // Paper-style: REF < DIA < REV < AEX < ALR.
        // All four below-threshold roles collapse onto REF (Bottom).
        let levels: Vec<Permission> = ["REF", "DIA", "REV", "AEX", "ALR"]
            .iter()
            .map(|n| Permission::new(*n))
            .collect();
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1); // DIA
        roles.insert(ChainRole::Top, 4); // ALR
        let chain = PermissionChain::new(levels, roles).expect("paper-5 must validate");
        assert_eq!(chain.role(ChainRole::Bottom).as_str(), "REF");
        assert_eq!(chain.role(ChainRole::Refused).as_str(), "REF");
        assert_eq!(chain.role(ChainRole::BlockerThreshold).as_str(), "DIA");
        assert_eq!(chain.role(ChainRole::Top).as_str(), "ALR");
    }

    #[test]
    fn chain_hash_is_deterministic() {
        let h1 = PermissionChain::default_chain().chain_hash();
        let h2 = PermissionChain::default_chain().chain_hash();
        assert_eq!(h1, h2);
    }

    #[test]
    fn different_role_bindings_different_hash() {
        // Same names, different role bindings → different hash.
        let levels: Vec<Permission> = ["A", "B", "C", "D"]
            .iter()
            .map(|n| Permission::new(*n))
            .collect();
        let mut r1 = HashMap::new();
        r1.insert(ChainRole::Bottom, 0);
        r1.insert(ChainRole::ExpiryFloor, 1);
        r1.insert(ChainRole::Refused, 1);
        r1.insert(ChainRole::Unsatisfied, 1);
        r1.insert(ChainRole::DisallowedUsesCeiling, 0);
        r1.insert(ChainRole::BlockerThreshold, 2);
        r1.insert(ChainRole::Top, 3);
        let c1 = PermissionChain::new(levels.clone(), r1).unwrap();

        let mut r2 = HashMap::new();
        r2.insert(ChainRole::Bottom, 0);
        r2.insert(ChainRole::ExpiryFloor, 0); // different
        r2.insert(ChainRole::Refused, 0);
        r2.insert(ChainRole::Unsatisfied, 0);
        r2.insert(ChainRole::DisallowedUsesCeiling, 0);
        r2.insert(ChainRole::BlockerThreshold, 2);
        r2.insert(ChainRole::Top, 3);
        let c2 = PermissionChain::new(levels, r2).unwrap();

        assert_ne!(c1.chain_hash(), c2.chain_hash());
    }

    #[test]
    fn chain_serde_round_trip() {
        let chain = PermissionChain::default_chain().clone();
        let json = serde_json::to_string(&chain).unwrap();
        let parsed: PermissionChain = serde_json::from_str(&json).unwrap();
        assert_eq!(chain.chain_hash(), parsed.chain_hash());
        assert_eq!(chain.len(), parsed.len());
    }

    #[test]
    fn chain_hash_hex_round_trip() {
        let h = PermissionChain::default_chain().chain_hash();
        let hex = h.to_hex();
        let parsed = ChainHash::from_hex(&hex).unwrap();
        assert_eq!(h, parsed);
    }

    #[test]
    fn registry_lookup_present_and_absent() {
        let mut reg = InMemoryChainRegistry::new();
        assert!(reg.is_empty());

        let chain = PermissionChain::default_chain().clone();
        let h = reg.publish(chain.clone());
        assert_eq!(reg.lookup(&h).map(|c| c.chain_hash()), Some(h));

        // Foreign hash misses.
        let zero = ChainHash([0u8; 32]);
        assert!(reg.lookup(&zero).is_none());
    }

    #[test]
    fn name_charset_violation_rejected() {
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        roles.insert(ChainRole::Top, 1);
        // Space is not in charset.
        let res = PermissionChain::new(
            vec![Permission::new("A B"), Permission::new("TOP")],
            roles,
        );
        match res {
            Err(ChainError::InvalidName {
                reason: NameRejectionReason::CharsetViolation { offending_char: ' ', .. },
                ..
            }) => {}
            other => panic!("expected CharsetViolation, got {:?}", other),
        }
    }

    #[test]
    fn name_too_long_rejected() {
        let long = "A".repeat(MAX_NAME_LEN + 1);
        let mut roles = HashMap::new();
        roles.insert(ChainRole::Bottom, 0);
        roles.insert(ChainRole::ExpiryFloor, 0);
        roles.insert(ChainRole::Refused, 0);
        roles.insert(ChainRole::Unsatisfied, 0);
        roles.insert(ChainRole::DisallowedUsesCeiling, 0);
        roles.insert(ChainRole::BlockerThreshold, 1);
        roles.insert(ChainRole::Top, 1);
        let res = PermissionChain::new(
            vec![Permission::new(long), Permission::new("TOP")],
            roles,
        );
        match res {
            Err(ChainError::InvalidName {
                reason: NameRejectionReason::TooLong { .. },
                ..
            }) => {}
            other => panic!("expected TooLong, got {:?}", other),
        }
    }
}
