@echo off
cd /d "%~dp0"
echo === pyCapCut API Server (Production) ===
echo Working Directory: %CD%
echo.

REM Check if venv exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv
    echo Please create venv first: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment and run server
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if flask is installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [WARNING] Flask not installed. Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting server on port 8000 (Production Mode)...
echo Press Ctrl+C to stop the server
echo.

REM Run with waitress for production (if available), otherwise use flask
python -c "import waitress" 2>nul
if errorlevel 1 (
    REM Fallback to Flask dev server with threading
    set FLASK_ENV=production
    python api_server.py
) else (
    REM Use waitress for production
    python -c "from waitress import serve; from api_server import app; serve(app, host='0.0.0.0', port=8000)"
)

pause
