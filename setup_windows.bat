@echo off
setlocal
echo === Student AI Placement Project Setup ===
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Setup complete. Edit .env with your MySQL credentials, create student_ai_db, then run:
echo   python ml\train_model.py
echo   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
echo In another terminal:
echo   cd frontend
echo   npm install
echo   npm run dev
pause
