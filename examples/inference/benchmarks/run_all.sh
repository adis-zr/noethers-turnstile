#!/usr/bin/env bash
# Single entry point: run all benchmarks, generate results and figures.
# Usage: ./benchmarks/run_all.sh [python_executable]
# Default python: python3

set -e
cd "$(dirname "$0")/.."   # run from experiments/inference/

PYTHON="${1:-python3}"
BENCH="benchmarks"

echo "================================================"
echo "  Compiler Benchmark Suite"
echo "  Python: $PYTHON"
echo "================================================"

echo ""
echo "── Scaling Claims ──────────────────────────────"
$PYTHON $BENCH/scaling/bench_mn_surface.py
$PYTHON $BENCH/scaling/bench_problem_size.py
$PYTHON $BENCH/scaling/bench_density.py
$PYTHON $BENCH/scaling/bench_expiry.py

echo ""
echo "── Degenerate Cases ────────────────────────────"
$PYTHON $BENCH/degenerate/bench_empty_context.py
$PYTHON $BENCH/degenerate/bench_single_bit.py
$PYTHON $BENCH/degenerate/bench_single_level.py
$PYTHON $BENCH/degenerate/bench_contradictory.py

echo ""
echo "── Figures ─────────────────────────────────────"
$PYTHON $BENCH/figures/fig_mn_surface.py
$PYTHON $BENCH/figures/fig_problem_size_ratio.py
$PYTHON $BENCH/figures/fig_density_scan_depth.py
$PYTHON $BENCH/figures/fig_expiry_sequence.py

echo ""
echo "================================================"
echo "  All benchmarks complete."
echo "  Results: benchmarks/results/"
echo "  Figures: benchmarks/figures/*.png"
echo "================================================"
