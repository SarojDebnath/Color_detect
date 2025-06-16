@echo off
title LED Test Controller - Web GUI
cls
echo.
echo ========================================================
echo    LED Test Controller - Web GUI
echo ========================================================
echo.
echo Activating conda environment: test_env
echo.

cd /d "%~dp0"

REM Initialize conda first
call C:\Users\sarojd\AppData\Local\anaconda3\condabin\activate

REM Activate conda environment
call conda activate test_env
if errorlevel 1 (
    echo.
    echo ERROR: Failed to activate conda environment 'test_env'
    echo Please make sure conda is installed and 'test_env' environment exists.
    echo.
    pause
    exit /b 1
)

echo.
echo Starting application...
echo.

python start_gui.py

echo.
echo Application stopped.
pause 