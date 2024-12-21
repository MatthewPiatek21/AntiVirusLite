#!/bin/bash

# Check for root privileges
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Install system dependencies
if [ -f /etc/debian_version ]; then
    apt-get update
    apt-get install -y python3-dev python3-pip libdbus-1-dev
elif [ -f /etc/redhat-release ]; then
    dnf install -y python3-devel python3-pip dbus-devel
fi

# Install Python package
pip3 install .

# Install systemd service
cp linux/antivirus.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable antivirus
systemctl start antivirus

echo "Installation complete" 