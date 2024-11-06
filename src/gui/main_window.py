from PyQt6.QtWidgets import (QMainWindow, QWidget, QPushButton, QVBoxLayout, 
                           QHBoxLayout, QFileDialog, QLabel, QProgressBar, 
                           QTableWidget, QTableWidgetItem, QGroupBox,
                           QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from pathlib import Path
import logging
import gc
import time
import asyncio
from src.core.engine import ScanEngine
from .platform_styles import PlatformStyles
from .console_widget import ConsoleWidget

class ScanWorker(QThread):
    """Worker thread for scanning operations"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(dict)
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    
    def __init__(self, engine, paths):
        super().__init__()
        self.engine = engine
        self.paths = paths
        self.total_files = 0
        self.processed_files = 0
        
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = []
            
            # First, accurately count all scannable files
            self.status.emit("Counting files...")
            for path in self.paths:
                if path.exists():
                    for file_path in path.rglob('*'):
                        if file_path.is_file() and not self._should_skip(file_path):
                            self.total_files += 1
                            
            if self.total_files == 0:
                self.status.emit("No files to scan")
                self.finished.emit([])
                return
                
            # Now scan files
            for path in self.paths:
                if path.exists():
                    self.status.emit(f"Scanning {path}...")
                    result = loop.run_until_complete(self.engine.scan_directory(path))
                    results.extend(result)
                    
                    # Update progress based on actual scanned files
                    self.processed_files = len(results)
                    self.progress.emit({
                        'current': self.processed_files,
                        'total': self.total_files,
                        'percentage': (self.processed_files / self.total_files * 100)
                    })
                    
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))
            
        finally:
            loop.close()
            
    def _should_skip(self, file_path: Path) -> bool:
        """Determine if a file should be skipped based on common criteria"""
        # Skip hidden files and directories
        if file_path.name.startswith('.'):
            return True
            
        # Skip system files and directories
        system_paths = [
            '/System', '/Library', '/private',  # macOS
            '/proc', '/sys', '/dev',           # Linux
            'Windows', 'Program Files'          # Windows
        ]
        if any(sys_path in str(file_path) for sys_path in system_paths):
            return True
            
        # Skip certain file types
        skip_extensions = {
            '.dll', '.sys', '.dylib', '.so',   # System libraries
            '.log', '.tmp', '.temp',           # Temporary files
            '.swp', '.bak', '.old'             # Backup files
        }
        if file_path.suffix.lower() in skip_extensions:
            return True
            
        return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize only essential components at startup
        self.engine = None
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('AntiVirus Scanner')
        self.setMinimumSize(1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create scan interface
        scan_widget = self._create_scan_interface()
        main_layout.addWidget(scan_widget, stretch=2)
        
        # Add console widget
        self.console = ConsoleWidget()
        main_layout.addWidget(self.console, stretch=1)
        
        # Apply platform-specific styles
        PlatformStyles.apply_platform_style(self)
        
    def _create_scan_interface(self) -> QWidget:
        """Create the scanning interface"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Scan controls
        controls_group = QGroupBox("Scan Controls")
        controls_layout = QHBoxLayout()
        
        # Scan button
        scan_btn = QPushButton("Scan File/Folder")
        scan_btn.clicked.connect(self.run_scan)
        controls_layout.addWidget(scan_btn)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Progress section
        progress_group = QGroupBox("Scan Progress")
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.detail_label = QLabel()
        progress_layout.addWidget(self.detail_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Results table
        results_group = QGroupBox("Scan Results")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            'File', 'Status', 'Threat Type', 'Action'
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        return widget
        
    def _initialize_components(self):
        """Initialize components only when needed"""
        if not self.engine:
            self.engine = ScanEngine(auto_start=False)
            
    def run_scan(self):
        """Run a scan on a user-selected location"""
        # Initialize components only when scanning
        self._initialize_components()
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Scan",
            str(Path.home())
        )
        
        if directory:
            # Start monitoring only when scanning
            self.engine.system_monitor.start_monitoring()
            
            self.status_label.setText(f"Preparing to scan {directory}...")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            
            self.scan_worker = ScanWorker(self.engine, [Path(directory)])
            self.scan_worker.finished.connect(self._scan_completed)
            self.scan_worker.error.connect(self._scan_error)
            self.scan_worker.progress.connect(self._update_progress)
            self.scan_worker.status.connect(self._update_status)
            self.scan_worker.start()
            
    def _scan_completed(self, results):
        """Handle scan completion"""
        # Stop monitoring after scan completes
        if self.engine:
            self.engine.system_monitor.stop_monitoring()
        
        self.status_label.setText("Scan Complete")
        self.progress_bar.setValue(100)
        
        # Update results table
        self.results_table.setRowCount(0)
        threats_found = 0
        
        for result in results:
            if result.get('threats'):
                threats_found += len(result['threats'])
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                self.results_table.setItem(row, 0, 
                    QTableWidgetItem(str(result['file_path'])))
                self.results_table.setItem(row, 1, 
                    QTableWidgetItem('Infected'))
                self.results_table.setItem(row, 2, 
                    QTableWidgetItem(result['threats'][0]['type']))
                
                action = 'Quarantined' if result.get('quarantined') else 'Detected'
                self.results_table.setItem(row, 3, 
                    QTableWidgetItem(action))
        
        # Show summary
        if threats_found > 0:
            QMessageBox.warning(self, 'Scan Complete', 
                f'Found {threats_found} threat(s).\nCheck the results table for details.')
        else:
            QMessageBox.information(self, 'Scan Complete', 
                'No threats found.')
            
    def _scan_error(self, error_msg):
        """Handle scan error"""
        # Stop monitoring on error
        if self.engine:
            self.engine.system_monitor.stop_monitoring()
        
        self.status_label.setText("Scan Failed")
        self.progress_bar.setRange(0, 100)
        QMessageBox.critical(self, "Error", f"Scan failed: {error_msg}")
        
    def _update_progress(self, progress):
        """Update scan progress"""
        self.progress_bar.setValue(int(progress['percentage']))
        self.detail_label.setText(
            f"Processed {progress['current']} of {progress['total']} files"
        )
        
    def _update_status(self, status):
        """Update scan status"""
        self.status_label.setText(status)
        
    def closeEvent(self, event):
        """Handle application shutdown"""
        try:
            # Stop services only if they were initialized
            if self.engine:
                if hasattr(self.engine, 'system_monitor'):
                    self.engine.system_monitor.stop_monitoring()
                    
            # Force garbage collection
            gc.collect()
            
            event.accept()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            event.accept()