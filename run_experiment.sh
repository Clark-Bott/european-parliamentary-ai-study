#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  exec "$SCRIPT_DIR/.venv/bin/python" -m parliament_ai_study.run_experiment "$@"
elif command -v uv >/dev/null 2>&1; then
  exec uv run --python 3.12 python -m parliament_ai_study.run_experiment "$@"
else
  exec python3 -m parliament_ai_study.run_experiment "$@"
fi
