@echo off
echo ========================================
echo    TIA Smart Arrival - Backend
echo ========================================
echo.

echo Activating virtual environment...
call .venv\Scripts\activate

echo.
echo Installing backend dependencies...
pip install fastapi uvicorn python-multipart -q

echo.
echo Starting FastAPI server...
echo Backend will be available at http://localhost:8000
echo API docs at http://localhost:8000/docs
echo.

cd backend
python main.py
