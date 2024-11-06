import os
import sys
import platform
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

# Global flag for platform detection
IS_WINDOWS = platform.system().lower() == 'windows'
IS_MACOS = platform.system().lower() == 'darwin'
IS_LINUX = platform.system().lower() == 'linux'

class SecurityHandler:
    """Handle platform-specific security operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform = platform.system().lower()
        
    def get_file_permissions(self, path: Path) -> Dict:
        """Get file permissions in a platform-agnostic way"""
        try:
            stat_info = path.stat()
            
            if IS_MACOS or IS_LINUX:
                import pwd
                import grp
                return {
                    'owner': pwd.getpwuid(stat_info.st_uid).pw_name,
                    'group': grp.getgrgid(stat_info.st_gid).gr_name,
                    'mode': stat_info.st_mode,
                    'permissions': oct(stat_info.st_mode)[-3:]
                }
            else:  # Windows or other platforms
                return {
                    'mode': stat_info.st_mode,
                    'permissions': oct(stat_info.st_mode)[-3:],
                    'platform': self.platform
                }
                
        except Exception as e:
            self.logger.error(f"Error getting file permissions for {path}: {e}")
            return {
                'error': str(e),
                'mode': getattr(stat_info, 'st_mode', None)
            }

class PlatformAdapter:
    """Platform-specific adaptations and utilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform = self._detect_platform()
        self.system_paths = self._get_system_paths()
        self.security = SecurityHandler()
        
    def _detect_platform(self) -> Dict[str, str]:
        """Detect current platform and capabilities"""
        system = platform.system().lower()
        
        # Platform-specific root check
        has_root = None
        if not IS_WINDOWS:
            try:
                has_root = os.geteuid() == 0
            except AttributeError:
                has_root = False
        
        return {
            'system': system,
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'python_version': platform.python_version(),
            'is_64bit': sys.maxsize > 2**32,
            'has_root': has_root,
            'temp_dir': self._get_temp_dir(),
            'user_home': str(Path.home())
        }
        
    def _get_system_paths(self) -> Dict[str, Path]:
        """Get platform-specific system paths"""
        paths = {}
        
        if IS_MACOS:
            # macOS paths
            paths.update({
                'system': Path('/System'),
                'applications': Path('/Applications'),
                'library': Path('/Library'),
                'user_library': Path.home() / 'Library',
                'temp': Path('/private/tmp')
            })
        elif IS_LINUX:
            # Linux paths
            paths.update({
                'root': Path('/'),
                'bin': Path('/bin'),
                'usr': Path('/usr'),
                'etc': Path('/etc'),
                'var': Path('/var'),
                'tmp': Path('/tmp'),
                'opt': Path('/opt')
            })
            
        # Common paths
        paths.update({
            'home': Path.home(),
            'documents': Path.home() / 'Documents',
            'downloads': Path.home() / 'Downloads'
        })
        
        return paths
        
    def _get_temp_dir(self) -> str:
        """Get platform-specific temporary directory"""
        if IS_MACOS:
            return '/private/tmp'
        elif IS_LINUX:
            return '/tmp'
        return str(Path.home() / 'temp')
        
    def get_startup_locations(self) -> List[Path]:
        """Get platform-specific startup locations"""
        locations = []
        
        if IS_MACOS:
            # macOS startup locations
            startup_paths = [
                Path.home() / 'Library' / 'LaunchAgents',
                Path('/Library/LaunchAgents'),
                Path('/Library/LaunchDaemons'),
                Path('/System/Library/LaunchAgents'),
                Path('/System/Library/LaunchDaemons')
            ]
            locations.extend(startup_paths)
        elif IS_LINUX:
            # Linux startup locations
            startup_paths = [
                Path.home() / '.config' / 'autostart',
                Path('/etc/xdg/autostart'),
                Path.home() / '.profile',
                Path.home() / '.bashrc',
                Path('/etc/profile')
            ]
            locations.extend(startup_paths)
            
        return locations
        
    def get_process_info(self, pid: int) -> Optional[Dict]:
        """Get platform-specific process information"""
        try:
            import psutil
            process = psutil.Process(pid)
            
            return {
                'name': process.name(),
                'exe': process.exe(),
                'cmdline': process.cmdline(),
                'username': process.username(),
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'status': process.status(),
                'create_time': process.create_time()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting process info for PID {pid}: {e}")
            return None
            
    def get_file_permissions(self, path: Path) -> Dict:
        """Get platform-specific file permissions"""
        return self.security.get_file_permissions(path)