@echo off
setlocal
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
python scripts\init_db.py
echo.
echo LAN mode starting on http://0.0.0.0:8000
echo Other machines should open http://YOUR-SERVER-IP:8000
echo Do not expose this directly to the public internet.
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8000
