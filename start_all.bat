@echo off
echo ========================================
echo    TIA Smart Arrival Ecosystem
echo    Starting Full Stack Application
echo ========================================
echo.

echo [1/2] Starting Backend (FastAPI)...
start "TIA Backend" cmd /k "call start_backend.bat"

echo Waiting for backend to initialize...
timeout /t 5 /nobreak > nul

echo [2/2] Starting Frontend (React)...
start "TIA Frontend" cmd /k "call start_frontend.bat"

echo.
echo ========================================
echo    All services starting!
echo ========================================
echo.
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit this window...
pause > nul
