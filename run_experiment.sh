#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
if command -v uv >/dev/null 2>&1; then
  exec uv run --python 3.12 python -m parliament_ai_study.run_experiment "$@"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  exec "$SCRIPT_DIR/.venv/bin/python" -m parliament_ai_study.run_experiment "$@"
else
  echo "Install uv or create .venv with the project dependencies before running the experiment." >&2
  exit 2
fi
