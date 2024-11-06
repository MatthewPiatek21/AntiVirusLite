import hashlib
import os
import logging
import subprocess
import shutil
import time
import re
import psutil
import json
import base64
from cryptography.fernet import Fernet
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from .quarantine_manager import QuarantineManager
from .system_monitor import SystemMonitor
from .scan_optimizer import ScanOptimizer
import asyncio
from concurrent.futures import as_completed
from .latency_monitor import LatencyMonitor
from .platform_utils import PlatformUtils
from .performance_monitor import PerformanceMonitor
from .resource_throttler import ResourceThrottler
from .performance_analyzer import PerformanceAnalyzer
from .system_health_monitor import SystemHealthMonitor
from .scan_intensity_manager import ScanIntensityManager
import gc
import weakref
from typing import Iterator
import yara  # You'll need to install this: pip install yara-python

# Make magic import optional
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    print("libmagic not found - file type detection will be limited")

@dataclass
class ScanStats:
    """Statistics for scanning operations"""
    start_time: float
    files_scanned: int = 0
    files_infected: int = 0
    files_error: int = 0
    bytes_scanned: int = 0

    @property
    def scan_duration(self) -> float:
        return time.time() - self.start_time

    @property
    def scan_speed(self) -> float:
        """Calculate files per second"""
        duration = self.scan_duration
        return self.files_scanned / duration if duration > 0 else 0

@dataclass
class HeuristicRule:
    """Rule for heuristic-based detection"""
    name: str
    pattern: str
    severity: int  # 1-10
    description: str

@dataclass
class QuarantineMetadata:
    """Metadata for quarantined files"""
    original_path: str
    timestamp: str
    file_hash: str
    threat_info: List[Dict]
    original_permissions: int
    encryption_key: bytes

