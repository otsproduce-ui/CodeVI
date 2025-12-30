@echo off
echo Checking for processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
)
echo Port 8000 is now free.

