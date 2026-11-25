#!/bin/bash
# macOS drop target. Finder passes each dropped file as its own argument.
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Drop one or more documents onto this file."
    echo
    read -r -p "Press Return to close." _
    exit 1
fi

"$ROOT/blank_evens.sh" "$@"
status=$?
echo
read -r -p "Press Return to close." _
exit "$status"
