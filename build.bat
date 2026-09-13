@echo off

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0build.py"
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0build.py"
    exit /b %ERRORLEVEL%
)

echo ERROR: Python 3 was not found in PATH.
pause
exit /b 1
