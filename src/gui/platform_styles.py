from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
import platform
import sys
import os
import subprocess

class PlatformStyles:
    """Platform-specific styling and adaptations"""
    
    @staticmethod
    def get_platform() -> str:
        """Get current platform"""
        system = platform.system().lower()
        if system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        return 'windows'
        
    @staticmethod
    def apply_platform_style(widget: QWidget):
        """Apply platform-specific styling"""
        platform_name = PlatformStyles.get_platform()
        
        if platform_name == 'macos':
            PlatformStyles._apply_macos_style(widget)
        elif platform_name == 'linux':
            PlatformStyles._apply_linux_style(widget)
        else:
            PlatformStyles._apply_default_style(widget)
            
    @staticmethod
    def _apply_macos_style(widget: QWidget):
        """Apply macOS-specific styling"""
        widget.setStyleSheet("""
            QMainWindow {
                background-color: #F0F0F0;
            }
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
            QTabWidget::pane {
                border: 1px solid #C8C8C8;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #E8E8E8;
                border: 1px solid #C8C8C8;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
            }
            QTabBar::tab:selected {
                background-color: white;
            }
        """)
        
    @staticmethod
    def _apply_linux_style(widget: QWidget):
        """Apply Linux-specific styling"""
        # Use system theme colors when possible
        palette = widget.palette()
        
        # Set up dark/light mode based on system theme
        if PlatformStyles._is_dark_mode():
            widget.setStyleSheet("""
                QMainWindow {
                    background-color: #2E3440;
                    color: #ECEFF4;
                }
                QPushButton {
                    background-color: #5E81AC;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #81A1C1;
                }
                QPushButton:pressed {
                    background-color: #4C566A;
                }
                QTabWidget::pane {
                    border: 1px solid #4C566A;
                }
                QTabBar::tab {
                    background-color: #3B4252;
                    border: 1px solid #4C566A;
                    color: #ECEFF4;
                    padding: 8px 16px;
                }
                QTabBar::tab:selected {
                    background-color: #434C5E;
                }
            """)
        else:
            widget.setStyleSheet("""
                QMainWindow {
                    background-color: #F8F9FB;
                }
                QPushButton {
                    background-color: #5294E2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #73B2F5;
                }
                QPushButton:pressed {
                    background-color: #3D7ACC;
                }
                QTabWidget::pane {
                    border: 1px solid #DAE1E7;
                }
                QTabBar::tab {
                    background-color: #EFF0F1;
                    border: 1px solid #DAE1E7;
                    padding: 8px 16px;
                }
                QTabBar::tab:selected {
                    background-color: white;
                }
            """)
            
    @staticmethod
    def _apply_default_style(widget: QWidget):
        """Apply default styling for other platforms"""
        widget.setStyleSheet("""
            QMainWindow {
                background-color: #F0F0F0;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 16px;
            }
            QTabWidget::pane {
                border: 1px solid #CCCCCC;
            }
            QTabBar::tab {
                background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                padding: 8px 16px;
            }
        """)
            
    @staticmethod
    def _is_dark_mode() -> bool:
        """Detect if system is using dark mode"""
        if sys.platform == 'darwin':
            try:
                # Use macOS defaults command to check dark mode
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip() == 'Dark'
            except:
                return False
        elif sys.platform == 'linux':
            # Linux dark mode detection (basic)
            try:
                if 'GTK_THEME' in os.environ:
                    return 'dark' in os.environ['GTK_THEME'].lower()
                return False
            except:
                return False
        return False
                
    @staticmethod
    def get_platform_font():
        """Get platform-specific default font"""
        platform_name = PlatformStyles.get_platform()
        
        if platform_name == 'macos':
            return {
                'family': '.AppleSystemUIFont',
                'size': 13
            }
        elif platform_name == 'linux':
            return {
                'family': 'Ubuntu',
                'size': 10
            }
        else:
            return {
                'family': 'Arial',
                'size': 9
            } 