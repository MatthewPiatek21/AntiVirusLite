from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                           QLabel, QPushButton, QTabWidget, QTextBrowser)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

class HelpTab(QWidget):
    """User-friendly help and instructions tab"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create nested tab widget for different help sections
        help_tabs = QTabWidget()
        
        # Getting Started Tab
        getting_started = QTextBrowser()
        getting_started.setOpenExternalLinks(True)
        getting_started.setHtml("""
            <h2>Welcome to AntiVirus Scanner!</h2>
            <p>This software helps protect your computer from viruses and other harmful programs. 
            Here's how to get started:</p>
            
            <h3>Quick Start Guide:</h3>
            <ol>
                <li><b>Run a Quick Scan:</b>
                    <ul>
                        <li>Click the "Scanner" tab</li>
                        <li>Click the "Quick Scan" button</li>
                        <li>This will check the most common places for viruses</li>
                    </ul>
                </li>
                <br>
                <li><b>Scan a Specific Folder:</b>
                    <ul>
                        <li>Click "Scan File/Folder"</li>
                        <li>Choose the folder you want to check</li>
                        <li>Wait for the scan to complete</li>
                    </ul>
                </li>
                <br>
                <li><b>View Results:</b>
                    <ul>
                        <li>After each scan, you'll see a summary of what was found</li>
                        <li>Any suspicious files will be listed in the results table</li>
                        <li>You can choose to quarantine or delete suspicious files</li>
                    </ul>
                </li>
            </ol>
            
            <h3>Important Tips:</h3>
            <ul>
                <li>Keep the software running to maintain protection</li>
                <li>Update regularly for the best protection</li>
                <li>Schedule regular scans of your computer</li>
            </ul>
        """)
        help_tabs.addTab(getting_started, "Getting Started")
        
        # Features Guide Tab
        features = QTextBrowser()
        features.setHtml("""
            <h2>Main Features</h2>
            
            <h3>Scanner Tab</h3>
            <p>The main scanning interface where you can:</p>
            <ul>
                <li><b>Quick Scan:</b> Fast check of common virus locations</li>
                <li><b>Full Scan:</b> Complete system check (takes longer)</li>
                <li><b>Custom Scan:</b> Check specific files or folders</li>
            </ul>
            
            <h3>Real-time Protection</h3>
            <p>Constantly monitors your computer for:</p>
            <ul>
                <li>New files being downloaded</li>
                <li>Programs trying to make changes</li>
                <li>Suspicious activity</li>
            </ul>
            
            <h3>Quarantine</h3>
            <p>A safe place where suspicious files are stored:</p>
            <ul>
                <li>Infected files are moved here automatically</li>
                <li>Files can't harm your computer while in quarantine</li>
                <li>You can restore files if they're safe</li>
                <li>Or permanently delete them if they're dangerous</li>
            </ul>
            
            <h3>Scheduled Scans</h3>
            <p>Set up automatic scans:</p>
            <ul>
                <li>Daily, weekly, or monthly scans</li>
                <li>Choose what time they run</li>
                <li>Pick which folders to scan</li>
            </ul>
            
            <h3>Updates</h3>
            <p>Keeps your protection current:</p>
            <ul>
                <li>Automatic updates</li>
                <li>Latest virus definitions</li>
                <li>Improved detection capabilities</li>
            </ul>
        """)
        help_tabs.addTab(features, "Features Guide")
        
        # How To Tab
        how_to = QTextBrowser()
        how_to.setHtml("""
            <h2>How To Guide</h2>
            
            <h3>How to Run a Scan</h3>
            <ol>
                <li><b>Quick Scan:</b>
                    <ul>
                        <li>Click the "Scanner" tab</li>
                        <li>Click "Quick Scan"</li>
                        <li>Wait for results</li>
                    </ul>
                </li>
                <br>
                <li><b>Full System Scan:</b>
                    <ul>
                        <li>Click "Full System Scan"</li>
                        <li>This will take longer but is more thorough</li>
                        <li>You can continue using your computer during the scan</li>
                    </ul>
                </li>
                <br>
                <li><b>Scan Specific Location:</b>
                    <ul>
                        <li>Click "Scan File/Folder"</li>
                        <li>Browse to the location you want to scan</li>
                        <li>Click "Select Folder" to start scanning</li>
                    </ul>
                </li>
            </ol>
            
            <h3>How to Schedule Scans</h3>
            <ol>
                <li>Go to the "Scheduled Scans" tab</li>
                <li>Click "Add New Schedule"</li>
                <li>Choose:
                    <ul>
                        <li>When to scan (daily/weekly/monthly)</li>
                        <li>What time to run</li>
                        <li>What to scan</li>
                    </ul>
                </li>
                <li>Click "Save" to activate the schedule</li>
            </ol>
            
            <h3>How to Handle Threats</h3>
            <p>When a threat is found:</p>
            <ol>
                <li>A notification will appear</li>
                <li>The file will be automatically quarantined</li>
                <li>You can:
                    <ul>
                        <li>Delete the file permanently</li>
                        <li>Keep it in quarantine</li>
                        <li>Restore it (if you're sure it's safe)</li>
                    </ul>
                </li>
            </ol>
            
            <h3>How to Update</h3>
            <ol>
                <li>Go to the "Updates" tab</li>
                <li>Click "Check for Updates"</li>
                <li>Updates will download and install automatically</li>
            </ol>
        """)
        help_tabs.addTab(how_to, "How To Guide")
        
        # Troubleshooting Tab
        troubleshooting = QTextBrowser()
        troubleshooting.setHtml("""
            <h2>Troubleshooting Guide</h2>
            
            <h3>Common Issues</h3>
            
            <h4>Scan is Running Slowly</h4>
            <ul>
                <li><b>Solution:</b>
                    <ul>
                        <li>Close other programs to free up resources</li>
                        <li>Try running a Quick Scan instead of Full Scan</li>
                        <li>Check system resources in the Settings tab</li>
                    </ul>
                </li>
            </ul>
            
            <h4>Updates Not Working</h4>
            <ul>
                <li><b>Solution:</b>
                    <ul>
                        <li>Check your internet connection</li>
                        <li>Try clicking "Force Update"</li>
                        <li>Restart the program</li>
                    </ul>
                </li>
            </ul>
            
            <h4>Program Using Too Much Memory</h4>
            <ul>
                <li><b>Solution:</b>
                    <ul>
                        <li>Adjust scan intensity in Settings</li>
                        <li>Reduce number of scheduled scans</li>
                        <li>Close other programs during scans</li>
                    </ul>
                </li>
            </ul>
            
            <h4>Can't Restore Quarantined File</h4>
            <ul>
                <li><b>Solution:</b>
                    <ul>
                        <li>Make sure you have permission to restore files</li>
                        <li>Check if the original location exists</li>
                        <li>Try restarting the program</li>
                    </ul>
                </li>
            </ul>
            
            <h3>Need More Help?</h3>
            <p>If you're still having problems:</p>
            <ul>
                <li>Check the system health monitor</li>
                <li>Review the program logs</li>
                <li>Contact support for assistance</li>
            </ul>
        """)
        help_tabs.addTab(troubleshooting, "Troubleshooting")
        
        # Add the tab widget to the main layout
        layout.addWidget(help_tabs)
        
        # Add a "Report Issue" button at the bottom
        report_button = QPushButton("Report an Issue")
        report_button.setIcon(QIcon("icons/help.png"))
        report_button.clicked.connect(self.report_issue)
        layout.addWidget(report_button)
        
    def report_issue(self):
        """Open issue reporting dialog"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Report Issue",
            "To report an issue, please contact support at:\n"
            "support@antivirusscanner.com\n\n"
            "Please include:\n"
            "- What you were doing\n"
            "- What went wrong\n"
            "- Any error messages you saw"
        ) 