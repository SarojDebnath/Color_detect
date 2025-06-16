@echo off
title LED Test Controller - Modern Web GUI
cls
echo.
echo ========================================================
echo    LED Test Controller - Modern Web GUI
echo ========================================================
echo.
echo Starting application...
echo.

cd /d "%~dp0"
python start_gui.py

echo.
echo Application stopped.
pause 