class ScanEngine:
    """Core scanning engine for malware detection"""
    
    def __init__(self, auto_start=False):
        # Initialize logging with proper levels as per PRD 1.4
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize core components
        self.signature_database: Dict[str, str] = {}
        self.max_threads = min(os.cpu_count() or 2, 4)  # Limit to 4 threads max
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_threads,
            thread_name_prefix="ScanWorker"
        )
        self.quarantine_path = Path("quarantine")
        self.quarantine_meta_path = self.quarantine_path / "metadata.json"
        self.quarantine_key = Fernet.generate_key()
        self.fernet = Fernet(self.quarantine_key)
        self.stats = ScanStats(start_time=time.time())
        
        # Initialize quarantine directory
        self.quarantine_path.mkdir(exist_ok=True)
        
        # Initialize heuristic rules
        self.heuristic_rules: List[HeuristicRule] = [
            HeuristicRule(
                name="Suspicious Script",
                pattern=r"(eval|exec)\s*\(\s*base64\.b64decode",
                severity=8,
                description="Possible encoded malicious code execution"
            ),
            HeuristicRule(
                name="System Modification",
                pattern=r"(registry\.write|regwrite|regedit)",
                severity=7,
                description="Attempt to modify system registry"
            ),
            # Add more rules as needed
        ]
        
        # Known suspicious process behaviors
        self.suspicious_behaviors: Set[str] = {
            "process_injection",
            "keylogging",
            "network_scanning",
            "file_encryption",
        }

        # Create quarantine directory and initialize metadata
        self.quarantine_path.mkdir(exist_ok=True)
        self._init_quarantine_metadata()

        # Initialize quarantine manager
        self.quarantine_manager = QuarantineManager(Path("data"))

        # Initialize system monitor
        self.system_monitor = SystemMonitor()
        self.system_monitor.register_throttle_callback(self._handle_throttling)
        
        # Only start monitoring if auto_start is True
        if auto_start:
            self.system_monitor.start_monitoring()

        # Initialize scan optimizer
        self.optimizer = ScanOptimizer(target_speed=1000)

        # Initialize latency monitor
        self.latency_monitor = LatencyMonitor(max_latency=100.0)  # 100ms max latency

        # Initialize platform utilities
        self.platform_utils = PlatformUtils()
        
        # Update paths based on platform
        self.system_paths = self.platform_utils.get_system_paths()
        self.critical_dirs = self.platform_utils.get_critical_directories()
        self.startup_locations = self.platform_utils.get_startup_locations()
        
        # Check privileges
        if not self.platform_utils.is_admin:
            self.logger.warning(
                "Running without administrative privileges. "
                "Some features may be limited."
            )
            
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor()
        self.performance_monitor.start_monitoring()

        # Initialize resource throttler
        self.throttler = ResourceThrottler()
        
        # Register throttling callbacks
        self.throttler.register_callback('cpu', self._handle_cpu_throttle)
        self.throttler.register_callback('memory', self._handle_memory_throttle)
        self.throttler.register_callback('disk_io', self._handle_disk_throttle)

        # Initialize performance analyzer
        self.performance_analyzer = PerformanceAnalyzer(self.performance_monitor)

        # Initialize system health monitor
        self.health_monitor = SystemHealthMonitor()
        self.health_monitor.register_alert_callback(self._handle_health_alert)
        self.health_monitor.start_monitoring()

        # Initialize scan intensity manager
        self.intensity_manager = ScanIntensityManager(self.health_monitor)

        # Add memory optimization settings
        self.cache = weakref.WeakValueDictionary()  # Use weak references for caching
        self.batch_size = 1000  # Process files in smaller batches

        # Register cleanup handler
        self.system_monitor.register_cleanup_handler(self._cleanup_scan_data)
        
        # Add memory management
        self._temp_data = {}
        self.max_batch_size = 500  # Reduce batch size
        self.signature_cache_size = 1000  # Limit signature cache

        # Initialize virus detection components
        self.virus_signatures = {
            # Known malware file hashes (SHA-256)
            'hashes': set([
                'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',  # Example malware hash
            ]),
            
            # Suspicious file patterns
            'patterns': [
                rb'(?i)(?:eval|exec)\s*\(\s*(?:base64|compile|marshal)\.(?:b64decode|loads)',  # Encoded execution
                rb'(?i)(?:os|subprocess|system)(?:\.|\s+)(?:system|popen|exec)',  # System command execution
                rb'(?i)(?:win32api|winreg|_winreg)\.(?:RegOpenKey|RegSetValue)',  # Registry manipulation
            ],
            
            # Suspicious file extensions
            'suspicious_extensions': {
                '.exe', '.dll', '.scr', '.bat', '.cmd', '.vbs', '.js',
                '.jar', '.ps1', '.msi', '.com', '.pif', '.hta'
            }
        }
        
        # YARA rules for malware detection
        self.yara_rules = """
            rule Suspicious_Behavior {
                strings:
                    $s1 = "CreateRemoteThread" wide ascii
                    $s2 = "VirtualAllocEx" wide ascii
                    $s3 = "WriteProcessMemory" wide ascii
                    $s4 = "LoadLibraryA" wide ascii
                    $crypto1 = "CryptoAPI" wide ascii
                    $crypto2 = "AES" wide ascii
                    $crypto3 = "RC4" wide ascii
                    $network1 = "WinSock" wide ascii
                    $network2 = "Socket" wide ascii
                    $network3 = "HTTP" wide ascii
                    
                condition:
                    2 of ($s*) or
                    all of ($crypto*) or
                    all of ($network*)
            }
            
            rule Ransomware_Indicators {
                strings:
                    $encrypt1 = "encrypt" nocase wide ascii
                    $encrypt2 = "AES" wide ascii
                    $encrypt3 = "RSA" wide ascii
                    $ransom1 = "ransom" nocase wide ascii
                    $ransom2 = "bitcoin" nocase wide ascii
                    $ransom3 = "payment" nocase wide ascii
                    
                condition:
                    2 of ($encrypt*) and 1 of ($ransom*)
            }
        """
        
        # Compile YARA rules
        try:
            self.yara_compiler = yara.compile(source=self.yara_rules)
        except Exception as e:
            self.logger.error(f"Failed to compile YARA rules: {e}")
            self.yara_compiler = None
            
    def _init_quarantine_metadata(self):
        """Initialize quarantine metadata storage"""
        try:
            if not self.quarantine_meta_path.exists():
                self.quarantine_meta_path.write_text("{}")
            self._load_quarantine_metadata()
        except Exception as e:
            self.logger.critical(f"Failed to initialize quarantine metadata: {e}")
            raise

    def _load_quarantine_metadata(self) -> Dict:
        """Load quarantine metadata from disk"""
        try:
            return json.loads(self.quarantine_meta_path.read_text())
        except Exception as e:
            self.logger.error(f"Error loading quarantine metadata: {e}")
            return {}

    def _save_quarantine_metadata(self, metadata: Dict):
        """Save quarantine metadata to disk"""
        try:
            self.quarantine_meta_path.write_text(json.dumps(metadata, indent=2))
        except Exception as e:
            self.logger.error(f"Error saving quarantine metadata: {e}")
            raise

    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate SHA-256 hash of a file"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                while chunk := f.read(8192):  # Read in 8kb chunks
                    self.stats.bytes_scanned += len(chunk)
                    file_hash.update(chunk)
            return file_hash.hexdigest()
        except (IOError, OSError) as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            self.stats.files_error += 1
            return None

    def check_process_behavior(self, pid: int) -> Tuple[bool, str]:
        """Monitor process behavior for suspicious activities"""
        try:
            if os.name == 'nt':  # Windows
                cmd = f"tasklist /FI \"PID eq {pid}\" /FO CSV /V"
            else:  # Unix-like
                cmd = f"ps -p {pid} -o %cpu,%mem,cmd"
                
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            # Basic behavior analysis (to be expanded)
            if process.returncode == 0:
                # Add behavior analysis logic here
                return False, "Process behavior normal"
            return False, "Process not found"
        except Exception as e:
            self.logger.error(f"Error checking process behavior: {e}")
            return False, str(e)

    def quarantine_file(self, file_path: Path, threats: List[Dict]) -> bool:
        """Enhanced quarantine function with encryption and metadata tracking"""
        try:
            # Generate unique quarantine filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_hash = self.calculate_file_hash(file_path)
            quarantine_name = f"{timestamp}_{file_hash[:8]}_{file_path.name}"
            quarantine_file = self.quarantine_path / quarantine_name

            # Read original file content
            with open(file_path, 'rb') as f:
                content = f.read()

            # Encrypt the content
            encrypted_content = self.fernet.encrypt(content)

            # Save encrypted content
            with open(quarantine_file, 'wb') as f:
                f.write(encrypted_content)

            # Create metadata
            metadata = self._load_quarantine_metadata()
            metadata[quarantine_name] = {
                'original_path': str(file_path),
                'timestamp': timestamp,
                'file_hash': file_hash,
                'threat_info': threats,
                'original_permissions': file_path.stat().st_mode,
                'encryption_key': base64.b64encode(self.quarantine_key).decode()
            }
            self._save_quarantine_metadata(metadata)

            # Securely delete original file
            self._secure_delete(file_path)

            self.logger.info(f"File quarantined successfully: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Quarantine failed for {file_path}: {e}")
            return False

    def restore_file(self, quarantine_name: str) -> bool:
        """Restore a quarantined file to its original location"""
        try:
            # Load metadata
            metadata = self._load_quarantine_metadata()
            if quarantine_name not in metadata:
                raise ValueError(f"No metadata found for {quarantine_name}")

            file_meta = metadata[quarantine_name]
            quarantine_file = self.quarantine_path / quarantine_name
            original_path = Path(file_meta['original_path'])

            # Read and decrypt file content
            with open(quarantine_file, 'rb') as f:
                encrypted_content = f.read()
            
            decryption_key = base64.b64decode(file_meta['encryption_key'])
            fernet = Fernet(decryption_key)
            decrypted_content = fernet.decrypt(encrypted_content)

            # Restore file to original location
            original_path.parent.mkdir(parents=True, exist_ok=True)
            with open(original_path, 'wb') as f:
                f.write(decrypted_content)

            # Restore original permissions
            os.chmod(original_path, file_meta['original_permissions'])

            # Remove from quarantine
            quarantine_file.unlink()
            metadata.pop(quarantine_name)
            self._save_quarantine_metadata(metadata)

            self.logger.info(f"File restored successfully: {original_path}")
            return True

        except Exception as e:
            self.logger.error(f"Restore failed for {quarantine_name}: {e}")
            return False

    def _secure_delete(self, file_path: Path):
        """Securely delete a file by overwriting with random data"""
        try:
            # Get file size
            file_size = file_path.stat().st_size

            # Overwrite file content with random data
            with open(file_path, 'wb') as f:
                # Overwrite 3 times
                for _ in range(3):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())

            # Finally delete the file
            file_path.unlink()

        except Exception as e:
            self.logger.error(f"Secure delete failed for {file_path}: {e}")
            raise

    def get_quarantine_list(self) -> List[Dict]:
        """Get list of all quarantined files with their metadata"""
        try:
            metadata = self._load_quarantine_metadata()
            return [
                {
                    'name': name,
                    'original_path': meta['original_path'],
                    'timestamp': meta['timestamp'],
                    'threats': meta['threat_info']
                }
                for name, meta in metadata.items()
            ]
        except Exception as e:
            self.logger.error(f"Error getting quarantine list: {e}")
            return []

    def analyze_file_content(self, file_path: Path) -> List[Dict[str, any]]:
        """Analyze file content for suspicious patterns"""
        threats = []
        try:
            # Skip very large files or binary files
            if file_path.stat().st_size > 10_000_000:  # 10MB limit
                return threats
                
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                
            # Apply heuristic rules
            for rule in self.heuristic_rules:
                if re.search(rule.pattern, content, re.IGNORECASE):
                    threats.append({
                        'type': 'heuristic',
                        'rule_name': rule.name,
                        'severity': rule.severity,
                        'description': rule.description
                    })
                    
        except Exception as e:
            self.logger.warning(f"Could not analyze content of {file_path}: {e}")
            
        return threats

    def analyze_process_behavior(self, pid: int) -> List[Dict[str, any]]:
        """Detailed process behavior analysis"""
        threats = []
        try:
            process = psutil.Process(pid)
            
            # Check CPU usage
            if process.cpu_percent(interval=1.0) > 80:
                threats.append({
                    'type': 'behavior',
                    'name': 'high_cpu_usage',
                    'severity': 6,
                    'description': 'Process consuming excessive CPU'
                })
                
            # Check network connections
            connections = process.connections()
            if len(connections) > 50:  # Arbitrary threshold
                threats.append({
                    'type': 'behavior',
                    'name': 'excessive_connections',
                    'severity': 7,
                    'description': 'Process creating too many network connections'
                })
                
            # Check file operations
            open_files = process.open_files()
            suspicious_paths = [f for f in open_files if 
                             any(p in str(f.path).lower() for p in 
                                 ['system32', 'windows', 'boot'])]
            if suspicious_paths:
                threats.append({
                    'type': 'behavior',
                    'name': 'suspicious_file_access',
                    'severity': 8,
                    'description': 'Process accessing system files'
                })
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Error analyzing process {pid}: {e}")
            
        return threats

    def scan_file(self, file_path: Path) -> Dict[str, any]:
        """Scan a single file for threats"""
        try:
            if not file_path.exists() or not file_path.is_file():
                return {
                    'file_path': str(file_path),
                    'status': 'error',
                    'error': 'File not found or not accessible'
                }
                
            threats = []
            
            # 1. Check file size
            if file_path.stat().st_size > 100 * 1024 * 1024:  # Skip files > 100MB
                return {
                    'file_path': str(file_path),
                    'status': 'skipped',
                    'reason': 'File too large'
                }
                
            # 2. Check file extension
            if file_path.suffix.lower() in self.virus_signatures['suspicious_extensions']:
                threats.append({
                    'type': 'suspicious_extension',
                    'details': f'Suspicious file extension: {file_path.suffix}',
                    'severity': 3
                })
                
            # 3. Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            if file_hash in self.virus_signatures['hashes']:
                threats.append({
                    'type': 'known_malware',
                    'details': 'File matches known malware signature',
                    'severity': 10
                })
                
            # 4. Check file content
            try:
                # Get file type if magic is available
                file_type = "unknown"
                if HAS_MAGIC:
                    file_type = magic.from_file(str(file_path))
                else:
                    # Basic file type detection based on extension
                    file_type = file_path.suffix.lower()[1:] if file_path.suffix else "unknown"
                
                # Read file content for analysis
                with open(file_path, 'rb') as f:
                    content = f.read()
                    
                    # Check for suspicious patterns
                    for pattern in self.virus_signatures['patterns']:
                        if re.search(pattern, content):
                            threats.append({
                                'type': 'suspicious_pattern',
                                'details': 'File contains suspicious code patterns',
                                'severity': 7
                            })
                            break
                    
                    # Apply YARA rules if available
                    if self.yara_compiler:
                        matches = self.yara_compiler.match(data=content)
                        for match in matches:
                            threats.append({
                                'type': 'yara_match',
                                'details': f'Matched YARA rule: {match.rule}',
                                'severity': 8
                            })
                            
            except Exception as e:
                self.logger.warning(f"Error analyzing file content: {e}")
                
            # Return scan results
            return {
                'file_path': str(file_path),
                'status': 'infected' if threats else 'clean',
                'threats': threats,
                'hash': file_hash,
                'file_type': file_type
            }
            
        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")
            return {
                'file_path': str(file_path),
                'status': 'error',
                'error': str(e)
            }
            
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def scan_directory(self, directory: Path) -> List[Dict[str, any]]:
        """Enhanced scan_directory with memory optimization"""
        try:
            self.system_monitor.set_scanning_state(True)
            self.optimizer.reset_stats()
            self.stats = ScanStats(start_time=time.time())
            
            # Collect files in batches to reduce memory usage
            results = []
            for batch in self._get_file_batches(directory):
                # Process batch
                batch_results = await self._scan_batch(batch)
                results.extend(batch_results)
                
                # Update progress
                self.system_monitor.update_scan_progress(self.stats.files_scanned)
                
                # Force garbage collection between batches
                gc.collect()
                
                # Add small delay to prevent resource exhaustion
                await asyncio.sleep(0.01)
                
            return results
            
        finally:
            self.system_monitor.set_scanning_state(False)
            
    def _get_file_batches(self, directory: Path) -> Iterator[List[Path]]:
        """Get files in batches to reduce memory usage"""
        batch = []
        for file_path in directory.rglob('*'):
            if file_path.is_file() and self.optimizer.should_scan_file(file_path):
                batch.append(file_path)
                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []
        if batch:
            yield batch

    def update_signatures(self, new_signatures: Dict[str, str]):
        """Update the signature database"""
        try:
            self.signature_database.update(new_signatures)
            self.logger.info(f"Updated signature database with {len(new_signatures)} new signatures")
        except Exception as e:
            self.logger.error(f"Error updating signatures: {e}")
            raise 

    def _handle_throttling(self):
        """Handle resource throttling"""
        try:
            # Reduce thread count
            new_threads = max(1, self.max_threads // 2)
            if new_threads != self.max_threads:
                self.logger.info(f"Throttling: Reducing threads from {self.max_threads} to {new_threads}")
                self.max_threads = new_threads
                self.executor._max_workers = new_threads
                
            # Increase scan batch delay
            time.sleep(0.1)  # Add small delay between batches
            
        except Exception as e:
            self.logger.error(f"Error handling throttling: {e}")
            
    def get_performance_stats(self) -> Dict:
        """Get performance statistics including latency"""
        stats = self.optimizer.get_performance_stats()
        latency_stats = self.latency_monitor.get_statistics()
        
        return {
            **stats,
            'latency': {
                'average_ms': latency_stats['average'],
                'median_ms': latency_stats['median'],
                'max_ms': latency_stats['max'],
                'violations': latency_stats['violations'],
                'violation_rate': (
                    latency_stats['violations'] / latency_stats['total_operations']
                    if latency_stats['total_operations'] > 0 else 0
                )
            }
        }
        
    def _handle_cpu_throttle(self, reduction: float):
        """Handle CPU throttling"""
        # Reduce thread count
        new_threads = max(1, int(self.max_threads * (1 - reduction)))
        if new_threads != self.max_threads:
            self.logger.info(f"CPU throttle: Reducing threads from {self.max_threads} to {new_threads}")
            self.max_threads = new_threads
            self.executor._max_workers = new_threads
            
    def _handle_memory_throttle(self, reduction: float):
        """Handle memory throttling"""
        # Reduce batch size
        self.optimizer.batch_size = max(
            self.optimizer.min_batch_size,
            int(self.optimizer.batch_size * (1 - reduction))
        )
        self.logger.info(f"Memory throttle: Reduced batch size to {self.optimizer.batch_size}")
        
    def _handle_disk_throttle(self, reduction: float):
        """Handle disk I/O throttling"""
        # Add delay between file operations
        delay = min(1.0, reduction)  # Maximum 1 second delay
        self.logger.info(f"Disk throttle: Adding {delay:.2f}s delay between operations")
        time.sleep(delay)
        
    def get_optimization_suggestions(self) -> Dict:
        """Get performance optimization suggestions"""
        return self.performance_analyzer.analyze_performance()
        
    def _handle_health_alert(self, status):
        """Handle system health alerts"""
        if status.status == 'critical':
            self.logger.critical(f"Critical system health issues: {', '.join(status.issues)}")
            # Pause non-essential operations
            self._pause_background_operations()
        elif status.status == 'warning':
            self.logger.warning(f"System health warnings: {', '.join(status.issues)}")
            # Reduce resource usage
            self._reduce_resource_usage()
            
    def _pause_background_operations(self):
        """Pause non-essential background operations"""
        # Implement pausing logic here
        pass
        
    def _reduce_resource_usage(self):
        """Reduce resource usage when system health is warning"""
        # Implement resource reduction logic here
        pass
        
    async def _scan_batch(self, batch: List[Path]) -> List[Dict]:
        """Process a batch of files with optimized scanning"""
        results = []
        
        # Use thread pool for parallel scanning
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Submit scan tasks
            future_to_file = {
                executor.submit(self.scan_file, file_path): file_path 
                for file_path in batch
            }
            
            # Process completed scans
            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update scan stats
                    self.stats.files_scanned += 1
                    if result.get('threats'):
                        self.stats.files_infected += 1
                    if result.get('error'):
                        self.stats.files_error += 1
                        
                except Exception as e:
                    file_path = future_to_file[future]
                    self.logger.error(f"Error scanning {file_path}: {e}")
                    results.append({
                        'file_path': str(file_path),
                        'status': 'error',
                        'error': str(e)
                    })
                    self.stats.files_error += 1
                    
        return results
        
    def _cleanup_scan_data(self):
        """Clean up temporary scan data"""
        try:
            # Clear temporary data
            self._temp_data.clear()
            
            # Clear signature cache
            if hasattr(self, 'signature_cache'):
                self.signature_cache.clear()
            
            # Reset batch processing
            if hasattr(self, 'current_batch'):
                self.current_batch = []
            
            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            self.logger.error(f"Error cleaning scan data: {e}")
        