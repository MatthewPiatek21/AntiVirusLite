import os
import sys
import platform
from setuptools import setup, find_packages
from pathlib import Path

def get_platform_requirements():
    """Get platform-specific package requirements"""
    system = platform.system().lower()
    
    common_requirements = [
        'PyQt6>=6.4.0',
        'PyQt6-Charts>=6.4.0',
        'psutil>=5.9.0',
        'cryptography>=3.4.7',
        'aiohttp>=3.8.1',
        'schedule>=1.1.0',
        'requests>=2.26.0'
    ]
    
    platform_requirements = {
        'windows': [
            'pywin32>=228',
            'wmi>=1.5.1',
            'winreg>=0.1.1'
        ],
        'darwin': [
            'pyobjc-framework-Cocoa>=8.0',
            'pyobjc-framework-SystemConfiguration>=8.0'
        ],
        'linux': [
            'dbus-python>=1.2.18',
            'python-xlib>=0.31'
        ]
    }
    
    return common_requirements + platform_requirements.get(system, [])

def get_platform_data_files():
    """Get platform-specific data files"""
    system = platform.system().lower()
    base_files = [
        ('icons', ['icons/antivirus.png']),
        ('data', ['data/signatures.json']),
    ]
    
    platform_files = {
        'windows': [
            ('', ['windows/antivirus.ico']),
            ('scripts', ['windows/install_service.bat', 'windows/uninstall_service.bat'])
        ],
        'darwin': [
            ('', ['macos/antivirus.icns']),
            ('scripts', ['macos/com.antivirus.plist'])
        ],
        'linux': [
            ('', ['linux/antivirus.svg']),
            ('scripts', ['linux/antivirus.service', 'linux/install.sh'])
        ]
    }
    
    return base_files + platform_files.get(system, [])

def get_platform_scripts():
    """Get platform-specific scripts"""
    system = platform.system().lower()
    
    scripts = {
        'windows': ['scripts/windows/antivirus.bat'],
        'darwin': ['scripts/macos/antivirus.sh'],
        'linux': ['scripts/linux/antivirus.sh']
    }
    
    return scripts.get(system, [])

setup(
    name='AntiVirusLite',
    version='0.1.0',
    description='A cross-platform antivirus solution',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    install_requires=get_platform_requirements(),
    data_files=get_platform_data_files(),
    scripts=get_platform_scripts(),
    entry_points={
        'console_scripts': [
            'antivirus=src.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Security',
    ],
    python_requires='>=3.8',
) 