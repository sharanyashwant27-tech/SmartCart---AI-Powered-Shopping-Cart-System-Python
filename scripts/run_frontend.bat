@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
set SMARTCART_API_URL=http://127.0.0.1:8904/api/v1
echo Starting Streamlit frontend on http://localhost:8501 ...
streamlit run frontend/Home.py --server.port 8501
