#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[[ -f .env ]] || cp .env.example .env

echo "Starting SmartCart API on http://localhost:8904"
uvicorn app.main:app --host 0.0.0.0 --port 8904 --reload
