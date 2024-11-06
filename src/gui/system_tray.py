from PyQt6.QtWidgets import (QSystemTrayIcon, QMenu, QWidget, QDialog,
                           QVBoxLayout, QLabel, QProgressBar)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
from typing import Dict
from ..core.system_monitor import SystemMonitor
from pathlib import Path

class ResourceMonitorDialog(QDialog):
    """Dialog showing detailed resource usage"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Resources")
        self.setMinimumWidth(300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # CPU Usage
        self.cpu_label = QLabel("CPU Usage:")
        layout.addWidget(self.cpu_label)
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        layout.addWidget(self.cpu_bar)
        
        # Memory Usage
        self.memory_label = QLabel("Memory Usage:")
        layout.addWidget(self.memory_label)
        
        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        layout.addWidget(self.memory_bar)
        
        # Disk Space
        self.disk_label = QLabel("Disk Space:")
        layout.addWidget(self.disk_label)
        
        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        layout.addWidget(self.disk_bar)
        
        # Temperature (if available)
        self.temp_label = QLabel("CPU Temperature: N/A")
        layout.addWidget(self.temp_label)
        
        # Status
        self.status_label = QLabel("System Status: Healthy")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
    def update_stats(self, stats: Dict):
        """Update displayed statistics"""
        # Update CPU
        self.cpu_bar.setValue(int(stats['cpu_percent']))
        self.cpu_label.setText(f"CPU Usage: {stats['cpu_percent']:.1f}%")
        
        # Update Memory
        self.memory_bar.setValue(int(stats['memory_percent']))
        self.memory_label.setText(
            f"Memory Usage: {stats['memory_usage_mb']:.1f}MB ({stats['memory_percent']:.1f}%)"
        )
        
        # Update Disk
        self.disk_bar.setValue(int(stats['disk_percent']))
        self.disk_label.setText(
            f"Free Disk Space: {stats['disk_space_gb']:.1f}GB ({100-stats['disk_percent']:.1f}% free)"
        )
        
        # Update Temperature
        if stats['cpu_temperature'] is not None:
            self.temp_label.setText(f"CPU Temperature: {stats['cpu_temperature']:.1f}°C")
        
        # Update Status
        status = stats['status']
        status_text = f"System Status: {status.title()}"
        if status == 'critical':
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        elif status == 'warning':
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.status_label.setText(status_text)
        
        # Update progress bar colors
        for bar in [self.cpu_bar, self.memory_bar, self.disk_bar]:
            value = bar.value()
            if value >= 90:
                bar.setStyleSheet("""
                    QProgressBar::chunk { background-color: red; }
                """)
            elif value >= 70:
                bar.setStyleSheet("""
                    QProgressBar::chunk { background-color: orange; }
                """)
            else:
                bar.setStyleSheet("""
                    QProgressBar::chunk { background-color: green; }
                """)

class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon with resource monitoring"""
    
    def __init__(self, system_monitor: SystemMonitor, parent: QWidget = None):
        super().__init__(parent)
        self.system_monitor = system_monitor
        self.resource_dialog = None
        
        # Use a default icon if custom icon is not found
        icon_path = Path("icons/antivirus.png")
        if not icon_path.exists():
            # Create a default icon using Qt
            from PyQt6.QtGui import QIcon, QPixmap
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.blue)
            self.setIcon(QIcon(pixmap))
        else:
            self.setIcon(QIcon(str(icon_path)))
        self.setToolTip("AntiVirus Scanner")
        
        # Create context menu
        self.menu = QMenu()
        self.create_menu()
        self.setContextMenu(self.menu)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(2000)  # Update every 2 seconds
        
        # Show initial status
        self.update_status()
        
    def create_menu(self):
        """Create the system tray context menu"""
        # Show main window action
        show_action = self.menu.addAction("Show Main Window")
        show_action.triggered.connect(self.parent().show)
        
        # Show resource monitor action
        monitor_action = self.menu.addAction("Resource Monitor")
        monitor_action.triggered.connect(self.show_resource_monitor)
        
        self.menu.addSeparator()
        
        # Exit action
        exit_action = self.menu.addAction("Exit")
        exit_action.triggered.connect(self.parent().close)
        
    def show_resource_monitor(self):
        """Show the resource monitor dialog"""
        if not self.resource_dialog:
            self.resource_dialog = ResourceMonitorDialog(self.parent())
        self.resource_dialog.show()
        self.resource_dialog.activateWindow()
        
    def update_status(self):
        """Update system status and tooltip"""
        stats = self.system_monitor.get_health_status()
        
        # Update tooltip with basic stats
        tooltip = (
            f"CPU: {stats['cpu_percent']:.1f}%\n"
            f"Memory: {stats['memory_percent']:.1f}%\n"
            f"Disk Free: {stats['disk_space_gb']:.1f}GB"
        )
        self.setToolTip(tooltip)
        
        # Update resource dialog if visible
        if self.resource_dialog and self.resource_dialog.isVisible():
            self.resource_dialog.update_stats(stats)
            
        # Show notification if system status is critical
        if stats['status'] == 'critical' and not hasattr(self, '_last_critical_notification'):
            self.showMessage(
                "System Resources Critical",
                "System resources are running low. Consider closing some applications.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000  # Show for 5 seconds
            )
            self._last_critical_notification = True
        elif stats['status'] != 'critical':
            self._last_critical_notification = False 