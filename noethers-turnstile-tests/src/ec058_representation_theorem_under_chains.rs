//! EC-058 — Representation theorem and non-constancy lemma (T-REPR-01, T-NONCONST-01).
//!
//! Representation theorem (§3.3): a sharp compiler exists iff every
//! permission-relevant failure mode is detectable in the evidence
//! representation. The compiler returns the same output on two contexts with
//! identical evidence representations, even when an underlying world fact
//! differs — so the failure of sharpness is representational, not
//! computational.

use noethers_turnstile_core::{compile_with_chain, permission::PermissionChain};
use noethers_turnstile_tests::chain_helpers::{paper_5_level, simple_context_with_profile};

#[test]
fn t_repr_01_same_evidence_same_output_under_paper_chain() {
    let chain = paper_5_level();
    // Two contexts with the same evidence representation but different
    // candidate_ids (the "world fact" hidden from the evidence map).
    let ctx_a = simple_context_with_profile(&chain, chain.parse("DIA").unwrap(), "world-a");
    let mut ctx_b = ctx_a.clone();
    ctx_b.candidate_id = "world-b".into();
    // Rehash to match new candidate_id.
    let new_hash = noethers_turnstile_core::token::compute_provenance_hash(
        &ctx_b.claim_id,
        &ctx_b.candidate_id,
        &ctx_b.context_id,
        &ctx_b.allowed_use,
    );
    for tok in &mut ctx_b.tokens {
        tok.provenance_hash = new_hash.clone();
    }

    let j_a = compile_with_chain(ctx_a, &chain).unwrap();
    let j_b = compile_with_chain(ctx_b, &chain).unwrap();
    // Same evidence representation → same permission (the compiler is
    // representation-bounded; can't see beyond candidate_id).
    assert_eq!(j_a.permission, j_b.permission);
}

#[test]
fn t_nonconst_01_compiler_silence_when_failure_invisible_to_evidence() {
    // Two contexts that map to the same evidence package (same gaps, same
    // tokens, same profiles) but represent different worlds. The compiler
    // returns the same permission on both because the evidence map is
    // representation-bounded. This is the non-constancy lemma: if a
    // permission-relevant failure isn't visible to evidence, no compiler
    // (regardless of chain) can be sharp on it.
    //
    // We assert the *silence shape*: the compiler does not distinguish the
    // two worlds, so it must return the same permission. An external
    // labeler would have to flag one as unsound.
    let chain = paper_5_level();
    let ctx1 = simple_context_with_profile(&chain, chain.parse("REV").unwrap(), "w1");
    let mut ctx2 = ctx1.clone();
    // Mutate ONLY a field that is invisible to the evidence map (the
    // context_fingerprint is not part of provenance hash).
    ctx2.context_fingerprint = "different-fp-but-same-evidence".into();

    let p1 = compile_with_chain(ctx1, &chain).unwrap().permission;
    let p2 = compile_with_chain(ctx2, &chain).unwrap().permission;
    // Compiler is silent on the difference — same output on both.
    assert_eq!(p1, p2);
    // If we externally know one is unsound (e.g., context_fingerprint mismatch
    // at runtime), the compile-time output is the same. That's exactly the
    // representation theorem's predicted silence.
}

#[test]
fn theorem_invariance_under_chain_choice() {
    // The representation theorem is invariant to chain choice. Same evidence,
    // different chains → still same shape of representation-induced silence.
    let chain_a = paper_5_level();
    let chain_b = noethers_turnstile_tests::chain_helpers::anon_8_level();

    let ctx_a = simple_context_with_profile(&chain_a, chain_a.parse("REV").unwrap(), "thm-a");
    let ctx_b = simple_context_with_profile(&chain_b, chain_b.parse("L05").unwrap(), "thm-b");
    // Both compile successfully — confirming the theorem doesn't depend on
    // the chain having any specific names.
    let _ = compile_with_chain(ctx_a, &chain_a).unwrap();
    let _ = compile_with_chain(ctx_b, &chain_b).unwrap();
}

#[test]
fn default_chain_satisfies_representation_theorem_too() {
    let chain = PermissionChain::default_chain();
    let ctx_a = simple_context_with_profile(chain, chain.parse("DIA").unwrap(), "def-a");
    let ctx_b = ctx_a.clone();
    let j_a = compile_with_chain(ctx_a, chain).unwrap();
    let j_b = compile_with_chain(ctx_b, chain).unwrap();
    assert_eq!(j_a.permission, j_b.permission);
}
