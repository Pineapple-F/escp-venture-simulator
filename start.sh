#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/market-simulator"

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.12)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "未找到 Python 3，请先安装 Python 3.10 或更高版本。" >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("需要 Python 3.10 或更高版本。")
PY

if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

if ! .venv/bin/python -c 'import duckdb' >/dev/null 2>&1; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

echo "创投模拟器：http://127.0.0.1:${MARKET_PORT:-8790}"
exec .venv/bin/python server.py
