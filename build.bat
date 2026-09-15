@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Prefer the Windows Python launcher when it has Python 3.10 or newer.
where py >nul 2>nul
if errorlevel 1 goto try_python_command

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto try_python_command

py -3 "%~dp0build.py"
exit /b %ERRORLEVEL%

:try_python_command
where python >nul 2>nul
if errorlevel 1 goto python_not_found

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto python_not_found

python "%~dp0build.py"
exit /b %ERRORLEVEL%

:python_not_found
echo ERROR: Python 3.10 or newer was not found in PATH.
exit /b 1
