import logging
import time
import psutil
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock

@dataclass
class ThrottleRule:
    """Rule for resource throttling"""
    resource: str  # 'cpu', 'memory', 'disk_io'
    threshold: float  # Percentage or absolute value
    reduction: float  # How much to reduce resource usage
    cooldown: int  # Seconds to wait before releasing throttle
    priority: int  # 1-10, higher means more aggressive throttling

class ResourceThrottler:
    """Manages system resource throttling"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.throttle_lock = Lock()
        self.is_throttled = False
        self.throttle_start: Optional[datetime] = None
        self.current_rules: List[ThrottleRule] = []
        self.throttle_callbacks: Dict[str, List[Callable]] = {
            'cpu': [],
            'memory': [],
            'disk_io': []
        }
        
        # Default throttle rules
        self.rules = [
            ThrottleRule(
                resource='cpu',
                threshold=80.0,  # 80% CPU usage
                reduction=0.5,   # Reduce by 50%
                cooldown=30,     # 30 seconds cooldown
                priority=8
            ),
            ThrottleRule(
                resource='memory',
                threshold=85.0,  # 85% memory usage
                reduction=0.4,   # Reduce by 40%
                cooldown=60,     # 1 minute cooldown
                priority=9
            ),
            ThrottleRule(
                resource='disk_io',
                threshold=90.0,  # 90% disk I/O
                reduction=0.6,   # Reduce by 60%
                cooldown=20,     # 20 seconds cooldown
                priority=7
            )
        ]
        
    def register_callback(self, resource: str, callback: Callable):
        """Register a callback for throttling events"""
        if resource in self.throttle_callbacks:
            self.throttle_callbacks[resource].append(callback)
            
    def check_resources(self) -> bool:
        """Check if throttling is needed"""
        with self.throttle_lock:
            # Check if we're in cooldown
            if self.is_throttled and self.throttle_start:
                for rule in self.current_rules:
                    elapsed = (datetime.now() - self.throttle_start).total_seconds()
                    if elapsed < rule.cooldown:
                        return True
                # Cooldown complete
                self.release_throttle()
                return False
                
            # Get current resource usage
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_io_counters()
            
            triggered_rules = []
            
            # Check CPU usage
            if cpu_percent > self.get_rule('cpu').threshold:
                triggered_rules.append(self.get_rule('cpu'))
                
            # Check memory usage
            if memory.percent > self.get_rule('memory').threshold:
                triggered_rules.append(self.get_rule('memory'))
                
            # Check disk I/O (simplified)
            disk_io_percent = (disk.read_bytes + disk.write_bytes) / (1024 * 1024)  # MB/s
            if disk_io_percent > self.get_rule('disk_io').threshold:
                triggered_rules.append(self.get_rule('disk_io'))
                
            if triggered_rules:
                self.apply_throttle(triggered_rules)
                return True
                
            return False
            
    def apply_throttle(self, rules: List[ThrottleRule]):
        """Apply throttling based on triggered rules"""
        with self.throttle_lock:
            self.is_throttled = True
            self.throttle_start = datetime.now()
            self.current_rules = rules
            
            # Sort rules by priority
            rules.sort(key=lambda r: r.priority, reverse=True)
            
            for rule in rules:
                self.logger.warning(
                    f"Applying throttle for {rule.resource}: "
                    f"reduction={rule.reduction*100}%, "
                    f"cooldown={rule.cooldown}s"
                )
                
                # Call registered callbacks
                for callback in self.throttle_callbacks[rule.resource]:
                    try:
                        callback(rule.reduction)
                    except Exception as e:
                        self.logger.error(f"Error in throttle callback: {e}")
                        
    def release_throttle(self):
        """Release throttling"""
        with self.throttle_lock:
            if self.is_throttled:
                self.logger.info("Releasing resource throttle")
                self.is_throttled = False
                self.throttle_start = None
                self.current_rules.clear()
                
    def get_rule(self, resource: str) -> ThrottleRule:
        """Get throttle rule for resource"""
        for rule in self.rules:
            if rule.resource == resource:
                return rule
        raise ValueError(f"No rule found for resource: {resource}")
        
    def update_rule(self, resource: str, **kwargs):
        """Update throttle rule parameters"""
        for rule in self.rules:
            if rule.resource == resource:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                break
                
    def get_status(self) -> Dict:
        """Get current throttling status"""
        return {
            'is_throttled': self.is_throttled,
            'throttle_start': self.throttle_start.isoformat() if self.throttle_start else None,
            'active_rules': [
                {
                    'resource': rule.resource,
                    'reduction': rule.reduction,
                    'cooldown': rule.cooldown,
                    'priority': rule.priority
                }
                for rule in self.current_rules
            ],
            'current_usage': {
                'cpu': psutil.cpu_percent(),
                'memory': psutil.virtual_memory().percent,
                'disk_io': sum(getattr(psutil.disk_io_counters(), counter) 
                              for counter in ['read_bytes', 'write_bytes']) / (1024 * 1024)
            }
        } 