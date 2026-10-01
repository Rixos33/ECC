#!/bin/bash
# Render every script in parallel (5 at a time), then run QA.  Usage: ./render_all.sh [extra render args]
set -e
cd "$(dirname "$0")"
ls scripts/*.json | xargs -P 5 -I{} .venv/bin/python render_short.py {} out/ "$@"
.venv/bin/python qa.py "scripts/*.json" --out out 2>&1 | grep -v -i warning
