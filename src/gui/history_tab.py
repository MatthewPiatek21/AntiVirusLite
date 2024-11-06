from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QTableWidget, QTableWidgetItem, QLabel, QComboBox,
                           QDateEdit, QGroupBox, QFormLayout, QSpinBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
from datetime import datetime, timedelta
from typing import Dict, List
from ..core.history_manager import HistoryManager, ThreatEvent

class HistoryTab(QWidget):
    def __init__(self, history_manager: HistoryManager):
        super().__init__()
        self.history_manager = history_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Filters section
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout()
        
        # Date range
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.dateChanged.connect(self.update_display)
        filter_layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.update_display)
        filter_layout.addRow("End Date:", self.end_date)
        
        # Threat type filter
        self.type_combo = QComboBox()
        self.type_combo.addItem("All Types")
        self.type_combo.currentTextChanged.connect(self.update_display)
        filter_layout.addRow("Threat Type:", self.type_combo)
        
        # Severity filter
        self.severity_spin = QSpinBox()
        self.severity_spin.setRange(0, 10)
        self.severity_spin.valueChanged.connect(self.update_display)
        filter_layout.addRow("Min Severity:", self.severity_spin)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Statistics section
        stats_group = QGroupBox("Statistics")
        stats_layout = QHBoxLayout()
        
        # Charts
        charts_layout = QVBoxLayout()
        
        # Threat types pie chart
        self.type_chart = QChart()
        self.type_chart.setTitle("Threats by Type")
        type_chart_view = QChartView(self.type_chart)
        charts_layout.addWidget(type_chart_view)
        
        # Severity distribution bar chart
        self.severity_chart = QChart()
        self.severity_chart.setTitle("Severity Distribution")
        severity_chart_view = QChartView(self.severity_chart)
        charts_layout.addWidget(severity_chart_view)
        
        stats_layout.addLayout(charts_layout)
        
        # Summary statistics
        summary_layout = QVBoxLayout()
        self.total_threats_label = QLabel()
        self.quarantined_label = QLabel()
        self.realtime_detections_label = QLabel()
        self.scheduled_detections_label = QLabel()
        self.manual_detections_label = QLabel()
        
        summary_layout.addWidget(self.total_threats_label)
        summary_layout.addWidget(self.quarantined_label)
        summary_layout.addWidget(self.realtime_detections_label)
        summary_layout.addWidget(self.scheduled_detections_label)
        summary_layout.addWidget(self.manual_detections_label)
        
        stats_layout.addLayout(summary_layout)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Events table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(7)
        self.events_table.setHorizontalHeaderLabels([
            'Time', 'File', 'Threat Type', 'Severity',
            'Action', 'Scan Type', 'Details'
        ])
        layout.addWidget(self.events_table)
        
        # Initial update
        self.update_display()
        
    def update_display(self):
        """Update all display elements with current filters"""
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        threat_type = self.type_combo.currentText()
        if threat_type == "All Types":
            threat_type = None
        min_severity = self.severity_spin.value()
        if min_severity == 0:
            min_severity = None
            
        # Get filtered events
        events = self.history_manager.get_events(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            threat_type=threat_type,
            min_severity=min_severity
        )
        
        # Update statistics
        stats = self.history_manager.get_statistics(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time())
        )
        
        self._update_summary_labels(stats)
        self._update_charts(stats)
        self._update_events_table(events)
        
    def _update_summary_labels(self, stats: Dict):
        """Update summary statistics labels"""
        self.total_threats_label.setText(f"Total Threats: {stats['total_threats']}")
        self.quarantined_label.setText(f"Quarantined: {stats['quarantined']}")
        self.realtime_detections_label.setText(
            f"Real-time Detections: {stats['scan_types']['real-time']}"
        )
        self.scheduled_detections_label.setText(
            f"Scheduled Detections: {stats['scan_types']['scheduled']}"
        )
        self.manual_detections_label.setText(
            f"Manual Detections: {stats['scan_types']['manual']}"
        )
        
    def _update_charts(self, stats: Dict):
        """Update statistical charts"""
        # Update threat types pie chart
        type_series = QPieSeries()
        for threat_type, count in stats['by_type'].items():
            type_series.append(threat_type, count)
        
        self.type_chart.removeAllSeries()
        self.type_chart.addSeries(type_series)
        
        # Update severity bar chart
        severity_series = QBarSeries()
        severity_set = QBarSet("Severity")
        for severity, count in stats['by_severity'].items():
            severity_set.append(count)
        severity_series.append(severity_set)
        
        self.severity_chart.removeAllSeries()
        self.severity_chart.addSeries(severity_series)
        
    def _update_events_table(self, events: List[ThreatEvent]):
        """Update events table with filtered events"""
        self.events_table.setRowCount(0)
        
        for event in events:
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            
            # Add event details to table
            self.events_table.setItem(row, 0, QTableWidgetItem(event.timestamp))
            self.events_table.setItem(row, 1, QTableWidgetItem(event.file_path))
            self.events_table.setItem(row, 2, QTableWidgetItem(event.threat_type))
            
            severity_item = QTableWidgetItem(str(event.severity))
            if event.severity >= 8:
                severity_item.setBackground(Qt.GlobalColor.red)
            elif event.severity >= 5:
                severity_item.setBackground(Qt.GlobalColor.yellow)
            self.events_table.setItem(row, 3, severity_item)
            
            self.events_table.setItem(row, 4, QTableWidgetItem(event.action_taken))
            self.events_table.setItem(row, 5, QTableWidgetItem(event.scan_type))
            self.events_table.setItem(row, 6, QTableWidgetItem(
                str(event.details) if event.details else ""
            )) 