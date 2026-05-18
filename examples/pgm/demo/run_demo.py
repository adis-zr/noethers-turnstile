"""
Diabetes BIF — certified inference permission sweep.

Demonstrates the full certified inference loop end-to-end:
  load diabetes.bif → run inference at three memory budgets → get certificates
  → translate to turnstile proof tokens → compile permission judgment → print table.

Run from examples/pgm/:
  python demo/run_demo.py

Requires diabetes.bif in data/bif/ (from https://www.bnlearn.com/bnrepository/).
"""
from __future__ import annotations

import math
import sys
import time
import uuid
from pathlib import Path

# Allow running from examples/pgm/ without installing
_HERE = Path(__file__).parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import turnstile as t
from bridge.bridge import build_profiles
from bridge.bif_parser import parse_bif as bridge_parse_bif, bif_to_pgm_dicts
from bridge.claims import GAP_BASIS
from bridge.fingerprints import fingerprint, fingerprint_graph, fingerprint_query, fingerprint_evidence

from demo.inference import compile_inference, InferenceResult
from demo.bif_loader import parse_bif as demo_parse_bif, make_bif_instance
from demo.tokens import cert_to_proof_tokens, claim_class_for_geometry

BIF_PATH = _HERE / "data" / "bif" / "diabetes.bif"

# Hardcoded for diabetes.bif — calibrated to produce three distinct rows.
# Do NOT use budget_tiers() here: the exact byte counts below are confirmed by
# actual frontier sweeps and correspond to genuinely different compiler outcomes.
#   tight  (~9 MB)  → OOC: ValueError, no kernel fits (min plan ≈11.2 MB)
#   medium (~20 MB) → DIA: plan fits (hilbert), composition guard fires → infinite cert
#   loose  (~120 MB) → AEX: exact everywhere, KL=0.0, permission=AEX
BUDGETS = [
    ("tight",  9_000_000),
    ("medium", 20_000_000),
    ("loose",  120_000_000),
]


def _fmt_kl(kl: float) -> str:
    if not math.isfinite(kl):
        return "∞"
    return f"{kl:.4f}"


def _fmt_mem(mem_bytes: float) -> str:
    if mem_bytes <= 0:
        return "—"
    return f"{mem_bytes / 1e6:.1f} MB"


