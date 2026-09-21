@echo off
title Cossacks Back to War - display and crash fix - CHECK
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython

echo Read-only check - nothing will be modified.
echo.
%PY% patch.py status
echo.
pause
exit /b

:nopython
echo.
echo   Python was not found on this computer.
echo.
echo   1. Download Python 3 from  https://www.python.org/downloads/
echo   2. During setup, TICK the box "Add python.exe to PATH"
echo   3. Close this window, open check.bat again
echo.
pause
exit /b 1
