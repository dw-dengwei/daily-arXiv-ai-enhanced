#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

if [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
    python scripts/test_llm.py "$@"
elif command -v uv >/dev/null 2>&1; then
    uv run --python 3.12 python scripts/test_llm.py "$@"
elif command -v python >/dev/null 2>&1; then
    python scripts/test_llm.py "$@"
else
    python3 scripts/test_llm.py "$@"
fi
