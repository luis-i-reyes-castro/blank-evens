#!/usr/bin/env bash
# Insert blank reverses. Paths are passed through quoted, including spaces.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: blank_evens.sh FILE [FILE ...]" >&2
    echo "Drop files onto blank_evens.command on macOS, or pass paths here." >&2
    exit 1
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
else
    echo "Python 3.11 or newer was not found." >&2
    echo "macOS: double-click install_macos.command" >&2
    echo "Linux: python3 -m venv .venv && .venv/bin/python -m pip install ." >&2
    exit 1
fi

exec "$PY" "$ROOT/blank_evens.py" "$@"
