@echo off
echo Installing AntiVirus Service...

:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Administrator privileges required.
    echo Please run as administrator.
    pause
    exit /b 1
)

:: Create service
sc create AntiVirusService binPath= "%~dp0\antivirus.exe" start= auto
sc description AntiVirusService "AntiVirus Protection Service"
sc start AntiVirusService

echo Service installed successfully.
pause 