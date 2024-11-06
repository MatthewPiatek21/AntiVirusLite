import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
from PyQt6.QtCore import QObject, pyqtSignal

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class SystemAlert:
    """Container for system alerts"""
    timestamp: datetime
    severity: AlertSeverity
    category: str
    message: str
    resource_info: Dict
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class AlertManager(QObject):
    """Manages system alerts and notifications"""
    
    # Signals for UI updates
    alert_raised = pyqtSignal(dict)  # New alert
    alert_resolved = pyqtSignal(dict)  # Alert resolved
    alert_status_changed = pyqtSignal(dict)  # Alert status update
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.alerts_dir = Path("data/alerts")
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        
        # Active alerts
        self.active_alerts: List[SystemAlert] = []
        
        # Alert thresholds
        self.thresholds = {
            'disk_space_critical': 1024 * 1024 * 1024,  # 1GB
            'disk_space_warning': 5 * 1024 * 1024 * 1024,  # 5GB
            'memory_critical': 95.0,  # 95% usage
            'memory_warning': 85.0,  # 85% usage
            'cpu_critical': 95.0,  # 95% usage
            'cpu_warning': 85.0,  # 85% usage
            'temperature_critical': 85.0,  # 85°C
            'temperature_warning': 75.0  # 75°C
        }
        
        # Load existing alerts
        self._load_alerts()
        
    def check_system_health(self, health_status: Dict):
        """Check system health and raise alerts if needed"""
        try:
            # Check disk space
            if health_status['disk_space'] < self.thresholds['disk_space_critical']:
                self.raise_alert(
                    AlertSeverity.CRITICAL,
                    "disk_space",
                    f"Critical: Low disk space - {health_status['disk_space'] / 1024 / 1024 / 1024:.1f}GB remaining",
                    health_status
                )
            elif health_status['disk_space'] < self.thresholds['disk_space_warning']:
                self.raise_alert(
                    AlertSeverity.WARNING,
                    "disk_space",
                    f"Warning: Low disk space - {health_status['disk_space'] / 1024 / 1024 / 1024:.1f}GB remaining",
                    health_status
                )
                
            # Check memory usage
            if health_status['memory_usage'] > self.thresholds['memory_critical']:
                self.raise_alert(
                    AlertSeverity.CRITICAL,
                    "memory",
                    f"Critical: High memory usage - {health_status['memory_usage']:.1f}%",
                    health_status
                )
            elif health_status['memory_usage'] > self.thresholds['memory_warning']:
                self.raise_alert(
                    AlertSeverity.WARNING,
                    "memory",
                    f"Warning: High memory usage - {health_status['memory_usage']:.1f}%",
                    health_status
                )
                
            # Check CPU usage
            if health_status['cpu_usage'] > self.thresholds['cpu_critical']:
                self.raise_alert(
                    AlertSeverity.CRITICAL,
                    "cpu",
                    f"Critical: High CPU usage - {health_status['cpu_usage']:.1f}%",
                    health_status
                )
            elif health_status['cpu_usage'] > self.thresholds['cpu_warning']:
                self.raise_alert(
                    AlertSeverity.WARNING,
                    "cpu",
                    f"Warning: High CPU usage - {health_status['cpu_usage']:.1f}%",
                    health_status
                )
                
            # Check CPU temperature if available
            if health_status.get('cpu_temp'):
                temp = health_status['cpu_temp']
                if temp > self.thresholds['temperature_critical']:
                    self.raise_alert(
                        AlertSeverity.CRITICAL,
                        "temperature",
                        f"Critical: High CPU temperature - {temp:.1f}°C",
                        health_status
                    )
                elif temp > self.thresholds['temperature_warning']:
                    self.raise_alert(
                        AlertSeverity.WARNING,
                        "temperature",
                        f"Warning: High CPU temperature - {temp:.1f}°C",
                        health_status
                    )
                    
            # Check for resolved alerts
            self._check_resolved_alerts(health_status)
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
            
    def raise_alert(self, severity: AlertSeverity, category: str, 
                   message: str, resource_info: Dict):
        """Raise a new system alert"""
        # Check if similar alert already exists
        for alert in self.active_alerts:
            if (alert.category == category and 
                alert.severity == severity and 
                not alert.resolved):
                return  # Skip duplicate alert
                
        alert = SystemAlert(
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=message,
            resource_info=resource_info
        )
        
        self.active_alerts.append(alert)
        self._save_alerts()
        
        # Emit signal for UI update
        self.alert_raised.emit(self._alert_to_dict(alert))
        
        # Log alert
        log_level = logging.CRITICAL if severity == AlertSeverity.CRITICAL else logging.WARNING
        self.logger.log(log_level, message)
        
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert"""
        if 0 <= alert_id < len(self.active_alerts):
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            self._save_alerts()
            
            # Emit signal for UI update
            self.alert_status_changed.emit(self._alert_to_dict(alert))
            
    def resolve_alert(self, alert_id: int):
        """Mark an alert as resolved"""
        if 0 <= alert_id < len(self.active_alerts):
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = datetime.now()
            self._save_alerts()
            
            # Emit signal for UI update
            self.alert_resolved.emit(self._alert_to_dict(alert))
            
    def get_active_alerts(self) -> List[Dict]:
        """Get list of active alerts"""
        return [
            self._alert_to_dict(alert)
            for alert in self.active_alerts
            if not alert.resolved
        ]
        
    def get_alert_history(self, days: int = 7) -> List[Dict]:
        """Get alert history for specified number of days"""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            self._alert_to_dict(alert)
            for alert in self.active_alerts
            if alert.timestamp > cutoff
        ]
        
    def _check_resolved_alerts(self, health_status: Dict):
        """Check if any active alerts can be resolved"""
        for i, alert in enumerate(self.active_alerts):
            if alert.resolved:
                continue
                
            # Check if condition is resolved
            resolved = False
            
            if alert.category == "disk_space":
                resolved = health_status['disk_space'] > self.thresholds['disk_space_warning']
            elif alert.category == "memory":
                resolved = health_status['memory_usage'] < self.thresholds['memory_warning']
            elif alert.category == "cpu":
                resolved = health_status['cpu_usage'] < self.thresholds['cpu_warning']
            elif alert.category == "temperature":
                temp = health_status.get('cpu_temp')
                if temp:
                    resolved = temp < self.thresholds['temperature_warning']
                    
            if resolved:
                self.resolve_alert(i)
                
    def _alert_to_dict(self, alert: SystemAlert) -> Dict:
        """Convert alert to dictionary for serialization"""
        return {
            'timestamp': alert.timestamp.isoformat(),
            'severity': alert.severity.value,
            'category': alert.category,
            'message': alert.message,
            'resource_info': alert.resource_info,
            'acknowledged': alert.acknowledged,
            'resolved': alert.resolved,
            'resolution_time': alert.resolution_time.isoformat() 
                             if alert.resolution_time else None
        }
        
    def _save_alerts(self):
        """Save alerts to disk"""
        try:
            alerts_file = self.alerts_dir / "alerts.json"
            alerts_data = [self._alert_to_dict(alert) for alert in self.active_alerts]
            alerts_file.write_text(json.dumps(alerts_data, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save alerts: {e}")
            
    def _load_alerts(self):
        """Load alerts from disk"""
        try:
            alerts_file = self.alerts_dir / "alerts.json"
            if alerts_file.exists():
                alerts_data = json.loads(alerts_file.read_text())
                self.active_alerts = [
                    SystemAlert(
                        timestamp=datetime.fromisoformat(alert['timestamp']),
                        severity=AlertSeverity(alert['severity']),
                        category=alert['category'],
                        message=alert['message'],
                        resource_info=alert['resource_info'],
                        acknowledged=alert['acknowledged'],
                        resolved=alert['resolved'],
                        resolution_time=datetime.fromisoformat(alert['resolution_time'])
                                    if alert['resolution_time'] else None
                    )
                    for alert in alerts_data
                ]
        except Exception as e:
            self.logger.error(f"Failed to load alerts: {e}") 