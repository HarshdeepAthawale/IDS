@echo off
echo Starting IDS Development Environment
echo =====================================
echo.

echo Starting Flask Backend...
start "Flask Backend" cmd /k "cd backend && python app.py"
timeout /t 3 /nobreak > nul

echo.
echo Starting Next.js Frontend...
start "Next.js Frontend" cmd /k "npm run dev"

echo.
echo Both services are starting up...
echo.
echo Flask Backend: http://localhost:3002
echo Next.js Frontend: http://localhost:3001
echo.
echo Press any key to exit...
pause > nul
