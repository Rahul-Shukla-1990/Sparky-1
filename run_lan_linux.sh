#!/usr/bin/env bash
set -e
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
echo "LAN mode starting on http://0.0.0.0:8000"
echo "Other machines should open http://YOUR-SERVER-IP:8000"
echo "Do not expose this directly to the public internet."
uvicorn app.main:app --host 0.0.0.0 --port 8000
