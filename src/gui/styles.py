"""Stylesheet definitions for the application"""

MAIN_STYLE = """
QMainWindow {
    background-color: #f0f0f0;
}

QTabWidget::pane {
    border: 1px solid #cccccc;
    background: white;
    border-radius: 4px;
}

QTabWidget::tab-bar {
    left: 5px;
}

QTabBar::tab {
    background: #e0e0e0;
    border: 1px solid #cccccc;
    padding: 8px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background: white;
    border-bottom-color: white;
}

QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #106ebe;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #cccccc;
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}

QTableWidget {
    border: 1px solid #cccccc;
    border-radius: 4px;
    gridline-color: #e0e0e0;
}

QTableWidget::item {
    padding: 4px;
}

QTableWidget::item:selected {
    background-color: #e5f3ff;
    color: black;
}

QHeaderView::section {
    background-color: #f5f5f5;
    padding: 6px;
    border: none;
    border-right: 1px solid #cccccc;
    border-bottom: 1px solid #cccccc;
}

QLabel {
    color: #333333;
}

QGroupBox {
    border: 1px solid #cccccc;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 24px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 3px;
    color: #333333;
}

/* Status indicators */
.status-good {
    color: #107c10;
}

.status-warning {
    color: #d83b01;
}

.status-error {
    color: #e81123;
}

/* Custom button styles */
QPushButton.primary {
    background-color: #0078d4;
}

QPushButton.secondary {
    background-color: #ffffff;
    color: #0078d4;
    border: 1px solid #0078d4;
}

QPushButton.danger {
    background-color: #e81123;
}

QPushButton.danger:hover {
    background-color: #c50f1f;
}

/* Scan status indicators */
QLabel.scan-status {
    font-size: 14px;
    font-weight: bold;
    padding: 4px 8px;
    border-radius: 4px;
}

QLabel.scan-status[status="scanning"] {
    background-color: #fff4ce;
    color: #d83b01;
}

QLabel.scan-status[status="complete"] {
    background-color: #dff6dd;
    color: #107c10;
}

QLabel.scan-status[status="error"] {
    background-color: #fde7e9;
    color: #e81123;
}

/* Statistics panel */
QWidget#stats-panel {
    background-color: #f8f9fa;
    border-radius: 4px;
    padding: 12px;
}

QLabel.stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #0078d4;
}

QLabel.stat-label {
    font-size: 12px;
    color: #666666;
}
"""

# Add to main_window.py
def apply_styles(widget):
    """Apply the application styles to a widget"""
    widget.setStyleSheet(MAIN_STYLE) 