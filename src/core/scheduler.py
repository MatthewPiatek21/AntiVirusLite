import schedule
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from .engine import ScanEngine

class ScanResult:
    """Container for scan results"""
    def __init__(self):
        self.files_scanned: int = 0
        self.threats_found: int = 0
        self.quarantined: int = 0
        self.errors: int = 0
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.threats: List[Dict] = []

class ScanScheduler:
    """Manages scheduled scans with enhanced detection capabilities"""
    
    def __init__(self, scan_engine: ScanEngine):
        self.engine = scan_engine
        self.scheduler_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.scheduled_scans: Dict[str, dict] = {}
        self.logger = logging.getLogger(__name__)
        self.current_scan: Optional[ScanResult] = None
        
    def add_scheduled_scan(self, name: str, path: Path, interval: str, time: str):
        """
        Add a new scheduled scan
        interval: 'daily', 'weekly', 'monthly'
        time: 'HH:MM' format
        """
        if interval not in ['daily', 'weekly', 'monthly']:
            raise ValueError("Invalid interval. Must be 'daily', 'weekly', or 'monthly'")
            
        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            raise ValueError("Invalid time format. Must be 'HH:MM'")
            
        self.scheduled_scans[name] = {
            'path': path,
            'interval': interval,
            'time': time,
            'last_run': None,
            'enabled': True,
            'results': [],  # Store historical results
            'status': 'scheduled'
        }
        
        # Schedule the scan based on interval
        if interval == 'daily':
            schedule.every().day.at(time).do(self._run_scheduled_scan, name)
        elif interval == 'weekly':
            schedule.every().week.at(time).do(self._run_scheduled_scan, name)
        elif interval == 'monthly':
            schedule.every().month.at(time).do(self._run_scheduled_scan, name)
            
    def _run_scheduled_scan(self, name: str):
        """Execute a scheduled scan with enhanced detection"""
        scan_info = self.scheduled_scans.get(name)
        if not scan_info or not scan_info['enabled']:
            return
            
        try:
            self.logger.info(f"Starting scheduled scan: {name}")
            scan_info['status'] = 'running'
            self.current_scan = ScanResult()
            
            # Run the scan using the enhanced engine capabilities
            results = self.engine.scan_directory(scan_info['path'])
            
            # Process results
            for result in results:
                if result.get('threats'):
                    self.current_scan.threats.extend(result['threats'])
                    self.current_scan.threats_found += len(result['threats'])
                if result.get('quarantined'):
                    self.current_scan.quarantined += 1
                if result.get('error'):
                    self.current_scan.errors += 1
                    
            # Update scan information
            self.current_scan.end_time = datetime.now()
            self.current_scan.files_scanned = self.engine.stats.files_scanned
            
            # Store scan results
            scan_info['last_run'] = datetime.now()
            scan_info['last_result'] = {
                'files_scanned': self.current_scan.files_scanned,
                'threats_found': self.current_scan.threats_found,
                'quarantined': self.current_scan.quarantined,
                'errors': self.current_scan.errors,
                'duration': (self.current_scan.end_time - self.current_scan.start_time).total_seconds(),
                'threats': self.current_scan.threats
            }
            
            scan_info['results'].append(scan_info['last_result'])
            scan_info['status'] = 'completed'
            
            # Log summary
            self.logger.info(
                f"Scheduled scan completed: {name}\n"
                f"Files scanned: {self.current_scan.files_scanned}\n"
                f"Threats found: {self.current_scan.threats_found}\n"
                f"Files quarantined: {self.current_scan.quarantined}\n"
                f"Errors: {self.current_scan.errors}"
            )
            
        except Exception as e:
            self.logger.error(f"Error in scheduled scan {name}: {e}")
            scan_info['status'] = 'error'
            scan_info['last_error'] = str(e)
            
        finally:
            self.current_scan = None
            
    def get_scan_history(self, name: str) -> List[Dict]:
        """Get historical scan results for a scheduled scan"""
        scan_info = self.scheduled_scans.get(name)
        if not scan_info:
            return []
        return scan_info['results']
        
    def get_current_scan_progress(self) -> Optional[Dict]:
        """Get progress of current running scan"""
        if not self.current_scan:
            return None
            
        return {
            'files_scanned': self.current_scan.files_scanned,
            'threats_found': self.current_scan.threats_found,
            'quarantined': self.current_scan.quarantined,
            'errors': self.current_scan.errors,
            'duration': (datetime.now() - self.current_scan.start_time).total_seconds()
        }
        
    def start(self):
        """Start the scheduler thread"""
        if not self.is_running:
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
    def stop(self):
        """Stop the scheduler thread"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
            
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    def get_schedule_status(self) -> Dict:
        """Get the current status of all scheduled scans"""
        return {
            name: {
                'path': str(scan['path']),
                'interval': scan['interval'],
                'time': scan['time'],
                'last_run': scan['last_run'].isoformat() if scan['last_run'] else None,
                'enabled': scan['enabled']
            }
            for name, scan in self.scheduled_scans.items()
        } 