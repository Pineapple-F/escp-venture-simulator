#!/usr/bin/env bash
# Assemble the static asset directory served by the Cloudflare Worker.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/build_site.py
