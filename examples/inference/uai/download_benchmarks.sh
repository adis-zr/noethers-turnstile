#!/usr/bin/env bash
# Download and extract the UAI 2022 tuning benchmarks (PR task, which contains
# the full problem set including MAR-compatible models).
#
# Source: https://www.ics.uci.edu/~dechter/uaicompetition/2022/TuningBenchmarks/
# Citation: Ihler et al., UAI 2014 competition problem sets.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"

mkdir -p "$DATA_DIR"

if [ -d "$DATA_DIR/PR" ] && [ "$(ls -A "$DATA_DIR/PR"/*.uai 2>/dev/null | wc -l)" -gt 10 ]; then
    echo "PR benchmark already extracted at $DATA_DIR/PR — skipping download."
    exit 0
fi

echo "Downloading PR.zip (~6.4 MB)..."
curl -L -o "$DATA_DIR/PR.zip" \
    "https://ics.uci.edu/~dechter/uaicompetition/2022/TuningBenchmarks/PR.zip"

echo "Extracting..."
unzip -o "$DATA_DIR/PR.zip" -d "$DATA_DIR"
rm "$DATA_DIR/PR.zip"

N=$(ls "$DATA_DIR/PR"/*.uai 2>/dev/null | wc -l | tr -d ' ')
echo "Done. $N .uai model files in $DATA_DIR/PR/"
