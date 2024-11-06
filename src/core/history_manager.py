import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class ThreatEvent:
    """Container for threat detection events"""
    timestamp: str
    file_path: str
    threat_type: str
    severity: int
    action_taken: str
    quarantine_id: Optional[str]
    scan_type: str  # 'real-time', 'scheduled', 'manual'
    details: Dict

class HistoryManager:
    """Manages threat detection history"""
    
    def __init__(self, base_path: Path):
        self.logger = logging.getLogger(__name__)
        self.base_path = base_path
        self.history_dir = base_path / "history"
        self.current_log = self.history_dir / f"threat_log_{datetime.now().strftime('%Y%m')}.json"
        
        # Initialize storage
        self._init_storage()
        
    def _init_storage(self):
        """Initialize history storage"""
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            if not self.current_log.exists():
                self.current_log.write_text("[]")
        except Exception as e:
            self.logger.critical(f"Failed to initialize history storage: {e}")
            raise
            
    def add_event(self, event: ThreatEvent):
        """Add a new threat event to history"""
        try:
            events = self._load_current_log()
            events.append(asdict(event))
            self._save_current_log(events)
            self.logger.info(f"Added threat event: {event.threat_type} in {event.file_path}")
        except Exception as e:
            self.logger.error(f"Failed to add threat event: {e}")
            
    def get_events(self, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  threat_type: Optional[str] = None,
                  min_severity: Optional[int] = None) -> List[ThreatEvent]:
        """Get threat events with optional filtering"""
        try:
            all_events = []
            
            # Collect events from all log files
            for log_file in self.history_dir.glob("threat_log_*.json"):
                events = self._load_log(log_file)
                all_events.extend(events)
                
            # Apply filters
            filtered_events = []
            for event in all_events:
                event_time = datetime.fromisoformat(event['timestamp'])
                
                if start_date and event_time < start_date:
                    continue
                if end_date and event_time > end_date:
                    continue
                if threat_type and event['threat_type'] != threat_type:
                    continue
                if min_severity and event['severity'] < min_severity:
                    continue
                    
                filtered_events.append(ThreatEvent(**event))
                
            return filtered_events
            
        except Exception as e:
            self.logger.error(f"Failed to get threat events: {e}")
            return []
            
    def get_statistics(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Dict:
        """Get threat detection statistics"""
        events = self.get_events(start_date, end_date)
        
        stats = {
            'total_threats': len(events),
            'by_type': {},
            'by_severity': {i: 0 for i in range(1, 11)},
            'quarantined': sum(1 for e in events if e.quarantine_id),
            'scan_types': {
                'real-time': 0,
                'scheduled': 0,
                'manual': 0
            }
        }
        
        for event in events:
            # Count by type
            stats['by_type'][event.threat_type] = \
                stats['by_type'].get(event.threat_type, 0) + 1
            
            # Count by severity
            stats['by_severity'][event.severity] += 1
            
            # Count by scan type
            stats['scan_types'][event.scan_type] += 1
            
        return stats
        
    def _load_current_log(self) -> List[Dict]:
        """Load current month's threat log"""
        return self._load_log(self.current_log)
        
    def _load_log(self, log_file: Path) -> List[Dict]:
        """Load threat log from file"""
        try:
            return json.loads(log_file.read_text())
        except Exception as e:
            self.logger.error(f"Failed to load threat log {log_file}: {e}")
            return []
            
    def _save_current_log(self, events: List[Dict]):
        """Save events to current month's log"""
        try:
            self.current_log.write_text(json.dumps(events, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save threat log: {e}")
            raise 