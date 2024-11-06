import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import psutil
import platform
from enum import Enum

class HealthLogLevel(Enum):
    """Health log severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class HealthLogEntry:
    """Container for health log entries"""
    timestamp: datetime
    level: HealthLogLevel
    category: str
    message: str
    metrics: Dict
    system_info: Dict
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_action: Optional[str] = None

class HealthLogger:
    """Manages system health logging and analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.log_dir = Path("data/health_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log rotation
        self.max_log_days = 30  # Keep logs for 30 days
        self.max_log_size = 50 * 1024 * 1024  # 50MB per log file
        
        # System info cache
        self._system_info = self._get_system_info()
        
        # Cleanup old logs on startup
        self._cleanup_old_logs()
        
    def log_health_event(self, level: HealthLogLevel, category: str, 
                        message: str, metrics: Dict):
        """Log a health event with current system metrics"""
        try:
            entry = HealthLogEntry(
                timestamp=datetime.now(),
                level=level,
                category=category,
                message=message,
                metrics=metrics,
                system_info=self._system_info
            )
            
            self._write_log_entry(entry)
            
            # Log to application log as well
            log_level = {
                HealthLogLevel.INFO: logging.INFO,
                HealthLogLevel.WARNING: logging.WARNING,
                HealthLogLevel.CRITICAL: logging.CRITICAL
            }[level]
            
            self.logger.log(log_level, f"Health event: {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to log health event: {e}")
            
    def resolve_event(self, event_id: str, resolution_action: str):
        """Mark a health event as resolved"""
        try:
            log_file = self._get_current_log_file()
            if not log_file.exists():
                return
                
            entries = json.loads(log_file.read_text())
            
            for entry in entries:
                if entry.get('id') == event_id and not entry.get('resolved'):
                    entry['resolved'] = True
                    entry['resolution_time'] = datetime.now().isoformat()
                    entry['resolution_action'] = resolution_action
                    break
                    
            log_file.write_text(json.dumps(entries, indent=2))
            
        except Exception as e:
            self.logger.error(f"Failed to resolve health event: {e}")
            
    def get_health_history(self, days: int = 7, 
                          level: Optional[HealthLogLevel] = None,
                          category: Optional[str] = None) -> List[Dict]:
        """Get health event history with optional filtering"""
        try:
            history = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Collect entries from all relevant log files
            for log_file in self.log_dir.glob("health_*.json"):
                try:
                    entries = json.loads(log_file.read_text())
                    for entry in entries:
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_time < cutoff_date:
                            continue
                            
                        if level and entry['level'] != level.value:
                            continue
                            
                        if category and entry['category'] != category:
                            continue
                            
                        history.append(entry)
                        
                except Exception as e:
                    self.logger.error(f"Error reading log file {log_file}: {e}")
                    continue
                    
            return sorted(history, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to get health history: {e}")
            return []
            
    def get_health_summary(self, days: int = 7) -> Dict:
        """Generate summary of health events"""
        try:
            history = self.get_health_history(days)
            
            return {
                'total_events': len(history),
                'by_level': {
                    'critical': sum(1 for e in history if e['level'] == 'critical'),
                    'warning': sum(1 for e in history if e['level'] == 'warning'),
                    'info': sum(1 for e in history if e['level'] == 'info')
                },
                'by_category': self._count_by_category(history),
                'resolution_rate': self._calculate_resolution_rate(history),
                'avg_resolution_time': self._calculate_avg_resolution_time(history),
                'most_common_issues': self._get_most_common_issues(history)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate health summary: {e}")
            return {}
            
    def _write_log_entry(self, entry: HealthLogEntry):
        """Write a health log entry to the current log file"""
        try:
            log_file = self._get_current_log_file()
            
            # Read existing entries
            if log_file.exists():
                entries = json.loads(log_file.read_text())
            else:
                entries = []
                
            # Add new entry
            entries.append({
                'id': f"{entry.timestamp.strftime('%Y%m%d%H%M%S')}_{len(entries)}",
                'timestamp': entry.timestamp.isoformat(),
                'level': entry.level.value,
                'category': entry.category,
                'message': entry.message,
                'metrics': entry.metrics,
                'system_info': entry.system_info,
                'resolved': entry.resolved,
                'resolution_time': entry.resolution_time.isoformat() 
                                 if entry.resolution_time else None,
                'resolution_action': entry.resolution_action
            })
            
            # Write updated entries
            log_file.write_text(json.dumps(entries, indent=2))
            
            # Check if rotation needed
            if log_file.stat().st_size > self.max_log_size:
                self._rotate_logs()
                
        except Exception as e:
            self.logger.error(f"Failed to write health log entry: {e}")
            
    def _get_current_log_file(self) -> Path:
        """Get the current log file path"""
        return self.log_dir / f"health_{datetime.now().strftime('%Y%m')}.json"
        
    def _cleanup_old_logs(self):
        """Clean up log files older than max_log_days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_log_days)
            
            for log_file in self.log_dir.glob("health_*.json"):
                try:
                    # Extract date from filename
                    file_date = datetime.strptime(
                        log_file.stem.split('_')[1], 
                        '%Y%m'
                    )
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        
                except (ValueError, IndexError):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            
    def _rotate_logs(self):
        """Rotate log files when size limit is reached"""
        try:
            current_file = self._get_current_log_file()
            if not current_file.exists():
                return
                
            # Create new filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_file = self.log_dir / f"health_{timestamp}.json"
            
            # Rename current file
            current_file.rename(new_file)
            
            # Cleanup old files if needed
            self._cleanup_old_logs()
            
        except Exception as e:
            self.logger.error(f"Failed to rotate logs: {e}")
            
    def _get_system_info(self) -> Dict:
        """Get detailed system information"""
        try:
            return {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'memory_total': psutil.virtual_memory().total,
                'cpu_count': psutil.cpu_count(),
                'disk_partitions': [
                    {
                        'device': p.device,
                        'mountpoint': p.mountpoint,
                        'fstype': p.fstype
                    }
                    for p in psutil.disk_partitions()
                ]
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}
            
    def _count_by_category(self, history: List[Dict]) -> Dict:
        """Count events by category"""
        categories = {}
        for entry in history:
            category = entry['category']
            categories[category] = categories.get(category, 0) + 1
        return categories
        
    def _calculate_resolution_rate(self, history: List[Dict]) -> float:
        """Calculate percentage of resolved events"""
        if not history:
            return 0.0
        resolved = sum(1 for e in history if e.get('resolved', False))
        return (resolved / len(history)) * 100
        
    def _calculate_avg_resolution_time(self, history: List[Dict]) -> Optional[float]:
        """Calculate average time to resolve issues"""
        resolution_times = []
        
        for entry in history:
            if not entry.get('resolved'):
                continue
                
            try:
                start_time = datetime.fromisoformat(entry['timestamp'])
                end_time = datetime.fromisoformat(entry['resolution_time'])
                duration = (end_time - start_time).total_seconds()
                resolution_times.append(duration)
            except (ValueError, KeyError):
                continue
                
        if not resolution_times:
            return None
            
        return sum(resolution_times) / len(resolution_times)
        
    def _get_most_common_issues(self, history: List[Dict], limit: int = 5) -> List[Dict]:
        """Get most frequently occurring issues"""
        issues = {}
        for entry in history:
            key = (entry['category'], entry['message'])
            issues[key] = issues.get(key, 0) + 1
            
        sorted_issues = sorted(
            issues.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:limit]
        
        return [
            {
                'category': category,
                'message': message,
                'count': count
            }
            for (category, message), count in sorted_issues
        ] 