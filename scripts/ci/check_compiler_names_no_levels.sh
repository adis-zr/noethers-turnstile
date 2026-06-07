#!/usr/bin/env bash
# CI gate: the compiler never names a permission level directly. See
# `docs/specs/permission_chain_refactor_spec.md` §7.7.
#
# Gate 1: no `Permission::OOC|EXP|...|AAA` identifier references in
# `noethers-turnstile-core/src/` outside `default_levels.rs`.
#
# Gate 2: no quoted string literal of any historical level name in
# `compiler.rs` or `composition.rs` (catches `chain.parse("DIA")` leaks).
#
# Exits 0 if both gates pass, 1 otherwise.

set -euo pipefail

cd "$(dirname "$0")/../.."

historical_names="OOC|EXP|REF|UNS|ETA|ESC|ROL|DIA|REV|AEX|ALR|AAA"

# ── Gate 1: no variant references in core src outside default_levels.rs ──────
# Excludes:
#   - default_levels.rs (the carve-out module)
#   - comment lines (// /// //!)
#   - tests/ subdirectory (test code can reference variants ergonomically)
gate1_hits=$(grep -rEn "Permission::($historical_names)\b" \
  noethers-turnstile-core/src/ \
  --include='*.rs' \
  --exclude='default_levels.rs' \
  | grep -vE ':\s*(///|//!|//)' \
  || true)

if [ -n "$gate1_hits" ]; then
  echo "Gate 1 FAILED: variant references found in core/src outside default_levels.rs:"
  echo "$gate1_hits"
  exit 1
fi

# ── Gate 2: no quoted level names in compiler.rs / composition.rs ────────────
# Match `"OOC"` etc. but skip lines that are doc comments (`///` or `//!`).
gate2_files=(
  noethers-turnstile-core/src/compiler.rs
  noethers-turnstile-core/src/composition.rs
)
gate2_hits=""
for f in "${gate2_files[@]}"; do
  hits=$(grep -nE "\"($historical_names)\"" "$f" \
    | grep -v -E '^\s*[0-9]+:\s*(///|//!|//)' \
    || true)
  if [ -n "$hits" ]; then
    gate2_hits+="$f:"$'\n'"$hits"$'\n'
  fi
done

if [ -n "$gate2_hits" ]; then
  echo "Gate 2 FAILED: quoted level-name literals in compiler.rs/composition.rs:"
  echo "$gate2_hits"
  exit 1
fi

echo "Both gates passed: compiler.rs / composition.rs reference no permission level by name."
