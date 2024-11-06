import time
import psutil
import logging
from typing import Dict, List, Optional, Deque
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import json
from pathlib import Path

@dataclass
class PerformanceMetric:
    """Container for performance measurements"""
    timestamp: datetime
    scan_speed: float  # files/second
    memory_usage: float  # MB
    cpu_usage: float  # percentage
    disk_io_read: float  # MB/s
    disk_io_write: float  # MB/s
    files_processed: int
    threads_active: int

class PerformanceMonitor:
    """Monitors and tracks system performance metrics"""
    
    def __init__(self, history_size: int = 3600):  # 1 hour of history at 1 sample/second
        self.logger = logging.getLogger(__name__)
        self.history: Deque[PerformanceMetric] = deque(maxlen=history_size)
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_io_counters = psutil.disk_io_counters()
        self.last_io_time = time.time()
        self.metrics_file = Path("data/performance_metrics.json")
        
        # Performance thresholds
        self.thresholds = {
            'scan_speed_min': 1000,  # files/second
            'memory_max': 512,  # MB
            'cpu_max': 30,  # percentage
            'io_max': 50  # MB/s
        }
        
        # Load historical metrics
        self._load_metrics()
        
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("Performance monitoring started")
            
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self._save_metrics()
            self.logger.info("Performance monitoring stopped")
            
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                metric = self._collect_metrics()
                self.history.append(metric)
                self._check_thresholds(metric)
                time.sleep(1)  # Collect metrics every second
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                
    def _collect_metrics(self) -> PerformanceMetric:
        """Collect current performance metrics"""
        # Get CPU and memory usage
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Calculate disk I/O rates
        current_io = psutil.disk_io_counters()
        current_time = time.time()
        time_delta = current_time - self.last_io_time
        
        read_speed = (current_io.read_bytes - self.last_io_counters.read_bytes) / time_delta / 1024 / 1024
        write_speed = (current_io.write_bytes - self.last_io_counters.write_bytes) / time_delta / 1024 / 1024
        
        self.last_io_counters = current_io
        self.last_io_time = current_time
        
        # Get thread count
        threads_active = threading.active_count()
        
        return PerformanceMetric(
            timestamp=datetime.now(),
            scan_speed=self._calculate_scan_speed(),
            memory_usage=memory.used / 1024 / 1024,  # Convert to MB
            cpu_usage=cpu_percent,
            disk_io_read=read_speed,
            disk_io_write=write_speed,
            files_processed=self._get_files_processed(),
            threads_active=threads_active
        )
        
    def _calculate_scan_speed(self) -> float:
        """Calculate current scan speed (files/second)"""
        if len(self.history) < 2:
            return 0.0
            
        recent_metrics = list(self.history)[-2:]
        files_delta = recent_metrics[1].files_processed - recent_metrics[0].files_processed
        time_delta = (recent_metrics[1].timestamp - recent_metrics[0].timestamp).total_seconds()
        
        return files_delta / time_delta if time_delta > 0 else 0.0
        
    def _get_files_processed(self) -> int:
        """Get total files processed"""
        return sum(1 for metric in self.history if metric.scan_speed > 0)
        
    def _check_thresholds(self, metric: PerformanceMetric):
        """Check if metrics exceed thresholds"""
        violations = []
        
        if metric.scan_speed < self.thresholds['scan_speed_min']:
            violations.append(f"Scan speed below minimum: {metric.scan_speed:.1f} files/sec")
            
        if metric.memory_usage > self.thresholds['memory_max']:
            violations.append(f"Memory usage exceeds maximum: {metric.memory_usage:.1f} MB")
            
        if metric.cpu_usage > self.thresholds['cpu_max']:
            violations.append(f"CPU usage exceeds maximum: {metric.cpu_usage:.1f}%")
            
        if max(metric.disk_io_read, metric.disk_io_write) > self.thresholds['io_max']:
            violations.append(f"Disk I/O exceeds maximum: {max(metric.disk_io_read, metric.disk_io_write):.1f} MB/s")
            
        if violations:
            self.logger.warning("Performance thresholds exceeded:\n" + "\n".join(violations))
            
    def get_current_metrics(self) -> Dict:
        """Get current performance metrics"""
        if not self.history:
            return {}
            
        latest = self.history[-1]
        return {
            'timestamp': latest.timestamp.isoformat(),
            'scan_speed': latest.scan_speed,
            'memory_usage': latest.memory_usage,
            'cpu_usage': latest.cpu_usage,
            'disk_io_read': latest.disk_io_read,
            'disk_io_write': latest.disk_io_write,
            'files_processed': latest.files_processed,
            'threads_active': latest.threads_active
        }
        
    def get_average_metrics(self, duration: timedelta = timedelta(minutes=5)) -> Dict:
        """Get average metrics over specified duration"""
        cutoff_time = datetime.now() - duration
        recent_metrics = [m for m in self.history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {}
            
        return {
            'scan_speed': sum(m.scan_speed for m in recent_metrics) / len(recent_metrics),
            'memory_usage': sum(m.memory_usage for m in recent_metrics) / len(recent_metrics),
            'cpu_usage': sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics),
            'disk_io_read': sum(m.disk_io_read for m in recent_metrics) / len(recent_metrics),
            'disk_io_write': sum(m.disk_io_write for m in recent_metrics) / len(recent_metrics),
            'files_processed': recent_metrics[-1].files_processed - recent_metrics[0].files_processed,
            'duration_seconds': (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
        }
        
    def _save_metrics(self):
        """Save metrics history to disk"""
        try:
            metrics_data = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'scan_speed': m.scan_speed,
                    'memory_usage': m.memory_usage,
                    'cpu_usage': m.cpu_usage,
                    'disk_io_read': m.disk_io_read,
                    'disk_io_write': m.disk_io_write,
                    'files_processed': m.files_processed,
                    'threads_active': m.threads_active
                }
                for m in self.history
            ]
            
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            self.metrics_file.write_text(json.dumps(metrics_data, indent=2))
            
        except Exception as e:
            self.logger.error(f"Failed to save performance metrics: {e}")
            
    def _load_metrics(self):
        """Load metrics history from disk"""
        try:
            if self.metrics_file.exists():
                metrics_data = json.loads(self.metrics_file.read_text())
                self.history.extend(
                    PerformanceMetric(
                        timestamp=datetime.fromisoformat(m['timestamp']),
                        scan_speed=m['scan_speed'],
                        memory_usage=m['memory_usage'],
                        cpu_usage=m['cpu_usage'],
                        disk_io_read=m['disk_io_read'],
                        disk_io_write=m['disk_io_write'],
                        files_processed=m['files_processed'],
                        threads_active=m['threads_active']
                    )
                    for m in metrics_data
                )
                
        except Exception as e:
            self.logger.error(f"Failed to load performance metrics: {e}") 