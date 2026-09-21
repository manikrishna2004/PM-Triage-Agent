@echo off
REM Infiheal Daily Digest Automation Launcher
REM This script runs the Python automation at a scheduled time

cd /D C:\Users\bmani\Downloads\Infiheal-Agent

REM Activate virtual environment if you have one (optional)
REM call venv\Scripts\activate.bat

REM Run the Python script
python infiheal_daily_automation.py

REM Log execution time
echo [%date% %time%] Infiheal digest automation executed >> infiheal_task_log.txt

pause
