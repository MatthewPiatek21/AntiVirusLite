from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
                           QLabel, QTextEdit, QGroupBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSlot
from pathlib import Path
from datetime import datetime
from ..core.quarantine_manager import QuarantineManager

class ThreatDetailsDialog(QDialog):
    """Dialog for displaying detailed threat information"""
    def __init__(self, threat_info: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Threat Details")
        self.setMinimumSize(500, 300)
        self.init_ui(threat_info)
        
    def init_ui(self, threat_info: list):
        layout = QVBoxLayout(self)
        
        # Threat information display
        for threat in threat_info:
            threat_group = QGroupBox(threat['name'])
            threat_layout = QVBoxLayout()
            
            # Add threat details
            threat_layout.addWidget(QLabel(f"Type: {threat['type']}"))
            threat_layout.addWidget(QLabel(f"Severity: {threat['severity']}/10"))
            
            description = QTextEdit()
            description.setPlainText(threat['description'])
            description.setReadOnly(True)
            threat_layout.addWidget(description)
            
            threat_group.setLayout(threat_layout)
            layout.addWidget(threat_group)
            
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class RestoreDialog(QDialog):
    """Dialog for confirming file restoration"""
    def __init__(self, file_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore Quarantined File")
        self.init_ui(file_info)
        
    def init_ui(self, file_info: dict):
        layout = QVBoxLayout(self)
        
        # Warning message
        warning = QLabel(
            "Warning: This file was quarantined because it contains malicious content. "
            "Restoring it could pose a security risk to your system."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: red;")
        layout.addWidget(warning)
        
        # File information
        info_group = QGroupBox("File Information")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"Original Path: {file_info['original_path']}"))
        info_layout.addWidget(QLabel(f"Quarantined On: {file_info['timestamp']}"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Confirmation checkbox
        self.confirm_check = QCheckBox(
            "I understand the risks and want to restore this file"
        )
        layout.addWidget(self.confirm_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        restore_btn = QPushButton("Restore")
        restore_btn.clicked.connect(self.accept)
        restore_btn.setEnabled(False)
        self.confirm_check.stateChanged.connect(
            lambda: restore_btn.setEnabled(self.confirm_check.isChecked())
        )
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(restore_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

class QuarantineTab(QWidget):
    def __init__(self, quarantine_manager: QuarantineManager):
        super().__init__()
        self.quarantine_manager = quarantine_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Quarantine table
        self.quarantine_table = QTableWidget()
        self.quarantine_table.setColumnCount(6)
        self.quarantine_table.setHorizontalHeaderLabels([
            'File Name', 'Original Path', 'Quarantined On', 
            'Threat Level', 'Size', 'Actions'
        ])
        self.quarantine_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.quarantine_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.view_details_btn = QPushButton('View Threat Details')
        self.view_details_btn.clicked.connect(self.view_threat_details)
        button_layout.addWidget(self.view_details_btn)
        
        self.restore_btn = QPushButton('Restore Selected')
        self.restore_btn.clicked.connect(self.restore_file)
        button_layout.addWidget(self.restore_btn)
        
        self.delete_btn = QPushButton('Delete Selected')
        self.delete_btn.clicked.connect(self.delete_file)
        button_layout.addWidget(self.delete_btn)
        
        self.refresh_btn = QPushButton('Refresh')
        self.refresh_btn.clicked.connect(self.update_quarantine_table)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.total_files_label = QLabel('Total Files: 0')
        self.total_size_label = QLabel('Total Size: 0 B')
        stats_layout.addWidget(self.total_files_label)
        stats_layout.addWidget(self.total_size_label)
        layout.addLayout(stats_layout)
        
        # Initial population
        self.update_quarantine_table()
        
    def update_quarantine_table(self):
        """Update the quarantine table with current quarantined files"""
        self.quarantine_table.setRowCount(0)
        quarantined_files = self.quarantine_manager.get_quarantine_list()
        
        total_size = 0
        for file_info in quarantined_files:
            row = self.quarantine_table.rowCount()
            self.quarantine_table.insertRow(row)
            
            # Basic file information
            self.quarantine_table.setItem(row, 0, QTableWidgetItem(file_info['name']))
            self.quarantine_table.setItem(row, 1, QTableWidgetItem(file_info['original_path']))
            self.quarantine_table.setItem(row, 2, QTableWidgetItem(file_info['timestamp']))
            
            # Calculate max threat severity
            max_severity = max((t['severity'] for t in file_info['threat_info']), default=0)
            severity_item = QTableWidgetItem(str(max_severity))
            if max_severity >= 8:
                severity_item.setBackground(Qt.GlobalColor.red)
            elif max_severity >= 5:
                severity_item.setBackground(Qt.GlobalColor.yellow)
            self.quarantine_table.setItem(row, 3, severity_item)
            
            # File size
            size = file_info['size']
            total_size += size
            size_str = self.format_size(size)
            self.quarantine_table.setItem(row, 4, QTableWidgetItem(size_str))
            
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            details_btn = QPushButton('Details')
            details_btn.clicked.connect(
                lambda checked, f=file_info: self.view_threat_details(f)
            )
            actions_layout.addWidget(details_btn)
            
            restore_btn = QPushButton('Restore')
            restore_btn.clicked.connect(
                lambda checked, f=file_info: self.restore_file(f)
            )
            actions_layout.addWidget(restore_btn)
            
            delete_btn = QPushButton('Delete')
            delete_btn.clicked.connect(
                lambda checked, f=file_info: self.delete_file(f)
            )
            actions_layout.addWidget(delete_btn)
            
            self.quarantine_table.setCellWidget(row, 5, actions_widget)
            
        # Update statistics
        self.total_files_label.setText(f'Total Files: {len(quarantined_files)}')
        self.total_size_label.setText(f'Total Size: {self.format_size(total_size)}')
        
    def view_threat_details(self, file_info=None):
        """Show detailed threat information"""
        if not file_info:
            selected = self.quarantine_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, 'Warning', 'Please select a file to view')
                return
            file_name = selected[0].text()
            file_info = self._get_file_info(file_name)
            
        if file_info and file_info['threat_info']:
            dialog = ThreatDetailsDialog(file_info['threat_info'], self)
            dialog.exec()
            
    def restore_file(self, file_info=None):
        """Restore selected file from quarantine"""
        if not file_info:
            selected = self.quarantine_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, 'Warning', 'Please select a file to restore')
                return
            file_name = selected[0].text()
            file_info = self._get_file_info(file_name)
            
        if file_info:
            dialog = RestoreDialog(file_info, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                success = self.quarantine_manager.restore_file(
                    file_info['name'],
                    force=True
                )
                if success:
                    QMessageBox.information(self, 'Success', 'File restored successfully')
                    self.update_quarantine_table()
                else:
                    QMessageBox.critical(self, 'Error', 'Failed to restore file')
                    
    def delete_file(self, file_info=None):
        """Permanently delete file from quarantine"""
        if not file_info:
            selected = self.quarantine_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, 'Warning', 'Please select a file to delete')
                return
            file_name = selected[0].text()
            file_info = self._get_file_info(file_name)
            
        if file_info:
            reply = QMessageBox.question(
                self,
                'Confirm Delete',
                f'Are you sure you want to permanently delete {file_info["name"]}?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.quarantine_manager.delete_quarantined_file(file_info['name'])
                if success:
                    QMessageBox.information(self, 'Success', 'File deleted successfully')
                    self.update_quarantine_table()
                else:
                    QMessageBox.critical(self, 'Error', 'Failed to delete file')
                    
    def _get_file_info(self, file_name: str) -> dict:
        """Get file information from quarantine list"""
        quarantined_files = self.quarantine_manager.get_quarantine_list()
        return next(
            (f for f in quarantined_files if f['name'] == file_name),
            None
        )
        
    @staticmethod
    def format_size(size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"