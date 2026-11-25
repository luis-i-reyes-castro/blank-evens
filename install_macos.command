#!/bin/bash
# Install Python 3.11+ when it is missing, then install blank-evens into .venv.
set -euo pipefail

cd "$(dirname "$0")"

python_ok() {
    local candidate="$1"
    [[ -n "$candidate" && -x "$candidate" ]] || return 1
    "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
}

find_python() {
    local candidate
    local from_path
    from_path="$(command -v python3 2>/dev/null || true)"
    for candidate in \
        "${BLANK_EVENS_PYTHON:-}" \
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
        "/opt/homebrew/opt/python@3.13/bin/python3.13" \
        "/usr/local/opt/python@3.13/bin/python3.13" \
        "/opt/homebrew/bin/python3.13" \
        "/usr/local/bin/python3.13" \
        "$from_path"
    do
        if python_ok "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

install_python_pkg() {
    local listing pkg patch ver url tmpdir
    echo "Homebrew is not installed. Downloading Python 3.13 from python.org."
    echo "macOS will ask for an administrator password to finish the installer."
    listing="$(curl -fsSL https://www.python.org/downloads/macos/)"
    pkg="$(printf '%s\n' "$listing" | grep -oE 'python-3\.13\.[0-9]+-macos11\.pkg' || true)"
    pkg="$(
        printf '%s\n' "$pkg" \
            | awk -F '[.-]' '{ printf "%d %s\n", $4, $0 }' \
            | sort -n \
            | tail -n 1 \
            | awk '{ print $2 }'
    )"
    if [[ -z "$pkg" ]]; then
        echo "Could not find a Python 3.13 macOS package on python.org." >&2
        echo "Install Python from https://www.python.org/downloads/macos/ and run this again." >&2
        exit 1
    fi
    ver="${pkg#python-}"
    ver="${ver%-macos11.pkg}"
    url="https://www.python.org/ftp/python/${ver}/${pkg}"
    tmpdir="$(mktemp -d)"
    curl -fL "$url" -o "$tmpdir/python.pkg"
    sudo installer -pkg "$tmpdir/python.pkg" -target /
    rm -rf "$tmpdir"
}

PY=""
if PY="$(find_python)"; then
    echo "Using $PY"
else
    if command -v brew >/dev/null 2>&1; then
        echo "Installing Python 3.13 with Homebrew..."
        brew install python@3.13
        PY="$(brew --prefix python@3.13)/bin/python3.13"
    else
        install_python_pkg
        PY="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
    fi
fi

if ! python_ok "$PY"; then
    echo "Python 3.11 or newer is still not available at: $PY" >&2
    echo "Install it from https://www.python.org/downloads/macos/ and run this again." >&2
    exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
    "$PY" -m venv .venv
fi
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install .

echo
echo "Installed. From Terminal:"
echo "  ./blank_evens.sh document.pdf"
echo "Or drop documents onto blank_evens.command."
echo "PDF files need only this install. Word and PowerPoint also need LibreOffice or Microsoft Office."
