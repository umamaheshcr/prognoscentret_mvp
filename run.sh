#!/usr/bin/env bash
# Mimir MVP - one command. Creates the venv on first run, then serves.
#
# No Docker, no Databricks, no database, no API key. Plain Python.
#
# Every candidate is probed by actually running it rather than trusted from
# `command -v`. On Windows the Microsoft Store build installs an execution alias
# that `command -v` misses even though the binary runs, and this script used to
# report "Python not found" with Python sitting right there.
set -euo pipefail
cd "$(dirname "$0")"

works() {
  local exe="$1"
  [ -z "$exe" ] && return 1
  local v
  v=$("$exe" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null) || return 1
  [ -z "$v" ] && return 1
  local maj=${v%%.*} min=${v##*.}
  if [ "$maj" -lt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -lt 11 ]; }; then
    echo "  found Python $v at $exe - too old, need 3.11+" >&2
    return 1
  fi
  PY_VERSION="$v"
  return 0
}

PY=""
CANDIDATES=(python3 python py)
# Windows Store alias and the usual per-user install location
if [ -n "${LOCALAPPDATA:-}" ]; then
  CANDIDATES+=("$LOCALAPPDATA/Microsoft/WindowsApps/python.exe")
  for d in "$LOCALAPPDATA"/Programs/Python/*/python.exe; do
    [ -x "$d" ] && CANDIDATES+=("$d")
  done
fi
CANDIDATES+=(/usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3)

for c in "${CANDIDATES[@]}"; do
  if command -v "$c" >/dev/null 2>&1; then c=$(command -v "$c"); fi
  if [ -x "$c" ] || command -v "$c" >/dev/null 2>&1; then
    if works "$c"; then PY="$c"; break; fi
  fi
done

if [ -z "$PY" ]; then
  cat >&2 <<'EOF'

Python 3.11 or newer was not found.

  macOS         brew install python@3.13
  Debian/Ubuntu sudo apt install python3 python3-venv
  Windows       winget install Python.Python.3.13   (then open a new terminal)

Already installed? Print the path and tell me what it says:
  command -v python3 python py
EOF
  exit 1
fi

echo "Python $PY_VERSION - $PY"

BIN=".venv/bin"
[ -d ".venv/Scripts" ] && BIN=".venv/Scripts"

if [ ! -x "$BIN/python" ] && [ ! -x "$BIN/python.exe" ]; then
  echo "Creating .venv (first run only)..."
  "$PY" -m venv .venv
  BIN=".venv/bin"; [ -d ".venv/Scripts" ] && BIN=".venv/Scripts"
  "$BIN/python" -m pip install --quiet --upgrade pip
  echo "Installing five dependencies (about a minute)..."
  "$BIN/python" -m pip install --quiet -r requirements.txt
fi

# Verify before serving, so a half-finished install fails here with a clear
# message rather than as a blank page in the browser.
if ! "$BIN/python" -c "import fastapi, uvicorn, pandas, numpy, openpyxl" 2>/dev/null; then
  echo "The virtual environment is incomplete - the first install was probably" >&2
  echo "interrupted. Delete .venv and run ./run.sh again." >&2
  exit 1
fi

PORT="${MIMIR_PORT:-8000}"
echo
echo "  Mimir MVP - Denmark, September 2026"
echo "  http://127.0.0.1:$PORT    (Ctrl+C to stop)"
echo
exec "$BIN/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
