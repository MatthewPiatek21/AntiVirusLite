import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from dataclasses import dataclass, asdict

@dataclass
class QuarantineEntry:
    """Container for quarantine entry information"""
    original_path: str
    timestamp: str
    file_hash: str
    threat_info: List[Dict]
    size: int
    quarantine_path: str
    is_encrypted: bool = True

class QuarantineManager:
    """Manages quarantined files and their metadata"""
    
    def __init__(self, base_path: Path):
        self.logger = logging.getLogger(__name__)
        self.base_path = base_path
        self.quarantine_dir = base_path / "quarantine"
        self.metadata_file = self.quarantine_dir / "metadata.json"
        
        # Initialize encryption
        self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Create quarantine directory structure
        self._init_quarantine_storage()
        
    def _init_quarantine_storage(self):
        """Initialize quarantine storage structure"""
        try:
            # Create quarantine directory if it doesn't exist
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize metadata file
            if not self.metadata_file.exists():
                self.metadata_file.write_text("{}")
                
        except Exception as e:
            self.logger.critical(f"Failed to initialize quarantine storage: {e}")
            raise
            
    def quarantine_file(self, file_path: Path, threat_info: List[Dict]) -> bool:
        """Quarantine an infected file"""
        try:
            # Generate quarantine file name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            quarantine_name = f"{timestamp}_{file_path.name}"
            quarantine_path = self.quarantine_dir / quarantine_name
            
            # Read and encrypt file content
            with open(file_path, 'rb') as f:
                content = f.read()
                encrypted_content = self.fernet.encrypt(content)
                
            # Save encrypted file
            with open(quarantine_path, 'wb') as f:
                f.write(encrypted_content)
                
            # Create quarantine entry
            entry = QuarantineEntry(
                original_path=str(file_path),
                timestamp=timestamp,
                file_hash=self._calculate_hash(file_path),
                threat_info=threat_info,
                size=file_path.stat().st_size,
                quarantine_path=str(quarantine_path)
            )
            
            # Update metadata
            self._add_quarantine_entry(quarantine_name, entry)
            
            # Securely delete original file
            self._secure_delete(file_path)
            
            self.logger.info(f"Successfully quarantined file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to quarantine file {file_path}: {e}")
            return False
            
    def restore_file(self, quarantine_name: str, force: bool = False) -> bool:
        """Restore a quarantined file to its original location"""
        try:
            # Get metadata
            metadata = self._load_metadata()
            if quarantine_name not in metadata:
                raise ValueError(f"No metadata found for {quarantine_name}")
                
            entry = QuarantineEntry(**metadata[quarantine_name])
            quarantine_path = Path(entry.quarantine_path)
            original_path = Path(entry.original_path)
            
            if not force and entry.threat_info:
                self.logger.warning(
                    f"Attempting to restore known infected file: {original_path}"
                )
                
            # Read and decrypt file content
            with open(quarantine_path, 'rb') as f:
                encrypted_content = f.read()
                decrypted_content = self.fernet.decrypt(encrypted_content)
                
            # Restore file to original location
            original_path.parent.mkdir(parents=True, exist_ok=True)
            with open(original_path, 'wb') as f:
                f.write(decrypted_content)
                
            # Remove from quarantine
            quarantine_path.unlink()
            self._remove_quarantine_entry(quarantine_name)
            
            self.logger.info(f"Successfully restored file: {original_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore file {quarantine_name}: {e}")
            return False
            
    def delete_quarantined_file(self, quarantine_name: str) -> bool:
        """Permanently delete a quarantined file"""
        try:
            metadata = self._load_metadata()
            if quarantine_name not in metadata:
                raise ValueError(f"No metadata found for {quarantine_name}")
                
            entry = QuarantineEntry(**metadata[quarantine_name])
            quarantine_path = Path(entry.quarantine_path)
            
            # Securely delete quarantined file
            self._secure_delete(quarantine_path)
            self._remove_quarantine_entry(quarantine_name)
            
            self.logger.info(f"Successfully deleted quarantined file: {quarantine_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete quarantined file {quarantine_name}: {e}")
            return False
            
    def get_quarantine_list(self) -> List[Dict]:
        """Get list of all quarantined files"""
        try:
            metadata = self._load_metadata()
            return [
                {
                    'name': name,
                    **asdict(QuarantineEntry(**entry))
                }
                for name, entry in metadata.items()
            ]
        except Exception as e:
            self.logger.error(f"Failed to get quarantine list: {e}")
            return []
            
    def _add_quarantine_entry(self, name: str, entry: QuarantineEntry):
        """Add a new quarantine entry to metadata"""
        metadata = self._load_metadata()
        metadata[name] = asdict(entry)
        self._save_metadata(metadata)
        
    def _remove_quarantine_entry(self, name: str):
        """Remove a quarantine entry from metadata"""
        metadata = self._load_metadata()
        metadata.pop(name, None)
        self._save_metadata(metadata)
        
    def _load_metadata(self) -> Dict:
        """Load quarantine metadata from disk"""
        try:
            return json.loads(self.metadata_file.read_text())
        except Exception as e:
            self.logger.error(f"Failed to load quarantine metadata: {e}")
            return {}
            
    def _save_metadata(self, metadata: Dict):
        """Save quarantine metadata to disk"""
        try:
            self.metadata_file.write_text(json.dumps(metadata, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save quarantine metadata: {e}")
            raise
            
    def _secure_delete(self, file_path: Path):
        """Securely delete a file by overwriting with random data"""
        try:
            if not file_path.exists():
                return
                
            # Get file size
            file_size = file_path.stat().st_size
            
            # Overwrite file content multiple times
            for _ in range(3):
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
                    
            # Finally delete the file
            file_path.unlink()
            
        except Exception as e:
            self.logger.error(f"Failed to securely delete file {file_path}: {e}")
            raise
            
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest() 