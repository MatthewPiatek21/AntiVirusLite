import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from .system_health_monitor import SystemHealthMonitor

@dataclass
class ScanProfile:
    """Scan intensity profile configuration"""
    name: str
    thread_count: int
    batch_size: int
    throttle_delay: float  # seconds
    max_cpu_usage: float  # percentage
    max_memory_usage: float  # MB
    max_io_rate: float  # MB/s
    description: str

class ScanIntensityManager:
    """Manages scan intensity based on system health"""
    
    def __init__(self, health_monitor: SystemHealthMonitor):
        self.logger = logging.getLogger(__name__)
        self.health_monitor = health_monitor
        self.current_profile: Optional[str] = None
        self.last_adjustment = datetime.now()
        self.adjustment_cooldown = timedelta(minutes=5)  # Minimum time between adjustments
        
        # Define scan intensity profiles
        self.profiles = {
            'aggressive': ScanProfile(
                name='aggressive',
                thread_count=8,
                batch_size=5000,
                throttle_delay=0.0,
                max_cpu_usage=80.0,
                max_memory_usage=512,
                max_io_rate=100.0,
                description='Maximum performance, high resource usage'
            ),
            'balanced': ScanProfile(
                name='balanced',
                thread_count=4,
                batch_size=2000,
                throttle_delay=0.05,
                max_cpu_usage=50.0,
                max_memory_usage=384,
                max_io_rate=50.0,
                description='Balanced performance and resource usage'
            ),
            'conservative': ScanProfile(
                name='conservative',
                thread_count=2,
                batch_size=1000,
                throttle_delay=0.1,
                max_cpu_usage=30.0,
                max_memory_usage=256,
                max_io_rate=25.0,
                description='Minimal resource usage, lower performance'
            ),
            'minimal': ScanProfile(
                name='minimal',
                thread_count=1,
                batch_size=500,
                throttle_delay=0.2,
                max_cpu_usage=20.0,
                max_memory_usage=128,
                max_io_rate=10.0,
                description='Emergency mode, lowest resource usage'
            )
        }
        
        # Start with balanced profile
        self.current_profile = 'balanced'
        
    def adjust_intensity(self) -> Optional[ScanProfile]:
        """Adjust scan intensity based on system health"""
        # Check cooldown period
        if datetime.now() - self.last_adjustment < self.adjustment_cooldown:
            return None
            
        try:
            # Get current health status
            health = self.health_monitor.get_current_health()
            if not health:
                return None
                
            # Determine appropriate profile based on system health
            new_profile = self._select_profile(health)
            
            if new_profile != self.current_profile:
                old_profile = self.profiles[self.current_profile]
                new_profile_config = self.profiles[new_profile]
                
                self.logger.info(
                    f"Adjusting scan intensity from {old_profile.name} to {new_profile_config.name} "
                    f"due to system health status: {health['status']}"
                )
                
                self.current_profile = new_profile
                self.last_adjustment = datetime.now()
                
                return new_profile_config
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error adjusting scan intensity: {e}")
            return None
            
    def _select_profile(self, health: Dict) -> str:
        """Select appropriate scan profile based on system health"""
        if health['status'] == 'critical':
            return 'minimal'
            
        # Check memory pressure
        if health['memory_usage'] > 90:
            return 'minimal'
        elif health['memory_usage'] > 75:
            return 'conservative'
            
        # Check CPU usage
        if health['cpu_usage'] > 85:
            return 'minimal'
        elif health['cpu_usage'] > 70:
            return 'conservative'
            
        # Check disk space
        if health['disk_usage'] > 95:
            return 'minimal'
        elif health['disk_usage'] > 85:
            return 'conservative'
            
        # If system is healthy, allow more aggressive scanning
        if health['status'] == 'healthy':
            if (health['memory_usage'] < 50 and 
                health['cpu_usage'] < 40 and 
                health['disk_usage'] < 70):
                return 'aggressive'
                
        # Default to balanced profile
        return 'balanced'
        
    def get_current_profile(self) -> ScanProfile:
        """Get current scan intensity profile"""
        return self.profiles[self.current_profile]
        
    def get_available_profiles(self) -> Dict[str, ScanProfile]:
        """Get all available scan profiles"""
        return self.profiles
        
    def set_profile(self, profile_name: str) -> bool:
        """Manually set scan intensity profile"""
        if profile_name not in self.profiles:
            return False
            
        self.current_profile = profile_name
        self.last_adjustment = datetime.now()
        self.logger.info(f"Manually set scan intensity profile to: {profile_name}")
        return True
        
    def get_profile_stats(self) -> Dict:
        """Get statistics about profile usage"""
        current_profile = self.profiles[self.current_profile]
        health = self.health_monitor.get_current_health()
        
        return {
            'current_profile': current_profile.name,
            'description': current_profile.description,
            'thread_count': current_profile.thread_count,
            'batch_size': current_profile.batch_size,
            'max_cpu_usage': current_profile.max_cpu_usage,
            'max_memory_usage': current_profile.max_memory_usage,
            'last_adjustment': self.last_adjustment.isoformat(),
            'system_status': health.get('status', 'unknown'),
            'resource_usage': {
                'cpu': health.get('cpu_usage', 0),
                'memory': health.get('memory_usage', 0),
                'disk': health.get('disk_usage', 0)
            }
        } 