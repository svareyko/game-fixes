@echo off
title Cossacks Back to War - display and crash fix - REVERT
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython

echo Close Cossacks: Back to War before continuing.
echo Restoring the original game files and mode.dat, removing the DPI flag.
echo.
%PY% patch.py revert
echo.
pause
exit /b

:nopython
echo.
echo   Python was not found on this computer.
echo.
echo   1. Download Python 3 from  https://www.python.org/downloads/
echo   2. During setup, TICK the box "Add python.exe to PATH"
echo   3. Close this window, open revert.bat again
echo.
pause
exit /b 1
