import requests
import json
import hashlib
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
import schedule
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal

class UpdateProgress:
    """Container for update progress information"""
    def __init__(self):
        self.total_signatures = 0
        self.processed_signatures = 0
        self.download_size = 0
        self.downloaded_bytes = 0
        self.current_operation = ""
        self.status = "idle"
        
    @property
    def progress_percentage(self) -> float:
        if self.total_signatures > 0:
            return (self.processed_signatures / self.total_signatures) * 100
        if self.download_size > 0:
            return (self.downloaded_bytes / self.download_size) * 100
        return 0

class SignatureUpdater(QObject):
    """Handles malware signature database updates"""
    
    # Add signals for progress updates
    update_progress = pyqtSignal(dict)
    update_complete = pyqtSignal(bool, str)
    
    def __init__(self, base_path: Path):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.base_path = base_path
        self.signatures_path = base_path / "signatures"
        self.signatures_path.mkdir(exist_ok=True)
        
        # Update configuration
        self.update_url = "https://your-update-server.com/signatures"  # Replace with actual URL
        self.update_interval = timedelta(hours=24)  # Daily updates
        self.last_update = None
        self.current_version = self._get_current_version()
        
        # Initialize signature verification
        self._init_verification()
        
        # Update scheduling
        self.update_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.last_scheduled_update = None
        self.update_schedule = {
            'daily': True,      # Enable daily updates
            'time': "03:00",    # Default update time (3 AM)
            'retry_interval': timedelta(hours=1),  # Retry failed updates every hour
            'force_update_after': timedelta(days=3)  # Force update if none for 3 days
        }
        
        self.progress = UpdateProgress()
        
    def _init_verification(self):
        """Initialize signature verification keys"""
        # In production, this would be your actual public key
        self.public_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        ).public_key()
        
    def _get_current_version(self) -> str:
        """Get current signature database version"""
        version_file = self.signatures_path / "version.json"
        if version_file.exists():
            try:
                data = json.loads(version_file.read_text())
                return data.get('version', '0')
            except Exception as e:
                self.logger.error(f"Error reading version file: {e}")
        return '0'
        
    async def check_for_updates(self) -> Tuple[bool, Optional[Dict]]:
        """Check if updates are available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.update_url}/version") as response:
                    if response.status != 200:
                        return False, None
                    
                    data = await response.json()
                    if data['version'] > self.current_version:
                        return True, data
                    return False, None
                    
        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            return False, None
            
    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify the signature of downloaded data"""
        try:
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            self.logger.error(f"Error verifying signature: {e}")
            return False
            
    async def download_update(self, version: str) -> Optional[Dict]:
        """Download signature database update"""
        try:
            async with aiohttp.ClientSession() as session:
                # Download signatures
                async with session.get(f"{self.update_url}/db/{version}") as response:
                    if response.status != 200:
                        return None
                    data = await response.read()
                    
                # Download signature
                async with session.get(f"{self.update_url}/db/{version}.sig") as sig_response:
                    if sig_response.status != 200:
                        return None
                    signature = await sig_response.read()
                    
            # Verify signature
            if not self.verify_signature(data, signature):
                self.logger.error("Invalid signature for update package")
                return None
                
            # Parse and return signatures
            return json.loads(data)
            
        except Exception as e:
            self.logger.error(f"Error downloading update: {e}")
            return None
            
    def apply_update(self, signatures: Dict) -> bool:
        """Apply downloaded signature updates"""
        try:
            # Backup current signatures
            backup_path = self.signatures_path / f"backup_{self.current_version}.json"
            current_path = self.signatures_path / "signatures.json"
            
            if current_path.exists():
                current_path.rename(backup_path)
                
            # Write new signatures
            current_path.write_text(json.dumps(signatures, indent=2))
            
            # Update version
            version_data = {
                'version': signatures['version'],
                'updated_at': datetime.now().isoformat()
            }
            (self.signatures_path / "version.json").write_text(
                json.dumps(version_data, indent=2)
            )
            
            self.current_version = signatures['version']
            self.last_update = datetime.now()
            
            self.logger.info(f"Successfully updated signatures to version {signatures['version']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying update: {e}")
            # Attempt rollback
            if backup_path.exists() and not current_path.exists():
                backup_path.rename(current_path)
            return False
            
    async def _download_with_progress(self, url: str) -> Optional[bytes]:
        """Download with progress tracking"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                        
                    self.progress.download_size = int(response.headers.get('content-length', 0))
                    self.progress.downloaded_bytes = 0
                    self.progress.current_operation = "Downloading updates..."
                    
                    chunks = []
                    async for chunk in response.content.iter_chunked(8192):
                        chunks.append(chunk)
                        self.progress.downloaded_bytes += len(chunk)
                        self._emit_progress()
                        
                    return b''.join(chunks)
                    
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None
            
    def _emit_progress(self):
        """Emit progress update signal"""
        self.update_progress.emit({
            'percentage': self.progress.progress_percentage,
            'operation': self.progress.current_operation,
            'status': self.progress.status,
            'processed': self.progress.processed_signatures,
            'total': self.progress.total_signatures,
            'downloaded': self.progress.downloaded_bytes,
            'download_size': self.progress.download_size
        })
        
    async def update_signatures(self) -> bool:
        """Enhanced update process with progress tracking"""
        try:
            self.progress.status = "checking"
            self.progress.current_operation = "Checking for updates..."
            self._emit_progress()
            
            # Check for updates
            update_available, version_info = await self.check_for_updates()
            if not update_available:
                self.update_complete.emit(True, "Signature database is up to date")
                return True
                
            # Download updates
            self.progress.status = "downloading"
            self.progress.current_operation = "Downloading signature updates..."
            self._emit_progress()
            
            signatures = await self.download_update(version_info['version'])
            if not signatures:
                self.update_complete.emit(False, "Failed to download updates")
                return False
                
            # Process and apply updates
            self.progress.status = "processing"
            self.progress.current_operation = "Processing signature updates..."
            self.progress.total_signatures = len(signatures)
            self.progress.processed_signatures = 0
            self._emit_progress()
            
            # Apply updates in batches to maintain responsiveness
            batch_size = 1000
            for i in range(0, len(signatures), batch_size):
                batch = dict(list(signatures.items())[i:i + batch_size])
                if not self.apply_update(batch):
                    self.update_complete.emit(False, "Failed to apply updates")
                    return False
                    
                self.progress.processed_signatures += len(batch)
                self._emit_progress()
                
                # Small delay to prevent UI freezing
                await asyncio.sleep(0.1)
                
            self.progress.status = "completed"
            self.progress.current_operation = "Update completed successfully"
            self._emit_progress()
            
            self.update_complete.emit(True, "Signature database updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            self.update_complete.emit(False, f"Update failed: {str(e)}")
            return False
            
        finally:
            self.progress.status = "idle"
            self.progress.current_operation = ""
            self._emit_progress()
            
    def get_update_status(self) -> Dict:
        """Get current update status"""
        return {
            'current_version': self.current_version,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'signatures_count': len(self._load_signatures()),
            'next_update': (self.last_update + self.update_interval).isoformat() 
                          if self.last_update else None
        }
        
    def _load_signatures(self) -> Dict:
        """Load current signatures from disk"""
        try:
            current_path = self.signatures_path / "signatures.json"
            if current_path.exists():
                return json.loads(current_path.read_text())
            return {}
        except Exception as e:
            self.logger.error(f"Error loading signatures: {e}")
            return {} 
        
    def start_scheduler(self):
        """Start the update scheduler thread"""
        if not self.is_running:
            self.is_running = True
            self.update_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.update_thread.start()
            self.logger.info("Update scheduler started")
            
    def stop_scheduler(self):
        """Stop the update scheduler"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join()
            self.logger.info("Update scheduler stopped")
            
    def _run_scheduler(self):
        """Main scheduler loop"""
        schedule.every().day.at(self.update_schedule['time']).do(
            lambda: asyncio.run(self._scheduled_update())
        )
        
        while self.is_running:
            schedule.run_pending()
            
            # Check if force update is needed
            if self.last_update:
                time_since_update = datetime.now() - self.last_update
                if time_since_update > self.update_schedule['force_update_after']:
                    self.logger.warning("Force update triggered - too long since last update")
                    asyncio.run(self.update_signatures())
                    
            time.sleep(60)  # Check every minute
            
    async def _scheduled_update(self):
        """Handle scheduled update execution"""
        self.logger.info("Starting scheduled signature update")
        try:
            success = await self.update_signatures()
            if success:
                self.last_scheduled_update = datetime.now()
                self.logger.info("Scheduled update completed successfully")
            else:
                self.logger.error("Scheduled update failed")
                # Schedule retry
                next_retry = datetime.now() + self.update_schedule['retry_interval']
                schedule.every().day.at(next_retry.strftime("%H:%M")).do(
                    self._scheduled_update
                ).tag('retry')
                
        except Exception as e:
            self.logger.error(f"Error during scheduled update: {e}")
            
    def configure_updates(self, schedule_config: Dict):
        """Configure update schedule"""
        try:
            # Validate time format
            datetime.strptime(schedule_config.get('time', "03:00"), "%H:%M")
            
            self.update_schedule.update(schedule_config)
            
            # Clear existing schedule
            schedule.clear()
            
            # Set new schedule
            if self.update_schedule['daily']:
                schedule.every().day.at(self.update_schedule['time']).do(
                    self._scheduled_update
                )
                
            self.logger.info(f"Update schedule configured: {self.update_schedule}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring update schedule: {e}")
            return False
            
    def get_schedule_info(self) -> Dict:
        """Get current update schedule information"""
        return {
            'schedule': self.update_schedule,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'last_scheduled': self.last_scheduled_update.isoformat() 
                            if self.last_scheduled_update else None,
            'next_update': schedule.next_run().isoformat() 
                          if schedule.next_run() else None
        }