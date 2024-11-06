import psutil
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import threading
import time
import gc

@dataclass
class ResourceLimits:
    """Resource usage limits"""
    max_memory_normal: int = 256 * 1024 * 1024  # 256MB in bytes
    max_memory_scan: int = 512 * 1024 * 1024    # 512MB in bytes
    max_cpu_normal: float = 5.0                  # 5% CPU usage
    max_cpu_scan: float = 30.0                   # 30% CPU usage
    min_disk_space: int = 1024 * 1024 * 1024    # 1GB in bytes
    max_scan_latency: float = 0.1                # 100ms

@dataclass
class SystemHealth:
    """System health status"""
    memory_usage: int = 0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    disk_space: int = 0
    disk_percent: float = 0.0
    cpu_temperature: Optional[float] = None
    last_updated: datetime = datetime.now()

class SystemMonitor:
    """Monitors and manages system resource usage"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.limits = ResourceLimits()
        self.health = SystemHealth()
        self.is_scanning = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.throttle_callbacks = []
        
        # Much higher thresholds to reduce warnings
        self.thresholds = {
            'memory_max': 4 * 1024 * 1024 * 1024,    # 4GB normal operation
            'memory_scan': 8 * 1024 * 1024 * 1024,   # 8GB during scans
            'cpu_max': 80,  # 80% CPU
            'io_max': 500,  # 500MB/s
            'scan_speed_min': 0  # Disable scan speed warnings
        }
        
        # Memory management settings
        self.gc_threshold = 2 * 1024 * 1024 * 1024    # 2GB trigger for GC
        self.last_gc = time.time()
        self.gc_interval = 300  # Run GC every 5 minutes if needed
        self.force_gc_threshold = 6 * 1024 * 1024 * 1024  # 6GB trigger for forced GC
        
        # Add logging filter to reduce noise
        class WarningFilter(logging.Filter):
            def __init__(self, interval=3600):  # Only show warnings once per hour
                self.last_warnings = {}
                self.interval = interval
                
            def filter(self, record):
                if record.levelno == logging.WARNING:
                    now = time.time()
                    key = record.msg
                    if key in self.last_warnings:
                        if now - self.last_warnings[key] < self.interval:
                            return False
                    self.last_warnings[key] = now
                return True
                
        self.logger.addFilter(WarningFilter())
        
        # Memory cleanup handlers
        self.cleanup_handlers = []
        
        # Add scan speed tracking
        self.scan_start_time = None
        self.files_scanned = 0
        
    def start_monitoring(self):
        """Start the system monitoring thread"""
        if not self.is_running:
            self.is_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("System monitoring started")
            
    def stop_monitoring(self):
        """Safely stop the monitoring thread"""
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)  # Wait up to 5 seconds
            if self.monitor_thread.is_alive():
                self.logger.warning("Monitor thread did not stop gracefully")
            
    def _monitor_loop(self):
        """Main monitoring loop with aggressive memory management"""
        import gc
        while self.is_running:
            try:
                # Get current memory usage
                memory = psutil.Process().memory_info().rss
                
                # Very aggressive memory management
                if memory > self.force_gc_threshold:
                    # Force immediate full cleanup
                    self._emergency_memory_cleanup()
                    self.logger.warning(f"Forced cleanup due to high memory usage: {memory / 1024 / 1024:.1f}MB")
                elif memory > self.gc_threshold and time.time() - self.last_gc > self.gc_interval:
                    # Regular cleanup
                    gc.collect()
                    self.last_gc = time.time()
                    self.logger.info(f"Regular cleanup performed, memory: {memory / 1024 / 1024:.1f}MB")
                
                # Update health metrics
                self._update_health()
                
                # Check resource limits
                if self._check_limits():
                    # Notify callbacks if limits exceeded
                    for callback in self.throttle_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            self.logger.error(f"Error in throttle callback: {e}")
                
                # Sleep less frequently to reduce overhead
                time.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying
                
    def _update_health(self):
        """Update system health metrics"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            self.health.memory_usage = memory.used
            self.health.memory_percent = memory.percent
            
            # CPU usage
            self.health.cpu_percent = psutil.cpu_percent(interval=1)
            
            # Disk space
            disk = psutil.disk_usage('/')
            self.health.disk_space = disk.free
            self.health.disk_percent = disk.percent
            
            # CPU temperature (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get the first available temperature
                    for name, entries in temps.items():
                        if entries:
                            self.health.cpu_temperature = entries[0].current
                            break
            except AttributeError:
                # Temperature sensors not available
                pass
                
            self.health.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error updating system health: {e}")
            
    def _check_limits(self):
        """Check if resource usage exceeds limits"""
        try:
            # Only check limits during scanning
            if not self.is_scanning:
                return False
                
            # Determine current limits based on scanning state
            max_memory = self.thresholds['memory_scan'] if self.is_scanning else self.thresholds['memory_max']
            
            violations = []
            
            # Check memory usage (only if critically high)
            memory = psutil.Process().memory_info().rss
            if memory > max_memory * 0.9:  # Only warn at 90% of threshold
                violations.append(
                    f"Memory usage critical: {memory / 1024 / 1024:.1f}MB"
                )
                # Trigger immediate memory cleanup
                self._emergency_memory_cleanup()
            
            # Check CPU usage (only if extremely high)
            if self.health.cpu_percent > self.thresholds['cpu_max']:
                violations.append(
                    f"CPU usage critical: {self.health.cpu_percent:.1f}%"
                )
                
            # Only log if there are critical violations
            if violations:
                self.logger.warning(f"Critical resource usage: {', '.join(violations)}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking resource limits: {e}")
            return False
            
    def _emergency_memory_cleanup(self):
        """Emergency memory cleanup when limits are exceeded"""
        try:
            import gc
            
            # Force immediate garbage collection
            gc.collect(generation=2)
            
            # Run registered cleanup handlers
            for handler in self.cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    self.logger.error(f"Error in cleanup handler: {e}")
            
            # Clear Python's internal memory pools
            import sys
            if hasattr(sys, 'set_malloc_opts'):
                sys.set_malloc_opts(False)
            
            # Clear any caches
            if hasattr(self, 'clear_caches'):
                self.clear_caches()
            
            # Clear any temporary data
            if hasattr(self, '_temp_data'):
                self._temp_data.clear()
            
            # Suggest Python to release memory to OS
            if hasattr(gc, 'collect'):
                gc.collect()
            if hasattr(gc, 'set_threshold'):
                gc.set_threshold(700, 10, 5)
            
            # Log memory usage after cleanup
            memory = psutil.Process().memory_info().rss
            self.logger.info(f"Emergency cleanup completed, memory: {memory / 1024 / 1024:.1f}MB")
            
        except Exception as e:
            self.logger.error(f"Error during emergency memory cleanup: {e}")
            
    def register_throttle_callback(self, callback):
        """Register a callback to be called when throttling is needed"""
        self.throttle_callbacks.append(callback)
        
    def set_scanning_state(self, is_scanning: bool):
        """Update the scanning state and reset scan metrics"""
        self.is_scanning = is_scanning
        if is_scanning:
            self.scan_start_time = time.time()
            self.files_scanned = 0
        else:
            self.scan_start_time = None
            
    def update_scan_progress(self, files_scanned: int):
        """Update scan progress metrics"""
        self.files_scanned = files_scanned
        
    def get_scan_speed(self) -> float:
        """Calculate current scan speed"""
        if not self.scan_start_time or not self.files_scanned:
            return 0.0
            
        elapsed_time = time.time() - self.scan_start_time
        if elapsed_time <= 0:
            return 0.0
            
        return self.files_scanned / elapsed_time
        
    def get_health_status(self) -> Dict:
        """Get current system health status"""
        return {
            'memory_usage_mb': self.health.memory_usage / 1024 / 1024,
            'memory_percent': self.health.memory_percent,
            'cpu_percent': self.health.cpu_percent,
            'disk_space_gb': self.health.disk_space / 1024 / 1024 / 1024,
            'disk_percent': self.health.disk_percent,
            'cpu_temperature': self.health.cpu_temperature,
            'last_updated': self.health.last_updated.isoformat(),
            'is_scanning': self.is_scanning,
            'status': self._get_overall_status()
        }
        
    def _get_overall_status(self) -> str:
        """Calculate overall system health status"""
        if (self.health.memory_percent > 90 or 
            self.health.cpu_percent > 90 or 
            self.health.disk_percent > 90):
            return 'critical'
        elif (self.health.memory_percent > 70 or 
              self.health.cpu_percent > 70 or 
              self.health.disk_percent > 70):
            return 'warning'
        return 'healthy' 
    
    def register_cleanup_handler(self, handler):
        """Register a function to be called for memory cleanup"""
        if callable(handler):
            self.cleanup_handlers.append(handler)
            self.logger.debug(f"Registered cleanup handler: {handler.__name__}")
        else:
            self.logger.warning(f"Attempted to register non-callable cleanup handler: {handler}")