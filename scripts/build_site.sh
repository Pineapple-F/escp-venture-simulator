#!/usr/bin/env bash
# Assemble the static asset directory served by the Cloudflare Worker.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf public
mkdir -p public/processed
cp -r demo/* public/
cp processed/patchtst_metrics.csv public/processed/
echo "public/ assembled: $(du -sh public | cut -f1)"
