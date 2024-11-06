from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QCheckBox, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QTextCursor, QFont
import logging

class ConsoleSignals(QObject):
    """Separate class for Qt signals to avoid conflicts"""
    message_received = pyqtSignal(str)

class ConsoleHandler(logging.Handler):
    """Custom logging handler that emits records to a Qt signal"""
    def __init__(self):
        super().__init__()
        self.signals = ConsoleSignals()
        
    def emit(self, record):
        # Only emit scan-related and process messages
        if any(keyword in record.msg.lower() for keyword in 
            ['scan', 'processing', 'file', 'threat', 'quarantine']):
            msg = self.format(record)
            self.signals.message_received.emit(msg)

class ConsoleWidget(QWidget):
    """Console widget for displaying scan operations and processes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_logging()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Scan Progress Monitor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                background-color: #2E2E2E;
                color: white;
                padding: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        # Console output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont('Menlo', 10))
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: none;
                padding: 5px;
            }
        """)
        layout.addWidget(self.console)
        
        # Store messages for filtering
        self.messages = []
        
    def setup_logging(self):
        """Set up logging handler to capture scan messages"""
        self.handler = ConsoleHandler()
        self.handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s',
                            datefmt='%H:%M:%S')
        )
        
        # Connect the handler's signal to our slot
        self.handler.signals.message_received.connect(self.append_message)
        
        # Add handler to root logger to capture all messages
        logging.getLogger().addHandler(self.handler)
        
    @pyqtSlot(str)
    def append_message(self, message: str):
        """Append a new message to the console"""
        # Color-code different operations
        if "threat" in message.lower():
            message = f'<span style="color: #FF5555;">{message}</span>'
        elif "scanning" in message.lower():
            message = f'<span style="color: #8BE9FD;">{message}</span>'
        elif "processing" in message.lower():
            message = f'<span style="color: #50FA7B;">{message}</span>'
        elif "complete" in message.lower():
            message = f'<span style="color: #FFB86C;">{message}</span>'
            
        self.console.append(message)
        
        # Scroll to bottom
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        
    def clear_console(self):
        """Clear the console output"""
        self.console.clear()
        
    def closeEvent(self, event):
        """Clean up logging handler on close"""
        logging.getLogger().removeHandler(self.handler)
        super().closeEvent(event)