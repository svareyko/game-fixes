@echo off
title Cossacks Back to War - display and crash fix - APPLY
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython

echo Close Cossacks: Back to War before continuing.
echo.

rem The resolution can also be given on the command line: apply.bat 2560x1440
set "RES=%~1"
if defined RES goto run

echo Which resolution should MISSIONS run in? The menu is always 1024x768.
echo.
echo   Just press Enter = 1024x768, the safe choice that works on every monitor.
echo   Or type your own = WIDTHxHEIGHT, for example 2560x1440.
echo.
echo   Not sure? Run check.bat first - its last lines show the maximum for
echo   your monitor, and README.md explains how to choose. Nothing above the
echo   engine ceiling is ever written: the tool refuses and tells you why.
echo.
set /p "RES=Resolution, then Enter: "

:run
rem Forgive spaces and a capital X, so that 2560 X 1440 still works.
if defined RES set "RES=%RES: =%"
if defined RES set "RES=%RES:X=x%"
if not defined RES set "RES=1024x768"

echo.
%PY% patch.py apply --res "%RES%"
echo.
pause
exit /b

:nopython
echo.
echo   Python was not found on this computer.
echo.
echo   1. Download Python 3 from  https://www.python.org/downloads/
echo   2. During setup, TICK the box "Add python.exe to PATH"
echo   3. Close this window, open apply.bat again
echo.
pause
exit /b 1
