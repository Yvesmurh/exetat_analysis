#!/usr/bin/env bash
# Lightweight helper script to run the app from project root
set -euo pipefail

# Activate venv if present
if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Run the app as a module; this keeps imports consistent
python -m src.app.app
