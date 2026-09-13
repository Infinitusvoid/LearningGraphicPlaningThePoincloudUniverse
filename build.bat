@echo off
setlocal EnableExtensions

rem This file is intentionally tiny.
rem Its only job is to find Python 3 and start build.py beside this file.
rem All actual project build behavior lives in build.py.

set "BUILD_SCRIPT=%~dp0build.py"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%BUILD_SCRIPT%" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%BUILD_SCRIPT%" %*
    exit /b %ERRORLEVEL%
)

echo.
echo BUILD ERROR: Python 3 was not found in PATH.
echo Install Python 3, then run build.bat again.
pause
exit /b 1
