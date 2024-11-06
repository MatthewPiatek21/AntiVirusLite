import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
from .performance_monitor import PerformanceMonitor

class PerformanceReporter:
    """Generates and manages performance reports"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = performance_monitor
        self.reports_dir = Path("data/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_weekly_report(self) -> Dict:
        """Generate a comprehensive weekly performance report"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            report = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': self._generate_summary(start_date, end_date),
                'daily_metrics': self._collect_daily_metrics(start_date, end_date),
                'resource_usage': self._analyze_resource_usage(start_date, end_date),
                'performance_issues': self._identify_issues(start_date, end_date),
                'recommendations': self._generate_recommendations(),
                'generated_at': datetime.now().isoformat()
            }
            
            # Save report
            report_file = self.reports_dir / f"weekly_report_{end_date.strftime('%Y%m%d')}.json"
            report_file.write_text(json.dumps(report, indent=2))
            
            # Generate visualizations
            self._generate_visualizations(report, report_file.stem)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate weekly report: {e}")
            return {}
            
    def _generate_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate performance summary statistics"""
        metrics = self.performance_monitor.get_average_metrics(end_date - start_date)
        
        return {
            'average_cpu_usage': metrics['cpu_usage'],
            'average_memory_usage': metrics['memory_usage'],
            'average_disk_io': {
                'read': metrics['disk_io_read'],
                'write': metrics['disk_io_write']
            },
            'total_files_processed': metrics['files_processed'],
            'scan_speed': metrics['scan_speed'],
            'resource_efficiency': self._calculate_efficiency(metrics)
        }
        
    def _collect_daily_metrics(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Collect daily performance metrics"""
        daily_metrics = []
        current_date = start_date
        
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            metrics = self.performance_monitor.get_average_metrics(
                timedelta(days=1), 
                start_time=current_date
            )
            
            daily_metrics.append({
                'date': current_date.isoformat(),
                'metrics': metrics
            })
            
            current_date = next_date
            
        return daily_metrics
        
    def _analyze_resource_usage(self, start_date: datetime, end_date: datetime) -> Dict:
        """Analyze resource usage patterns"""
        metrics = self.performance_monitor.get_average_metrics(end_date - start_date)
        
        return {
            'cpu_analysis': {
                'average_usage': metrics['cpu_usage'],
                'peak_usage': max(m['metrics']['cpu_usage'] 
                                for m in self._collect_daily_metrics(start_date, end_date)),
                'efficiency_score': self._calculate_cpu_efficiency(metrics)
            },
            'memory_analysis': {
                'average_usage': metrics['memory_usage'],
                'peak_usage': max(m['metrics']['memory_usage'] 
                                for m in self._collect_daily_metrics(start_date, end_date)),
                'efficiency_score': self._calculate_memory_efficiency(metrics)
            },
            'disk_analysis': {
                'average_io': (metrics['disk_io_read'] + metrics['disk_io_write']) / 2,
                'peak_io': max(m['metrics']['disk_io_read'] + m['metrics']['disk_io_write']
                              for m in self._collect_daily_metrics(start_date, end_date)),
                'efficiency_score': self._calculate_disk_efficiency(metrics)
            }
        }
        
    def _identify_issues(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Identify performance issues and bottlenecks"""
        issues = []
        metrics = self.performance_monitor.get_average_metrics(end_date - start_date)
        
        # Check CPU usage
        if metrics['cpu_usage'] > 30:
            issues.append({
                'type': 'cpu',
                'severity': 'high' if metrics['cpu_usage'] > 50 else 'medium',
                'description': f"High CPU usage: {metrics['cpu_usage']:.1f}%",
                'recommendation': "Consider reducing scan frequency or adjusting thread count"
            })
            
        # Check memory usage
        if metrics['memory_usage'] > 512:  # MB
            issues.append({
                'type': 'memory',
                'severity': 'high' if metrics['memory_usage'] > 768 else 'medium',
                'description': f"High memory usage: {metrics['memory_usage']:.1f}MB",
                'recommendation': "Adjust batch size or enable memory optimization"
            })
            
        # Check scan speed
        if metrics['scan_speed'] < 1000:
            issues.append({
                'type': 'performance',
                'severity': 'medium',
                'description': f"Below target scan speed: {metrics['scan_speed']:.1f} files/sec",
                'recommendation': "Review file filtering rules and optimize scan patterns"
            })
            
        return issues
        
    def _generate_recommendations(self) -> List[Dict]:
        """Generate performance optimization recommendations"""
        recommendations = []
        current_metrics = self.performance_monitor.get_current_metrics()
        
        # CPU optimization
        if current_metrics['cpu_usage'] > 25:
            recommendations.append({
                'category': 'cpu',
                'title': "CPU Usage Optimization",
                'description': "Reduce CPU usage by adjusting scan settings",
                'actions': [
                    "Decrease maximum thread count",
                    "Increase scan batch intervals",
                    "Optimize file filtering rules"
                ]
            })
            
        # Memory optimization
        if current_metrics['memory_usage'] > 400:  # MB
            recommendations.append({
                'category': 'memory',
                'title': "Memory Usage Optimization",
                'description': "Optimize memory consumption",
                'actions': [
                    "Reduce batch size",
                    "Enable incremental scanning",
                    "Adjust cache size"
                ]
            })
            
        # Performance optimization
        if current_metrics.get('scan_speed', 0) < 1200:
            recommendations.append({
                'category': 'performance',
                'title': "Scan Speed Optimization",
                'description': "Improve scanning performance",
                'actions': [
                    "Review exclusion lists",
                    "Optimize signature matching",
                    "Enable parallel processing"
                ]
            })
            
        return recommendations
        
    def _generate_visualizations(self, report: Dict, report_name: str):
        """Generate performance visualization charts"""
        try:
            # CPU Usage Chart
            plt.figure(figsize=(10, 6))
            dates = [m['date'] for m in report['daily_metrics']]
            cpu_usage = [m['metrics']['cpu_usage'] for m in report['daily_metrics']]
            plt.plot(dates, cpu_usage, marker='o')
            plt.title('CPU Usage Over Time')
            plt.xlabel('Date')
            plt.ylabel('CPU Usage (%)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(self.reports_dir / f"{report_name}_cpu.png")
            plt.close()
            
            # Memory Usage Chart
            plt.figure(figsize=(10, 6))
            memory_usage = [m['metrics']['memory_usage'] for m in report['daily_metrics']]
            plt.plot(dates, memory_usage, marker='o', color='green')
            plt.title('Memory Usage Over Time')
            plt.xlabel('Date')
            plt.ylabel('Memory Usage (MB)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(self.reports_dir / f"{report_name}_memory.png")
            plt.close()
            
            # Scan Speed Chart
            plt.figure(figsize=(10, 6))
            scan_speed = [m['metrics'].get('scan_speed', 0) for m in report['daily_metrics']]
            plt.plot(dates, scan_speed, marker='o', color='orange')
            plt.axhline(y=1000, color='r', linestyle='--', label='Target Speed')
            plt.title('Scan Speed Over Time')
            plt.xlabel('Date')
            plt.ylabel('Files per Second')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(self.reports_dir / f"{report_name}_speed.png")
            plt.close()
            
        except Exception as e:
            self.logger.error(f"Failed to generate visualizations: {e}")
            
    def _calculate_efficiency(self, metrics: Dict) -> float:
        """Calculate overall resource efficiency score"""
        cpu_score = self._calculate_cpu_efficiency(metrics)
        memory_score = self._calculate_memory_efficiency(metrics)
        disk_score = self._calculate_disk_efficiency(metrics)
        
        return (cpu_score + memory_score + disk_score) / 3
        
    def _calculate_cpu_efficiency(self, metrics: Dict) -> float:
        """Calculate CPU efficiency score (0-100)"""
        cpu_usage = metrics['cpu_usage']
        target_usage = 30  # Target maximum CPU usage
        
        if cpu_usage <= target_usage:
            return 100 * (1 - cpu_usage / target_usage)
        return max(0, 100 * (1 - (cpu_usage - target_usage) / target_usage))
        
    def _calculate_memory_efficiency(self, metrics: Dict) -> float:
        """Calculate memory efficiency score (0-100)"""
        memory_usage = metrics['memory_usage']
        target_usage = 512  # Target maximum memory usage (MB)
        
        if memory_usage <= target_usage:
            return 100 * (1 - memory_usage / target_usage)
        return max(0, 100 * (1 - (memory_usage - target_usage) / target_usage))
        
    def _calculate_disk_efficiency(self, metrics: Dict) -> float:
        """Calculate disk I/O efficiency score (0-100)"""
        io_usage = metrics['disk_io_read'] + metrics['disk_io_write']
        target_usage = 50  # Target maximum I/O (MB/s)
        
        if io_usage <= target_usage:
            return 100 * (1 - io_usage / target_usage)
        return max(0, 100 * (1 - (io_usage - target_usage) / target_usage)) 