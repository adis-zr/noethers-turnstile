//! EC-059 — Default chain behavioral equivalence (T-DEFAULT-01, T-DEFAULT-02).
//!
//! For every `(ctx, expected_permission)` pair captured in the pre-refactor
//! golden corpus, `compile(ctx)` and `compile_with_chain(ctx, default_chain())`
//! must both return a judgment whose `permission` matches the golden value.

use std::fs;
use std::path::PathBuf;

use noethers_turnstile_core::{
    compile, compile_with_chain, context::ProofContext, permission::PermissionChain,
};
use serde::Deserialize;

#[derive(Deserialize)]
struct Golden {
    name: String,
    description: String,
    context: ProofContext,
    expected_permission: String,
}

fn fixtures_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures/pre_refactor_contexts")
}

fn load_corpus() -> Vec<Golden> {
    let dir = fixtures_dir();
    let mut goldens = vec![];
    let mut entries: Vec<_> = fs::read_dir(&dir)
        .expect("fixtures dir missing")
        .filter_map(Result::ok)
        .collect();
    entries.sort_by_key(|e| e.file_name());
    for entry in entries {
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) != Some("json") {
            continue;
        }
        let bytes = fs::read(&path).unwrap_or_else(|e| panic!("read {:?}: {e}", path));
        let g: Golden =
            serde_json::from_slice(&bytes).unwrap_or_else(|e| panic!("parse {:?}: {e}", path));
        goldens.push(g);
    }
    assert!(!goldens.is_empty(), "fixture corpus is empty");
    goldens
}

#[test]
fn t_default_01_bare_compile_matches_explicit_default_chain() {
    let corpus = load_corpus();
    for g in &corpus {
        let bare = compile(g.context.clone()).expect("compile");
        let explicit = compile_with_chain(g.context.clone(), PermissionChain::default_chain())
            .expect("compile_with_chain");
        assert_eq!(
            bare.permission, explicit.permission,
            "[{}] bare and explicit must agree",
            g.name
        );
        assert_eq!(
            bare.chain_hash,
            PermissionChain::default_chain().chain_hash(),
            "[{}] bare compile must stamp the default chain hash",
            g.name
        );
    }
}

#[test]
fn t_default_02_pre_refactor_golden_outputs_match() {
    let corpus = load_corpus();
    for g in &corpus {
        let j = compile(g.context.clone()).expect("compile");
        assert_eq!(
            j.permission.as_str(),
            g.expected_permission,
            "[{}] {}",
            g.name,
            g.description
        );
    }
}
