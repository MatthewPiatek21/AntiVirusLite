import os
import time
import logging
from typing import List, Dict, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

@dataclass
class ScanBatch:
    """Container for a batch of files to scan"""
    files: List[Path]
    total_size: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0
        
    @property
    def files_per_second(self) -> float:
        if self.duration > 0:
            return len(self.files) / self.duration
        return 0.0
        
    @property
    def mb_per_second(self) -> float:
        if self.duration > 0:
            return (self.total_size / 1024 / 1024) / self.duration
        return 0.0

class ScanOptimizer:
    """Optimizes scan performance"""
    
    def __init__(self, target_speed: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.target_speed = target_speed  # Files per second
        self.batch_size = 1000  # Initial batch size
        self.max_batch_size = 5000
        self.min_batch_size = 100
        
        # Performance tracking
        self.total_files = 0
        self.total_size = 0
        self.start_time = 0.0
        self.batches: List[ScanBatch] = []
        
        # File type optimization
        self.skip_extensions: Set[str] = {
            '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.wav',
            '.avi', '.mov', '.mkv', '.pdf', '.zip', '.rar', '.7z'
        }
        
        # Path optimization
        self.skip_paths: Set[str] = {
            'node_modules', 'venv', '.git', '.svn', '__pycache__'
        }
        
    def should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned based on optimization rules"""
        # Skip certain file types
        if file_path.suffix.lower() in self.skip_extensions:
            return False
            
        # Skip certain paths
        if any(part in self.skip_paths for part in file_path.parts):
            return False
            
        return True
        
    def create_batch(self, files: List[Path]) -> List[List[Path]]:
        """Split files into optimally sized batches"""
        batches = []
        current_batch = []
        current_size = 0
        
        for file in files:
            try:
                file_size = file.stat().st_size
                if current_size + file_size > 50 * 1024 * 1024:  # 50MB per batch
                    if current_batch:
                        batches.append(current_batch)
                    current_batch = [file]
                    current_size = file_size
                else:
                    current_batch.append(file)
                    current_size += file_size
            except (OSError, IOError):
                continue
                
        if current_batch:
            batches.append(current_batch)
            
        return batches
        
    def adjust_batch_size(self, last_batch: ScanBatch):
        """Adjust batch size based on performance"""
        if last_batch.files_per_second < self.target_speed * 0.8:
            # Too slow, reduce batch size
            self.batch_size = max(
                self.min_batch_size,
                int(self.batch_size * 0.8)
            )
        elif last_batch.files_per_second > self.target_speed * 1.2:
            # Too fast, increase batch size
            self.batch_size = min(
                self.max_batch_size,
                int(self.batch_size * 1.2)
            )
            
    def start_batch(self, files: List[Path]) -> ScanBatch:
        """Start a new scan batch"""
        batch = ScanBatch(files=files)
        batch.start_time = time.time()
        try:
            batch.total_size = sum(f.stat().st_size for f in files)
        except (OSError, IOError):
            pass
        return batch
        
    def end_batch(self, batch: ScanBatch):
        """End a scan batch and update statistics"""
        batch.end_time = time.time()
        self.batches.append(batch)
        
        # Update performance tracking
        self.total_files += len(batch.files)
        self.total_size += batch.total_size
        
        # Adjust batch size for next iteration
        self.adjust_batch_size(batch)
        
        # Log performance metrics
        self.logger.debug(
            f"Batch completed: {len(batch.files)} files, "
            f"{batch.files_per_second:.1f} files/sec, "
            f"{batch.mb_per_second:.1f} MB/sec"
        )
        
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        duration = time.time() - self.start_time if self.start_time else 0
        return {
            'total_files': self.total_files,
            'total_size_mb': self.total_size / 1024 / 1024,
            'duration_seconds': duration,
            'files_per_second': self.total_files / duration if duration > 0 else 0,
            'mb_per_second': (self.total_size / 1024 / 1024) / duration if duration > 0 else 0,
            'current_batch_size': self.batch_size,
            'batch_count': len(self.batches)
        }
        
    def reset_stats(self):
        """Reset performance statistics"""
        self.total_files = 0
        self.total_size = 0
        self.start_time = time.time()
        self.batches.clear() 