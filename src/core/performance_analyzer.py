import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np
from .performance_monitor import PerformanceMonitor

@dataclass
class PerformancePattern:
    """Container for identified performance patterns"""
    metric: str
    pattern_type: str  # 'spike', 'trend', 'periodic'
    severity: int  # 1-10
    description: str
    recommendation: str
    impact: float  # Estimated performance impact

class PerformanceAnalyzer:
    """Analyzes performance patterns and provides optimization suggestions"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = performance_monitor
        self.analysis_dir = Path("data/analysis")
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance thresholds
        self.thresholds = {
            'cpu_high': 70.0,
            'memory_high': 512,  # MB
            'io_high': 50.0,  # MB/s
            'scan_speed_low': 800,  # files/sec
            'latency_high': 80.0  # ms
        }
        
    def analyze_performance(self, duration: timedelta = timedelta(days=7)) -> Dict:
        """Analyze performance metrics and generate recommendations"""
        try:
            # Get historical metrics
            metrics = self.performance_monitor.get_metrics_history(duration)
            
            # Identify patterns
            patterns = self._identify_patterns(metrics)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(patterns)
            
            # Calculate optimization potential
            optimization_score = self._calculate_optimization_score(patterns)
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'period': {
                    'start': (datetime.now() - duration).isoformat(),
                    'end': datetime.now().isoformat()
                },
                'patterns': [self._pattern_to_dict(p) for p in patterns],
                'recommendations': recommendations,
                'optimization_score': optimization_score,
                'metrics_summary': self._generate_metrics_summary(metrics)
            }
            
            # Save analysis
            self._save_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return {}
            
    def _identify_patterns(self, metrics: List[Dict]) -> List[PerformancePattern]:
        """Identify performance patterns in metrics"""
        patterns = []
        
        # Extract metric series
        cpu_usage = [m['cpu_usage'] for m in metrics]
        memory_usage = [m['memory_usage'] for m in metrics]
        scan_speed = [m.get('scan_speed', 0) for m in metrics]
        
        # Check for CPU spikes
        if any(cpu > self.thresholds['cpu_high'] for cpu in cpu_usage):
            patterns.append(PerformancePattern(
                metric='cpu',
                pattern_type='spike',
                severity=8,
                description="Frequent CPU usage spikes detected",
                recommendation="Consider reducing scan thread count or adjusting scan frequency",
                impact=0.3
            ))
            
        # Check for memory trends
        memory_trend = self._calculate_trend(memory_usage)
        if memory_trend > 0.1:  # 10% increase trend
            patterns.append(PerformancePattern(
                metric='memory',
                pattern_type='trend',
                severity=7,
                description="Increasing memory usage trend detected",
                recommendation="Review cache settings and batch processing size",
                impact=0.25
            ))
            
        # Check for scan speed consistency
        speed_variance = np.var(scan_speed) if scan_speed else 0
        if speed_variance > 10000:  # High variance in scan speed
            patterns.append(PerformancePattern(
                metric='scan_speed',
                pattern_type='periodic',
                severity=6,
                description="Inconsistent scan performance detected",
                recommendation="Optimize file filtering and signature matching algorithms",
                impact=0.2
            ))
            
        return patterns
        
    def _generate_recommendations(self, patterns: List[PerformancePattern]) -> List[Dict]:
        """Generate optimization recommendations based on patterns"""
        recommendations = []
        
        # Group patterns by metric
        metric_patterns = {}
        for pattern in patterns:
            if pattern.metric not in metric_patterns:
                metric_patterns[pattern.metric] = []
            metric_patterns[pattern.metric].append(pattern)
            
        # Generate recommendations for each metric
        if 'cpu' in metric_patterns:
            recommendations.append({
                'category': 'CPU Optimization',
                'priority': self._calculate_priority(metric_patterns['cpu']),
                'suggestions': [
                    "Reduce maximum thread count",
                    "Implement smarter process prioritization",
                    "Optimize signature matching algorithms"
                ],
                'estimated_impact': 'High'
            })
            
        if 'memory' in metric_patterns:
            recommendations.append({
                'category': 'Memory Management',
                'priority': self._calculate_priority(metric_patterns['memory']),
                'suggestions': [
                    "Adjust cache size limits",
                    "Implement memory-efficient data structures",
                    "Review memory leak potential"
                ],
                'estimated_impact': 'Medium'
            })
            
        if 'scan_speed' in metric_patterns:
            recommendations.append({
                'category': 'Scan Performance',
                'priority': self._calculate_priority(metric_patterns['scan_speed']),
                'suggestions': [
                    "Optimize file filtering rules",
                    "Implement predictive file loading",
                    "Review signature database indexing"
                ],
                'estimated_impact': 'High'
            })
            
        return recommendations
        
    def _calculate_optimization_score(self, patterns: List[PerformancePattern]) -> float:
        """Calculate overall optimization potential score (0-100)"""
        if not patterns:
            return 100.0  # Perfect score if no issues
            
        # Calculate weighted impact
        total_impact = sum(p.impact * p.severity for p in patterns)
        max_possible_impact = len(patterns) * 10  # Maximum severity is 10
        
        # Convert to 0-100 scale
        score = 100 * (1 - total_impact / max_possible_impact)
        return max(0.0, min(100.0, score))
        
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend coefficient for a series of values"""
        if not values:
            return 0.0
            
        x = np.arange(len(values))
        y = np.array(values)
        
        # Calculate linear regression
        try:
            slope = np.polyfit(x, y, 1)[0]
            return slope / np.mean(values)  # Normalize by mean
        except:
            return 0.0
            
    def _calculate_priority(self, patterns: List[PerformancePattern]) -> str:
        """Calculate priority based on pattern severity"""
        max_severity = max(p.severity for p in patterns)
        if max_severity >= 8:
            return 'High'
        elif max_severity >= 5:
            return 'Medium'
        return 'Low'
        
    def _generate_metrics_summary(self, metrics: List[Dict]) -> Dict:
        """Generate summary statistics for metrics"""
        if not metrics:
            return {}
            
        return {
            'cpu': {
                'average': np.mean([m['cpu_usage'] for m in metrics]),
                'max': max(m['cpu_usage'] for m in metrics),
                'min': min(m['cpu_usage'] for m in metrics)
            },
            'memory': {
                'average': np.mean([m['memory_usage'] for m in metrics]),
                'max': max(m['memory_usage'] for m in metrics),
                'min': min(m['memory_usage'] for m in metrics)
            },
            'scan_speed': {
                'average': np.mean([m.get('scan_speed', 0) for m in metrics]),
                'max': max(m.get('scan_speed', 0) for m in metrics),
                'min': min(m.get('scan_speed', 0) for m in metrics)
            }
        }
        
    def _pattern_to_dict(self, pattern: PerformancePattern) -> Dict:
        """Convert pattern to dictionary for serialization"""
        return {
            'metric': pattern.metric,
            'pattern_type': pattern.pattern_type,
            'severity': pattern.severity,
            'description': pattern.description,
            'recommendation': pattern.recommendation,
            'impact': pattern.impact
        }
        
    def _save_analysis(self, analysis: Dict):
        """Save analysis results to disk"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = self.analysis_dir / f"analysis_{timestamp}.json"
            file_path.write_text(json.dumps(analysis, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save analysis: {e}") 