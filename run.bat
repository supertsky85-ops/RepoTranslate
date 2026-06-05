@echo off
cd /d %~dp0

echo ============================================
echo   RepoTranslate v0.1.0
echo ============================================

REM Check venv
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run: python -m venv .venv
    echo          Then: .venv\Scripts\activate.bat ^&^& pip install fastapi uvicorn httpx pydantic-settings aiosqlite jinja2 python-multipart
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate venv
    pause
    exit /b 1
)

echo.
echo   Server: http://127.0.0.1:9000/
echo   Press Ctrl+C to stop
echo.
uvicorn app.main:app --host 127.0.0.1 --port 9000
pause
