@echo off
cd /d "%~dp0"
echo Starting FM27 Recruitment Board (close this window to stop)...
python fm27.py --serve --open
pause
