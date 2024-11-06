import os
import sys
import platform
import logging
from pathlib import Path
from typing import Dict, List, Optional

class PlatformUtils:
    """Platform-agnostic utility functions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.system = platform.system().lower()
        self.is_admin = self._check_admin_rights()
        
    def _check_admin_rights(self) -> bool:
        """Check for administrative privileges in a platform-agnostic way"""
        try:
            if self.system == 'windows':
                # Windows-specific check
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                # Unix-like systems (macOS, Linux)
                return os.geteuid() == 0
        except Exception as e:
            self.logger.warning(f"Could not check admin rights: {e}")
            return False
            
    def get_system_paths(self) -> Dict[str, Path]:
        """Get platform-specific system paths"""
        paths = {}
        
        if self.system == 'darwin':  # macOS
            paths.update({
                'system': Path('/System'),
                'applications': Path('/Applications'),
                'library': Path('/Library'),
                'user_library': Path.home() / 'Library',
                'temp': Path('/private/tmp')
            })
        elif self.system == 'linux':
            paths.update({
                'root': Path('/'),
                'bin': Path('/bin'),
                'usr': Path('/usr'),
                'etc': Path('/etc'),
                'var': Path('/var'),
                'tmp': Path('/tmp'),
                'opt': Path('/opt')
            })
        else:  # Windows or other
            system_drive = os.environ.get('SystemDrive', 'C:')
            paths.update({
                'system': Path(system_drive) / 'Windows',
                'program_files': Path(os.environ.get('ProgramFiles', 'C:/Program Files')),
                'temp': Path(os.environ.get('TEMP', 'C:/Windows/Temp'))
            })
            
        # Common paths for all platforms
        paths.update({
            'home': Path.home(),
            'documents': Path.home() / 'Documents',
            'downloads': Path.home() / 'Downloads'
        })
        
        return paths
        
    def get_critical_directories(self) -> List[Path]:
        """Get platform-specific critical directories to monitor"""
        if self.system == 'darwin':  # macOS
            return [
                Path('/System'),
                Path('/Library'),
                Path('/usr/local/bin'),
                Path('/private/etc'),
                Path.home() / 'Library'
            ]
        elif self.system == 'linux':
            return [
                Path('/bin'),
                Path('/sbin'),
                Path('/usr/bin'),
                Path('/usr/sbin'),
                Path('/etc'),
                Path('/lib'),
                Path('/usr/lib')
            ]
        else:  # Windows
            system_drive = os.environ.get('SystemDrive', 'C:')
            return [
                Path(system_drive) / 'Windows',
                Path(system_drive) / 'Windows/System32',
                Path(os.environ.get('ProgramFiles', 'C:/Program Files')),
                Path(os.environ.get('ProgramData', 'C:/ProgramData'))
            ]
            
    def get_startup_locations(self) -> List[Path]:
        """Get platform-specific startup locations"""
        if self.system == 'darwin':  # macOS
            return [
                Path.home() / 'Library/LaunchAgents',
                Path('/Library/LaunchAgents'),
                Path('/Library/LaunchDaemons'),
                Path('/System/Library/LaunchAgents'),
                Path('/System/Library/LaunchDaemons')
            ]
        elif self.system == 'linux':
            return [
                Path.home() / '.config/autostart',
                Path('/etc/xdg/autostart'),
                Path.home() / '.profile',
                Path.home() / '.bashrc',
                Path('/etc/profile')
            ]
        else:  # Windows
            startup_paths = []
            if 'APPDATA' in os.environ:
                startup_paths.append(
                    Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup'
                )
            if 'ProgramData' in os.environ:
                startup_paths.append(
                    Path(os.environ['ProgramData']) / 'Microsoft/Windows/Start Menu/Programs/Startup'
                )
            return startup_paths
            
    def scan_file(self, file_path: Path) -> Dict:
        """Platform-agnostic file scanning"""
        try:
            stat_info = file_path.stat()
            
            # Get Unix-style permissions for all platforms
            mode = stat_info.st_mode
            permissions = oct(mode)[-3:]
            
            # Get owner/group info
            if self.system != 'windows':
                import pwd
                import grp
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
                group = grp.getgrgid(stat_info.st_gid).gr_name
            else:
                owner = 'Unknown'
                group = 'Unknown'
                
            return {
                'path': str(file_path),
                'size': stat_info.st_size,
                'mode': mode,
                'permissions': permissions,
                'owner': owner,
                'group': group,
                'platform': self.system
            }
            
        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")
            return {
                'path': str(file_path),
                'error': str(e),
                'platform': self.system
            }