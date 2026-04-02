#!/usr/bin/env bash
set -euo pipefail
PIPE="$(cd "$(dirname "$0")" && pwd)"
EXP="$(cd "$PIPE/.." && pwd)"
rm -rf "${PIPE}/output"/*
mkdir -p "${PIPE}/.cache/fontconfig" "${PIPE}/.mplconfig"
export XDG_CACHE_HOME="${PIPE}/.cache"
export MPLCONFIGDIR="${PIPE}/.mplconfig"
# shellcheck source=/dev/null
source "${HOME}/klotho-venv/bin/activate"
cd "${EXP}"
export PYTHONPATH=.
python notation_pipeline/render_examples.py
python notation_pipeline/render_containers.py
python notation_pipeline/render_comparison.py
python notation_pipeline/render_barline_splits.py
python notation_pipeline/render_span_edge_cases.py
echo "Done. PNGs under ${PIPE}/output/"
