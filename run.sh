#!/usr/bin/env bash
# LexAgent - Instalador y arranque (Linux/macOS)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[ERROR] Python no esta instalado." >&2
  exit 1
fi
exec "$PY" "$DIR/install.py" "$@"
