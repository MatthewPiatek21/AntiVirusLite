from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
                           QHeaderView)
from PyQt6.QtCore import Qt
from pathlib import Path
from datetime import datetime

class ScanResultsDialog(QDialog):
    def __init__(self, results: list, parent=None):
        super().__init__(parent)
        self.results = results
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Scan Results')
        self.setMinimumSize(800, 400)
        
        layout = QVBoxLayout(self)
        
        # Summary section
        summary_layout = QHBoxLayout()
        
        total_files = len(self.results)
        infected_files = sum(1 for r in self.results if r['status'] == 'infected')
        quarantined_files = sum(1 for r in self.results if r.get('quarantined'))
        
        summary_layout.addWidget(QLabel(f'Total Files Scanned: {total_files}'))
        summary_layout.addWidget(QLabel(f'Threats Found: {infected_files}'))
        summary_layout.addWidget(QLabel(f'Files Quarantined: {quarantined_files}'))
        
        layout.addLayout(summary_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            'File Path', 'Status', 'Threat Details', 'Severity', 'Action Taken'
        ])
        
        # Auto-resize columns to content
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.populate_results()
        layout.addWidget(self.results_table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.view_quarantine_btn = QPushButton('View Quarantine')
        self.view_quarantine_btn.clicked.connect(self.view_quarantine)
        button_layout.addWidget(self.view_quarantine_btn)
        
        self.export_btn = QPushButton('Export Results')
        self.export_btn.clicked.connect(self.export_results)
        button_layout.addWidget(self.export_btn)
        
        self.close_btn = QPushButton('Close')
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def populate_results(self):
        """Populate the results table with scan data"""
        self.results_table.setRowCount(0)
        
        for result in self.results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # File path
            self.results_table.setItem(row, 0, 
                QTableWidgetItem(result['file_path']))
            
            # Status
            status_item = QTableWidgetItem(result['status'])
            if result['status'] == 'infected':
                status_item.setBackground(Qt.GlobalColor.red)
            elif result['status'] == 'clean':
                status_item.setBackground(Qt.GlobalColor.green)
            self.results_table.setItem(row, 1, status_item)
            
            # Threat details
            threats = result.get('threats', [])
            threat_text = '\n'.join(f"{t['name']}: {t['description']}" 
                                  for t in threats) if threats else 'None'
            self.results_table.setItem(row, 2, QTableWidgetItem(threat_text))
            
            # Severity
            max_severity = max((t['severity'] for t in threats), default=0)
            severity_item = QTableWidgetItem(str(max_severity) if max_severity else 'N/A')
            if max_severity >= 8:
                severity_item.setBackground(Qt.GlobalColor.red)
            elif max_severity >= 5:
                severity_item.setBackground(Qt.GlobalColor.yellow)
            self.results_table.setItem(row, 3, severity_item)
            
            # Action taken
            action = 'Quarantined' if result.get('quarantined') else 'None'
            self.results_table.setItem(row, 4, QTableWidgetItem(action))
            
    def view_quarantine(self):
        """Switch to quarantine tab in main window"""
        main_window = self.parent()
        if main_window:
            main_window.tab_widget.setCurrentIndex(2)  # Switch to quarantine tab
        self.accept()
        
    def export_results(self):
        """Export scan results to a file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_results_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write("=== Scan Results ===\n\n")
                f.write(f"Scan Time: {timestamp}\n")
                f.write(f"Total Files Scanned: {len(self.results)}\n")
                f.write(f"Threats Found: {sum(1 for r in self.results if r['status'] == 'infected')}\n")
                f.write(f"Files Quarantined: {sum(1 for r in self.results if r.get('quarantined'))}\n\n")
                
                f.write("=== Detailed Results ===\n\n")
                for result in self.results:
                    if result['status'] == 'infected':
                        f.write(f"\nFile: {result['file_path']}\n")
                        f.write(f"Status: {result['status']}\n")
                        for threat in result.get('threats', []):
                            f.write(f"Threat: {threat['name']}\n")
                            f.write(f"Severity: {threat['severity']}\n")
                            f.write(f"Description: {threat['description']}\n")
                        f.write(f"Action: {'Quarantined' if result.get('quarantined') else 'None'}\n")
                        f.write("-" * 50 + "\n")
                        
            QMessageBox.information(self, 'Success', 
                f'Results exported to {filename}')
                
        except Exception as e:
            QMessageBox.critical(self, 'Error', 
                f'Failed to export results: {e}') 