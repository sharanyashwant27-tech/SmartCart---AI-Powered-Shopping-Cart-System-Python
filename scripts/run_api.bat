@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
if not exist .env copy .env.example .env

echo.
echo Starting SmartCart API on http://localhost:8904 ...
echo Swagger docs: http://localhost:8904/docs
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8904 --reload
