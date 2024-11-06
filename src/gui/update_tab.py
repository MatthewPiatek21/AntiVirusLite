from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QProgressBar, QMessageBox, QTimeEdit, QCheckBox, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from datetime import datetime
from ..core.updater import SignatureUpdater

class UpdateTab(QWidget):
    def __init__(self, updater: SignatureUpdater):
        super().__init__()
        self.updater = updater
        
        # Connect update signals
        self.updater.update_progress.connect(self.update_progress)
        self.updater.update_complete.connect(self.update_completed)
        
        self.init_ui()
        
        # Set up auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_for_updates)
        self.update_timer.start(3600000)  # Check every hour
        
        # Add schedule configuration section
        self.init_schedule_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Status section
        status_layout = QVBoxLayout()
        self.version_label = QLabel('Current Version: Unknown')
        self.last_update_label = QLabel('Last Update: Never')
        self.next_update_label = QLabel('Next Update: Not Scheduled')
        self.signatures_count_label = QLabel('Signatures: 0')
        
        status_layout.addWidget(self.version_label)
        status_layout.addWidget(self.last_update_label)
        status_layout.addWidget(self.next_update_label)
        status_layout.addWidget(self.signatures_count_label)
        
        layout.addLayout(status_layout)
        
        # Update progress
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.check_button = QPushButton('Check for Updates')
        self.check_button.clicked.connect(self.check_for_updates)
        button_layout.addWidget(self.check_button)
        
        self.force_update_button = QPushButton('Force Update')
        self.force_update_button.clicked.connect(lambda: self.check_for_updates(force=True))
        button_layout.addWidget(self.force_update_button)
        
        layout.addLayout(button_layout)
        
        # Initial status update
        self.update_status()
        
        # Add detailed progress section
        progress_group = QGroupBox("Update Progress")
        progress_layout = QVBoxLayout()
        
        self.operation_label = QLabel("Ready")
        progress_layout.addWidget(self.operation_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.detail_label = QLabel()
        progress_layout.addWidget(self.detail_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
    def init_schedule_ui(self):
        """Initialize update schedule configuration UI"""
        schedule_group = QGroupBox("Update Schedule")
        schedule_layout = QFormLayout()
        
        # Daily updates toggle
        self.daily_check = QCheckBox("Enable Daily Updates")
        self.daily_check.setChecked(self.updater.update_schedule['daily'])
        self.daily_check.stateChanged.connect(self.update_schedule)
        schedule_layout.addRow("Daily Updates:", self.daily_check)
        
        # Update time
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        current_time = datetime.strptime(
            self.updater.update_schedule['time'], 
            "%H:%M"
        ).time()
        self.time_edit.setTime(current_time)
        self.time_edit.timeChanged.connect(self.update_schedule)
        schedule_layout.addRow("Update Time:", self.time_edit)
        
        # Next update info
        self.next_update_label = QLabel()
        schedule_layout.addRow("Next Update:", self.next_update_label)
        
        schedule_group.setLayout(schedule_layout)
        self.layout().addWidget(schedule_group)
        
        # Update schedule display
        self.update_schedule_display()
        
    def update_status(self):
        """Update the display with current status"""
        status = self.updater.get_update_status()
        
        self.version_label.setText(f"Current Version: {status['current_version']}")
        
        if status['last_update']:
            last_update = datetime.fromisoformat(status['last_update'])
            self.last_update_label.setText(
                f"Last Update: {last_update.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
        if status['next_update']:
            next_update = datetime.fromisoformat(status['next_update'])
            self.next_update_label.setText(
                f"Next Update: {next_update.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
        self.signatures_count_label.setText(f"Signatures: {status['signatures_count']}")
        
    async def check_for_updates(self, force=False):
        """Check for and apply updates"""
        try:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
            self.check_button.setEnabled(False)
            self.force_update_button.setEnabled(False)
            
            if await self.updater.update_signatures():
                self.update_status()
                if not force:
                    QMessageBox.information(self, 'Success', 
                        'Signature database updated successfully')
            else:
                QMessageBox.warning(self, 'Update Failed', 
                    'Failed to update signature database')
                    
        except Exception as e:
            QMessageBox.critical(self, 'Error', 
                f'Error updating signatures: {e}')
            
        finally:
            self.progress_bar.hide()
            self.check_button.setEnabled(True)
            self.force_update_button.setEnabled(True) 
        
    def update_schedule(self):
        """Update the signature update schedule"""
        schedule_config = {
            'daily': self.daily_check.isChecked(),
            'time': self.time_edit.time().toString("HH:mm")
        }
        
        if self.updater.configure_updates(schedule_config):
            self.update_schedule_display()
            QMessageBox.information(
                self, 
                'Success', 
                'Update schedule configured successfully'
            )
        else:
            QMessageBox.warning(
                self, 
                'Error', 
                'Failed to configure update schedule'
            )
            
    def update_schedule_display(self):
        """Update the schedule information display"""
        info = self.updater.get_schedule_info()
        
        if info['next_update']:
            next_update = datetime.fromisoformat(info['next_update'])
            self.next_update_label.setText(
                next_update.strftime("%Y-%m-%d %H:%M")
            )
        else:
            self.next_update_label.setText("Not scheduled") 
        
    @pyqtSlot(dict)
    def update_progress(self, progress: dict):
        """Handle update progress"""
        self.operation_label.setText(progress['operation'])
        self.progress_bar.setValue(int(progress['percentage']))
        
        if progress['status'] == 'downloading':
            downloaded_mb = progress['downloaded'] / 1024 / 1024
            total_mb = progress['download_size'] / 1024 / 1024
            self.detail_label.setText(
                f"Downloading: {downloaded_mb:.1f} MB / {total_mb:.1f} MB"
            )
        elif progress['status'] == 'processing':
            self.detail_label.setText(
                f"Processing signatures: {progress['processed']} / {progress['total']}"
            )
        else:
            self.detail_label.setText("")
            
    @pyqtSlot(bool, str)
    def update_completed(self, success: bool, message: str):
        """Handle update completion"""
        if success:
            QMessageBox.information(self, "Update Complete", message)
        else:
            QMessageBox.warning(self, "Update Failed", message)
            
        self.update_status()  # Refresh status display