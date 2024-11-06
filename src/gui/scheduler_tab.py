from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QComboBox, QTimeEdit, QTableWidget,
                           QTableWidgetItem, QFileDialog)
from PyQt6.QtCore import Qt, QTime
from pathlib import Path
from ..core.scheduler import ScanScheduler

class SchedulerTab(QWidget):
    def __init__(self, scheduler: ScanScheduler):
        super().__init__()
        self.scheduler = scheduler
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Add new schedule section
        add_layout = QHBoxLayout()
        
        self.path_button = QPushButton('Select Path')
        self.path_button.clicked.connect(self.select_path)
        add_layout.addWidget(self.path_button)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(['daily', 'weekly', 'monthly'])
        add_layout.addWidget(self.interval_combo)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        add_layout.addWidget(self.time_edit)
        
        self.add_button = QPushButton('Add Schedule')
        self.add_button.clicked.connect(self.add_schedule)
        add_layout.addWidget(self.add_button)
        
        layout.addLayout(add_layout)
        
        # Scheduled scans table
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(5)
        self.schedule_table.setHorizontalHeaderLabels(
            ['Name', 'Path', 'Interval', 'Time', 'Last Run']
        )
        layout.addWidget(self.schedule_table)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.remove_button = QPushButton('Remove Selected')
        self.remove_button.clicked.connect(self.remove_schedule)
        control_layout.addWidget(self.remove_button)
        
        layout.addLayout(control_layout)
        
        self.update_schedule_table()
        
    def select_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if path:
            self.selected_path = Path(path)
            self.path_button.setText(f"Path: {path}")
            
    def add_schedule(self):
        if not hasattr(self, 'selected_path'):
            return
            
        name = f"Scan_{len(self.scheduler.scheduled_scans) + 1}"
        time = self.time_edit.time().toString("HH:mm")
        interval = self.interval_combo.currentText()
        
        self.scheduler.add_scheduled_scan(name, self.selected_path, interval, time)
        self.update_schedule_table()
        
    def remove_schedule(self):
        selected = self.schedule_table.selectedItems()
        if selected:
            row = selected[0].row()
            name = self.schedule_table.item(row, 0).text()
            self.scheduler.remove_scheduled_scan(name)
            self.update_schedule_table()
            
    def update_schedule_table(self):
        self.schedule_table.setRowCount(0)
        for name, info in self.scheduler.get_schedule_status().items():
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)
            self.schedule_table.setItem(row, 0, QTableWidgetItem(name))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(info['path']))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(info['interval']))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(info['time']))
            self.schedule_table.setItem(row, 4, QTableWidgetItem(
                info['last_run'] or 'Never'
            )) 