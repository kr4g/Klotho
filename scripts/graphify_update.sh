#!/usr/bin/env bash
set -euo pipefail

# Refresh the Klotho code knowledge graph (AST-only, no API cost) and keep the
# output at the repo root in graphify-out/, while preserving the incremental
# SHA256 cache between runs.
#
# Usage:
#   bash scripts/graphify_update.sh            # update klotho/ package graph
#   GRAPHIFY_TARGET=klotho bash scripts/...     # override the scoped target dir

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KLOTHO_VENV:-$HOME/klotho-venv}"
TARGET="${GRAPHIFY_TARGET:-klotho}"

FINAL_DIR="$REPO_ROOT/graphify-out"
WORK_DIR="$REPO_ROOT/$TARGET/graphify-out"

if [[ -x "$VENV/bin/graphify" ]]; then
  GRAPHIFY=("$VENV/bin/graphify")
elif [[ -x "$VENV/bin/python" ]]; then
  GRAPHIFY=("$VENV/bin/python" -m graphify)
else
  GRAPHIFY=(python -m graphify)
fi

cd "$REPO_ROOT"

# Stage the existing graph (and its cache) where `graphify update <target>`
# expects it, so the rebuild is incremental rather than from scratch.
if [[ -d "$FINAL_DIR" ]]; then
  rm -rf "$WORK_DIR"
  mv "$FINAL_DIR" "$WORK_DIR"
fi

# AST-only rebuild: unset OPENAI_API_KEY so no LLM/billable calls can happen.
env -u OPENAI_API_KEY "${GRAPHIFY[@]}" update "$TARGET"

# Land the refreshed output back at the repo root.
rm -rf "$FINAL_DIR"
mv "$WORK_DIR" "$FINAL_DIR"

echo "graphify-out/ refreshed at repo root ($FINAL_DIR)"
