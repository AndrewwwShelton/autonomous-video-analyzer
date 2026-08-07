@echo off
REM ============================================================
REM  AdSafe Studio - one-click demo launcher
REM  Double-click this file. It starts the app and opens the browser.
REM ============================================================
title AdSafe Studio - demo server
cd /d "%~dp0"

echo.
echo   Autonomous Video Ad-Placement ^& Contextual Safety Analyzer
echo   ---------------------------------------------------------
echo.

REM --- make sure the built front end exists (served by the API on one port)
if not exist "frontend\dist\index.html" (
    echo   Building the interface, one moment...
    call npm run build --prefix frontend
    if errorlevel 1 goto :buildfail
)

REM --- refuse to start a second server on the same port. The app opens the
REM     database when it is imported, before uvicorn binds, so a copy that loses
REM     the port still holds data\audit.db -- serving nothing while blocking
REM     demo_setup.py. Catch it here rather than leave a confusing half-state.
netstat -ano | findstr /r /c:"LISTENING" | findstr /c:":8000 " >nul
if not errorlevel 1 (
    echo   Something is already listening on port 8000.
    echo.
    echo   That is probably an AdSafe server you already started. Use it, or
    echo   close its window and run this again. Starting a second copy would
    echo   lock the database without serving anything.
    echo.
    pause
    goto :eof
)

echo   Starting server on http://localhost:8000
echo.
echo   Leave this window OPEN during the presentation.
echo   Close it when you are finished.
echo.

REM --- give the server a moment, then open the browser
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:8000"

python -m uvicorn backend.main:app --port 8000
goto :eof

:buildfail
echo.
echo   Build failed. Run this once in a terminal, then try again:
echo       npm install --prefix frontend
echo.
pause
