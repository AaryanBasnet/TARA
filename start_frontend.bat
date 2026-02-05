@echo off
echo ========================================
echo    TIA Smart Arrival - Frontend
echo ========================================
echo.

cd frontend

echo Installing dependencies...
call npm install

echo.
echo Starting development server...
echo Frontend will be available at http://localhost:3000
echo.

call npm run dev