def main() -> None:
    if not BIF_PATH.exists():
        print(f"diabetes.bif not found at {BIF_PATH}")
        print("Download from https://www.bnlearn.com/bnrepository/ and place in data/bif/")
        sys.exit(0)

    # Parse once for fingerprinting (bridge format: string var names)
    bg = bridge_parse_bif(BIF_PATH)
    graph_dict, query_dict, _ = bif_to_pgm_dicts(bg)
    fp_graph = fingerprint_graph(graph_dict)
    fp_query = fingerprint_query(query_dict)
    fp_evidence = fingerprint_evidence({})   # no observations
    context_id = fp_evidence

    # Parse once for inference computation (demo format: integer IDs)
    demo_bif = demo_parse_bif(BIF_PATH)
    n_vars = len(demo_bif.domains)
    n_factors = len(demo_bif.factors_raw)
    query_var_id = demo_bif.query_var
    query_var_name = demo_bif.var_names[query_var_id]

    issued_at_unix = time.time()

    print(f"Diabetes BIF — certified inference permission sweep")
    print(f"Network : {n_vars} variables, {n_factors} factors")
    print(f"Query   : {query_var_name} (variable {query_var_id})")
    print(f"Evidence: none")
    print(f"C1/TP-C1: n/a (stubbed) — requires experiments package")
    print(f"          (see demo/inference/compiler/cert_policy.py for stub details)")
    print()

    rows = []
    for label, budget in BUDGETS:
        print(f"Running {label} budget ({budget / 1e6:.0f} MB)...", end=" ", flush=True)
        t0 = time.time()

        inst = make_bif_instance(
            "diabetes", demo_bif, budget, label,
            query_var=query_var_id, clamp_zeros=True,
        )

        try:
            result = compile_inference(inst.model, inst.query, budget)
            elapsed = time.time() - t0

            geometry = result.certificate_geometry
            claim_class = claim_class_for_geometry(geometry)

            fp_algorithm = fingerprint("exact") if geometry == "exact" else fingerprint("hilbert")
            prov_hash = t.compute_provenance_hash(fp_graph, fp_query, context_id, claim_class)

            ts_tokens = cert_to_proof_tokens(
                result, fp_graph, fp_query, fp_evidence,
                fp_algorithm, prov_hash, issued_at_unix,
            )

            ctx = t.ProofContext(
                claim_id=fp_graph,
                candidate_id=fp_query,
                context_id=context_id,
                allowed_use=claim_class,
                membership=t.Membership.InClass,
                authority_ceiling=t.Permission.ALR,
                expiry=t.Expiry.never(),
                gaps=[t.GapRecord(g, g) for g in GAP_BASIS],
                profiles=build_profiles(claim_class),
                tokens=ts_tokens,
                context_fingerprint=context_id,
            )

            live = t.compile(ctx)
            rt = t.RuntimeContext(now_unix=issued_at_unix, context_fingerprint=context_id)
            permission = live.permission_str(rt)

            kl_str = _fmt_kl(result.certified_kl)
            mem_str = _fmt_mem(result.memory.bytes)
            rows.append((label, f"{budget / 1e6:.0f} MB", geometry, kl_str, mem_str, "n/a", permission))
            print(f"done ({elapsed:.1f}s) → {permission}")

        except ValueError:
            elapsed = time.time() - t0
            rows.append((label, f"{budget / 1e6:.0f} MB", "—", "—", "—", "n/a", "OOC"))
            print(f"done ({elapsed:.1f}s) → OOC (no plan fits)")

    # Print table
    print()
    header = f"{'Budget':<8}  {'Budget':<9}  {'Geometry':<10}  {'KL bound':<12}  {'Mem':<10}  {'C1':<6}  {'Permission'}"
    sep    = "─" * len(header)
    print("━" * len(header))
    print(header)
    print(sep)
    for row in rows:
        label, bstr, geom, kl, mem, c1, perm = row
        print(f"{label:<8}  {bstr:<9}  {geom:<10}  {kl:<12}  {mem:<10}  {c1:<6}  {perm}")
    print("━" * len(header))

    # Row notes
    print()
    print("── Row notes " + "─" * 67)
    print("tight  (OOC):   No certified candidate fits within 9 MB.")
    print("                The minimum feasible plan requires ≈11.2 MB.")
    print("                Inference is out of class for this memory tier.")
    print()
    print("medium (DIA):   Plan fits in 20 MB using hilbert kernel, but the composition")
    print("                soundness check fails — 161 Hilbert sites with 4307 overlapping")
    print("                output scopes. A finite KL bound requires a residual certificate")
    print("                (C1/TP-C1), which is stubbed in this demo.")
    print("                With C1/TP-C1 available, a finite bound could potentially be")
    print("                recovered. Result: infinite certificate, no useful bound → DIA.")
    print()
    print("loose  (AEX):   Exact inference everywhere. KL = 0 (computation is provably")
    print("                correct given the model).")

    # The model_specification_gap lesson
    print()
    print("── The model_specification_gap boundary " + "─" * 40)
    print("The loose row earns AEX, not ALR. model_specification_gap stays OPEN.")
    print("This gap asks: 'Is the diabetes BIF model an adequate representation of")
    print("real patients?' No inference kernel can answer that. It requires a")
    print("ModelSpecificationToken issued by a domain expert or external clinical")
    print("validation study — a token the system cannot self-issue.")
    print()
    print("  AEX: 'the computation was correct given the model.'")
    print("  ALR: 'the model is adequate AND the computation was correct.'")
    print("Without a ModelSpecificationToken, AEX is the ceiling.")
    print("─" * 80)


if __name__ == "__main__":
    main()
