import time
import logging
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass
from statistics import mean, median

@dataclass
class LatencyRecord:
    """Container for latency measurements"""
    operation: str
    start_time: float
    end_time: float
    file_path: str
    
    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time) * 1000  # Convert to milliseconds

class LatencyMonitor:
    """Monitors and manages operation latency"""
    
    def __init__(self, max_latency: float = 100.0):
        self.logger = logging.getLogger(__name__)
        self.max_latency = max_latency  # Maximum allowed latency in milliseconds
        self.history_size = 1000  # Keep last 1000 measurements
        self.latency_history = deque(maxlen=self.history_size)
        self.current_operations: Dict[str, float] = {}
        
    def start_operation(self, operation: str, file_path: str):
        """Start timing an operation"""
        operation_id = f"{operation}:{file_path}"
        self.current_operations[operation_id] = time.perf_counter()
        
    def end_operation(self, operation: str, file_path: str) -> Optional[float]:
        """End timing an operation and record latency"""
        operation_id = f"{operation}:{file_path}"
        start_time = self.current_operations.pop(operation_id, None)
        
        if start_time is None:
            return None
            
        end_time = time.perf_counter()
        record = LatencyRecord(operation, start_time, end_time, file_path)
        self.latency_history.append(record)
        
        # Log if latency exceeds threshold
        if record.duration > self.max_latency:
            self.logger.warning(
                f"High latency detected: {record.duration:.2f}ms for {operation} "
                f"on {file_path}"
            )
            
        return record.duration
        
    def get_statistics(self) -> Dict:
        """Get latency statistics"""
        if not self.latency_history:
            return {
                'average': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'violations': 0,
                'total_operations': 0
            }
            
        durations = [r.duration for r in self.latency_history]
        violations = sum(1 for d in durations if d > self.max_latency)
        
        return {
            'average': mean(durations),
            'median': median(durations),
            'min': min(durations),
            'max': max(durations),
            'violations': violations,
            'total_operations': len(durations)
        }
        
    def get_violation_details(self) -> List[Dict]:
        """Get details of latency violations"""
        return [
            {
                'operation': r.operation,
                'file_path': r.file_path,
                'latency': r.duration,
                'timestamp': r.start_time
            }
            for r in self.latency_history
            if r.duration > self.max_latency
        ]
        
    def clear_history(self):
        """Clear latency history"""
        self.latency_history.clear()
        self.current_operations.clear() 