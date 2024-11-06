import psutil
import logging
import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
from .alert_manager import AlertManager
from .health_logger import HealthLogger, HealthLogLevel

@dataclass
class HealthThresholds:
    """System health thresholds"""
    min_disk_space: int = 1024 * 1024 * 1024  # 1GB in bytes
    max_memory_usage: float = 85.0  # percentage
    max_cpu_temp: float = 85.0  # Celsius
    max_cpu_usage: float = 90.0  # percentage
    min_disk_free: float = 10.0  # percentage

@dataclass
class HealthStatus:
    """Container for system health status"""
    timestamp: datetime
    disk_space: int  # bytes
    disk_usage: float  # percentage
    memory_usage: float  # percentage
    memory_available: int  # bytes
    cpu_usage: float  # percentage
    cpu_temp: Optional[float]  # Celsius
    io_counters: Dict  # disk I/O stats
    critical_services: Dict  # service status
    status: str  # 'healthy', 'warning', 'critical'
    issues: List[str]

class SystemHealthMonitor:
    """Monitors and manages system health"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.thresholds = HealthThresholds()
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_monitoring = False
        self.health_log_path = Path("data/health")
        self.health_log_path.mkdir(parents=True, exist_ok=True)
        
        # Critical services to monitor
        self.critical_services = [
            'antivirus',
            'realtime_protection',
            'update_service'
        ]
        
        # Alert callbacks
        self.alert_callbacks = []
        
        # Health history
        self.health_history: List[HealthStatus] = []
        self.max_history = 1440  # 24 hours at 1-minute intervals
        
        # Initialize alert manager
        self.alert_manager = AlertManager()
        
        # Initialize health logger
        self.health_logger = HealthLogger()
        
    def start_monitoring(self):
        """Start health monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("System health monitoring started")
            
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.logger.info("System health monitoring stopped")
            
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                health_status = self._check_system_health()
                self._update_health_history(health_status)
                self._check_alerts(health_status)
                self._log_health_status(health_status)
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                
    def _check_system_health(self) -> HealthStatus:
        """Check current system health status"""
        issues = []
        
        # Get disk space
        disk = psutil.disk_usage('/')
        if disk.free < self.thresholds.min_disk_space:
            issues.append(f"Low disk space: {disk.free / 1024 / 1024 / 1024:.1f}GB free")
            
        # Get memory usage
        memory = psutil.virtual_memory()
        if memory.percent > self.thresholds.max_memory_usage:
            issues.append(f"High memory usage: {memory.percent:.1f}%")
            
        # Get CPU usage and temperature
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > self.thresholds.max_cpu_usage:
            issues.append(f"High CPU usage: {cpu_usage:.1f}%")
            
        # Try to get CPU temperature
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        cpu_temp = entries[0].current
                        if cpu_temp > self.thresholds.max_cpu_temp:
                            issues.append(f"High CPU temperature: {cpu_temp:.1f}°C")
                        break
        except:
            pass
            
        # Check critical services
        services_status = self._check_critical_services()
        for service, status in services_status.items():
            if not status['running']:
                issues.append(f"Critical service not running: {service}")
                
        # Determine overall status
        if any(i.startswith("Critical") for i in issues):
            status = "critical"
        elif issues:
            status = "warning"
        else:
            status = "healthy"
            
        return HealthStatus(
            timestamp=datetime.now(),
            disk_space=disk.free,
            disk_usage=disk.percent,
            memory_usage=memory.percent,
            memory_available=memory.available,
            cpu_usage=cpu_usage,
            cpu_temp=cpu_temp,
            io_counters=psutil.disk_io_counters()._asdict(),
            critical_services=services_status,
            status=status,
            issues=issues
        )
        
    def _check_critical_services(self) -> Dict:
        """Check status of critical services"""
        status = {}
        for service in self.critical_services:
            try:
                # This is a simplified check - in production, you'd check actual services
                status[service] = {
                    'running': True,
                    'uptime': 0,
                    'memory_usage': 0
                }
            except Exception as e:
                self.logger.error(f"Error checking service {service}: {e}")
                status[service] = {
                    'running': False,
                    'error': str(e)
                }
        return status
        
    def _update_health_history(self, status: HealthStatus):
        """Update health history"""
        self.health_history.append(status)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
            
    def _check_alerts(self, status: HealthStatus):
        """Check if alerts should be triggered"""
        if status.status in ['warning', 'critical']:
            for callback in self.alert_callbacks:
                try:
                    callback(status)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
                    
    def _log_health_status(self, status: HealthStatus):
        """Log health status to disk"""
        try:
            log_file = self.health_log_path / f"health_{status.timestamp.strftime('%Y%m%d')}.json"
            
            # Load existing log if it exists
            if log_file.exists():
                log_data = json.loads(log_file.read_text())
            else:
                log_data = []
                
            # Add new status
            log_data.append({
                'timestamp': status.timestamp.isoformat(),
                'disk_space': status.disk_space,
                'disk_usage': status.disk_usage,
                'memory_usage': status.memory_usage,
                'memory_available': status.memory_available,
                'cpu_usage': status.cpu_usage,
                'cpu_temp': status.cpu_temp,
                'io_counters': status.io_counters,
                'critical_services': status.critical_services,
                'status': status.status,
                'issues': status.issues
            })
            
            # Save updated log
            log_file.write_text(json.dumps(log_data, indent=2))
            
        except Exception as e:
            self.logger.error(f"Failed to log health status: {e}")
            
    def register_alert_callback(self, callback):
        """Register a callback for health alerts"""
        self.alert_callbacks.append(callback)
        
    def get_current_health(self) -> Dict:
        """Get current system health status"""
        if not self.health_history:
            return {}
            
        latest = self.health_history[-1]
        return {
            'timestamp': latest.timestamp.isoformat(),
            'disk_space_gb': latest.disk_space / 1024 / 1024 / 1024,
            'disk_usage': latest.disk_usage,
            'memory_usage': latest.memory_usage,
            'memory_available_mb': latest.memory_available / 1024 / 1024,
            'cpu_usage': latest.cpu_usage,
            'cpu_temp': latest.cpu_temp,
            'status': latest.status,
            'issues': latest.issues
        }
        
    def get_health_history(self, duration: timedelta = timedelta(hours=1)) -> List[Dict]:
        """Get health history for specified duration"""
        cutoff_time = datetime.now() - duration
        return [
            {
                'timestamp': status.timestamp.isoformat(),
                'disk_usage': status.disk_usage,
                'memory_usage': status.memory_usage,
                'cpu_usage': status.cpu_usage,
                'status': status.status
            }
            for status in self.health_history
            if status.timestamp > cutoff_time
        ]
        
    def update_thresholds(self, **kwargs):
        """Update health monitoring thresholds"""
        for key, value in kwargs.items():
            if hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)
                self.logger.info(f"Updated threshold {key} to {value}") 