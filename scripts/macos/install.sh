#!/bin/bash

# Check for root privileges
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Install Python package
pip3 install .

# Install launch agent
cp macos/com.antivirus.plist /Library/LaunchAgents/
launchctl load /Library/LaunchAgents/com.antivirus.plist

echo "Installation complete" 