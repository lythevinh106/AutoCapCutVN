@echo off
echo === pyCapCut API Server ===
echo.

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo Starting server on port 8000...
echo.
python api_server.py

pause
