@echo off
echo ============================================
echo   Telegram Bot Dashboard - Starting Up
echo ============================================
echo.
echo [1/2] Starting API server on http://localhost:8000 ...
start "Bot API" cmd /k "python api.py"
timeout /t 2 /nobreak >nul
echo [2/2] Starting Dashboard UI on http://localhost:5173 ...
cd dashboard
start "Dashboard UI" cmd /k "npm run dev"
echo.
echo ============================================
echo   Dashboard: http://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo ============================================
echo.
echo Default password: admin123  (change it in Settings!)
echo.
pause
