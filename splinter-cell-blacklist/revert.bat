@echo off
title Splinter Cell Blacklist - 30-minute crash fix - REVERT
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython

%PY% patch_pool_leak.py revert
echo.
pause
exit /b

:nopython
echo.
echo   Python 3 not found. Install it from https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH", then run this file again.
echo.
pause
exit /b 1
