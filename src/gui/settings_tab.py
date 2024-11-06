from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
                           QComboBox, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from pathlib import Path
import json

class SettingsTab(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.settings_file = Path("data/settings.json")
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Scan Settings
        scan_group = QGroupBox("Scan Settings")
        scan_layout = QFormLayout()
        
        # Real-time monitoring
        self.realtime_enabled = QCheckBox()
        self.realtime_enabled.stateChanged.connect(self.save_settings)
        scan_layout.addRow("Enable Real-time Monitoring:", self.realtime_enabled)
        
        # CPU Usage Limit
        self.cpu_limit = QSpinBox()
        self.cpu_limit.setRange(1, 100)
        self.cpu_limit.setValue(30)
        self.cpu_limit.valueChanged.connect(self.save_settings)
        scan_layout.addRow("CPU Usage Limit (%):", self.cpu_limit)
        
        # Memory Usage Limit
        self.memory_limit = QSpinBox()
        self.memory_limit.setRange(128, 1024)
        self.memory_limit.setValue(512)
        self.memory_limit.valueChanged.connect(self.save_settings)
        scan_layout.addRow("Memory Usage Limit (MB):", self.memory_limit)
        
        # Scan Priority
        self.scan_priority = QComboBox()
        self.scan_priority.addItems(["Low", "Normal", "High"])
        self.scan_priority.setCurrentText("Normal")
        self.scan_priority.currentTextChanged.connect(self.save_settings)
        scan_layout.addRow("Scan Priority:", self.scan_priority)
        
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)
        
        # Detection Settings
        detection_group = QGroupBox("Detection Settings")
        detection_layout = QFormLayout()
        
        # Heuristic Analysis
        self.heuristic_enabled = QCheckBox()
        self.heuristic_enabled.setChecked(True)
        self.heuristic_enabled.stateChanged.connect(self.save_settings)
        detection_layout.addRow("Enable Heuristic Analysis:", self.heuristic_enabled)
        
        # Behavior Monitoring
        self.behavior_enabled = QCheckBox()
        self.behavior_enabled.setChecked(True)
        self.behavior_enabled.stateChanged.connect(self.save_settings)
        detection_layout.addRow("Enable Behavior Monitoring:", self.behavior_enabled)
        
        # Threat Sensitivity
        self.threat_sensitivity = QComboBox()
        self.threat_sensitivity.addItems(["Low", "Medium", "High"])
        self.threat_sensitivity.setCurrentText("Medium")
        self.threat_sensitivity.currentTextChanged.connect(self.save_settings)
        detection_layout.addRow("Threat Sensitivity:", self.threat_sensitivity)
        
        detection_group.setLayout(detection_layout)
        layout.addWidget(detection_group)
        
        # Quarantine Settings
        quarantine_group = QGroupBox("Quarantine Settings")
        quarantine_layout = QFormLayout()
        
        # Auto-quarantine
        self.auto_quarantine = QCheckBox()
        self.auto_quarantine.setChecked(True)
        self.auto_quarantine.stateChanged.connect(self.save_settings)
        quarantine_layout.addRow("Auto-quarantine Threats:", self.auto_quarantine)
        
        # Quarantine Location
        self.quarantine_location = QPushButton("Select Location")
        self.quarantine_location.clicked.connect(self.select_quarantine_location)
        quarantine_layout.addRow("Quarantine Location:", self.quarantine_location)
        
        # Retention Period
        self.retention_period = QSpinBox()
        self.retention_period.setRange(1, 365)
        self.retention_period.setValue(30)
        self.retention_period.valueChanged.connect(self.save_settings)
        quarantine_layout.addRow("Retention Period (days):", self.retention_period)
        
        quarantine_group.setLayout(quarantine_layout)
        layout.addWidget(quarantine_group)
        
        # Performance Settings
        performance_group = QGroupBox("Performance Settings")
        performance_layout = QFormLayout()
        
        # Thread Count
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 16)
        self.thread_count.setValue(4)
        self.thread_count.valueChanged.connect(self.save_settings)
        performance_layout.addRow("Scan Threads:", self.thread_count)
        
        # Scan Batch Size
        self.batch_size = QSpinBox()
        self.batch_size.setRange(100, 10000)
        self.batch_size.setValue(1000)
        self.batch_size.valueChanged.connect(self.save_settings)
        performance_layout.addRow("Scan Batch Size:", self.batch_size)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_button)
        
        self.apply_button = QPushButton("Apply Settings")
        self.apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        
    def load_settings(self):
        """Load settings from file"""
        try:
            if self.settings_file.exists():
                settings = json.loads(self.settings_file.read_text())
                
                # Apply loaded settings
                self.realtime_enabled.setChecked(settings.get('realtime_enabled', True))
                self.cpu_limit.setValue(settings.get('cpu_limit', 30))
                self.memory_limit.setValue(settings.get('memory_limit', 512))
                self.scan_priority.setCurrentText(settings.get('scan_priority', 'Normal'))
                self.heuristic_enabled.setChecked(settings.get('heuristic_enabled', True))
                self.behavior_enabled.setChecked(settings.get('behavior_enabled', True))
                self.threat_sensitivity.setCurrentText(settings.get('threat_sensitivity', 'Medium'))
                self.auto_quarantine.setChecked(settings.get('auto_quarantine', True))
                self.retention_period.setValue(settings.get('retention_period', 30))
                self.thread_count.setValue(settings.get('thread_count', 4))
                self.batch_size.setValue(settings.get('batch_size', 1000))
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load settings: {e}")
            
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'realtime_enabled': self.realtime_enabled.isChecked(),
                'cpu_limit': self.cpu_limit.value(),
                'memory_limit': self.memory_limit.value(),
                'scan_priority': self.scan_priority.currentText(),
                'heuristic_enabled': self.heuristic_enabled.isChecked(),
                'behavior_enabled': self.behavior_enabled.isChecked(),
                'threat_sensitivity': self.threat_sensitivity.currentText(),
                'auto_quarantine': self.auto_quarantine.isChecked(),
                'retention_period': self.retention_period.value(),
                'thread_count': self.thread_count.value(),
                'batch_size': self.batch_size.value()
            }
            
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            self.settings_file.write_text(json.dumps(settings, indent=2))
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")
            
    def apply_settings(self):
        """Apply settings to the engine"""
        try:
            # Update engine settings
            self.engine.max_threads = self.thread_count.value()
            self.engine.batch_size = self.batch_size.value()
            
            # Update scan settings
            self.engine.realtime_monitoring = self.realtime_enabled.isChecked()
            self.engine.cpu_limit = self.cpu_limit.value()
            self.engine.memory_limit = self.memory_limit.value() * 1024 * 1024  # Convert to bytes
            
            # Update detection settings
            self.engine.heuristic_enabled = self.heuristic_enabled.isChecked()
            self.engine.behavior_monitoring = self.behavior_enabled.isChecked()
            
            # Save settings to file
            self.save_settings()
            
            QMessageBox.information(self, "Success", "Settings applied successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")
            
    def reset_settings(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to defaults
            self.realtime_enabled.setChecked(True)
            self.cpu_limit.setValue(30)
            self.memory_limit.setValue(512)
            self.scan_priority.setCurrentText("Normal")
            self.heuristic_enabled.setChecked(True)
            self.behavior_enabled.setChecked(True)
            self.threat_sensitivity.setCurrentText("Medium")
            self.auto_quarantine.setChecked(True)
            self.retention_period.setValue(30)
            self.thread_count.setValue(4)
            self.batch_size.setValue(1000)
            
            # Save and apply settings
            self.save_settings()
            self.apply_settings() 

    def select_quarantine_location(self):
        """Open dialog to select quarantine directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Quarantine Directory",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            # Update button text to show selected path
            self.quarantine_location.setText(directory)
            # Save the new location
            self.save_settings()
            
            # Ensure the directory exists
            Path(directory).mkdir(parents=True, exist_ok=True)
            
            QMessageBox.information(
                self,
                "Success",
                f"Quarantine location set to: {directory}"
            )