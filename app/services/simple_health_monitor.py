"""
Simple Health Monitor - Local RAG Integration for Raspberry Pi 5.

This module integrates the local RAG system with the existing health monitoring
to provide intelligent insights without any external dependencies.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .local_rag_system import get_local_rag_system
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation

logger = logging.getLogger(__name__)

class SimpleHealthMonitor:
    """Simple health monitor using local RAG system."""
    
    def __init__(self):
        self.rag_system = get_local_rag_system()
        self.last_check = None
        self.check_history = []
    
    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check using local RAG insights."""
        logger.info("Running comprehensive health check with local RAG...")
        
        # Traditional checks
        traditional_results = self._run_traditional_checks()
        
        # Local RAG analysis
        rag_results = self._run_rag_analysis()
        
        # Combine results
        combined_results = self._combine_results(traditional_results, rag_results)
        
        # Store results
        self.last_check = combined_results
        self.check_history.append({
            'timestamp': datetime.utcnow(),
            'results': combined_results
        })
        
        # Keep only last 100 checks
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]
        
        logger.info(f"Health check completed. Overall score: {combined_results['overall_score']}%")
        
        return combined_results
    
    def _run_traditional_checks(self) -> Dict[str, Any]:
        """Run traditional health checks."""
        results = {
            'database_health': self._check_database_health(),
            'node_connectivity': self._check_node_connectivity(),
            'cluster_status': self._check_cluster_status(),
            'ssh_health': self._check_ssh_health(),
            'system_resources': self._check_system_resources(),
            'ansible_health': self._check_ansible_health()
        }
        
        return results
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and integrity."""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            
            # Check table existence
            tables = ['nodes', 'clusters', 'operations', 'users']
            missing_tables = []
            
            for table in tables:
                try:
                    db.session.execute(f'SELECT COUNT(*) FROM {table}')
                except Exception:
                    missing_tables.append(table)
            
            return {
                'status': 'healthy' if not missing_tables else 'degraded',
                'connected': True,
                'missing_tables': missing_tables,
                'score': 100 if not missing_tables else 50
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'critical',
                'connected': False,
                'error': str(e),
                'score': 0
            }
    
    def _check_node_connectivity(self) -> Dict[str, Any]:
        """Check node connectivity and status."""
        try:
            nodes = Node.query.all()
            
            if not nodes:
                return {
                    'status': 'warning',
                    'message': 'No nodes configured',
                    'score': 70
                }
            
            online_nodes = 0
            ssh_ready_nodes = 0
            issues = []
            
            for node in nodes:
                if node.status == 'online':
                    online_nodes += 1
                
                if node.ssh_connection_ready:
                    ssh_ready_nodes += 1
                else:
                    issues.append(f"Node {node.hostname}: SSH not ready")
            
            total_nodes = len(nodes)
            connectivity_score = (online_nodes / total_nodes) * 100 if total_nodes > 0 else 0
            ssh_score = (ssh_ready_nodes / total_nodes) * 100 if total_nodes > 0 else 0
            
            overall_score = (connectivity_score + ssh_score) / 2
            
            return {
                'status': 'healthy' if overall_score > 80 else 'degraded' if overall_score > 50 else 'critical',
                'total_nodes': total_nodes,
                'online_nodes': online_nodes,
                'ssh_ready_nodes': ssh_ready_nodes,
                'issues': issues,
                'score': overall_score
            }
            
        except Exception as e:
            logger.error(f"Node connectivity check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'score': 0
            }
    
    def _check_cluster_status(self) -> Dict[str, Any]:
        """Check cluster health and status."""
        try:
            clusters = Cluster.query.all()
            
            if not clusters:
                return {
                    'status': 'info',
                    'message': 'No clusters configured',
                    'score': 90
                }
            
            healthy_clusters = 0
            issues = []
            
            for cluster in clusters:
                if cluster.status == 'active':
                    healthy_clusters += 1
                else:
                    issues.append(f"Cluster {cluster.name}: Status {cluster.status}")
            
            total_clusters = len(clusters)
            score = (healthy_clusters / total_clusters) * 100 if total_clusters > 0 else 0
            
            return {
                'status': 'healthy' if score > 80 else 'degraded' if score > 50 else 'critical',
                'total_clusters': total_clusters,
                'healthy_clusters': healthy_clusters,
                'issues': issues,
                'score': score
            }
            
        except Exception as e:
            logger.error(f"Cluster status check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'score': 0
            }
    
    def _check_ssh_health(self) -> Dict[str, Any]:
        """Check SSH key management health."""
        try:
            nodes = Node.query.all()
            
            if not nodes:
                return {
                    'status': 'info',
                    'message': 'No nodes to check SSH health',
                    'score': 90
                }
            
            ssh_ready_count = 0
            issues = []
            
            for node in nodes:
                ssh_status = node.get_ssh_key_status()
                
                if ssh_status['overall_status'] == 'ready':
                    ssh_ready_count += 1
                else:
                    issues.append(f"Node {node.hostname}: {ssh_status['status_description']}")
            
            total_nodes = len(nodes)
            score = (ssh_ready_count / total_nodes) * 100 if total_nodes > 0 else 0
            
            return {
                'status': 'healthy' if score > 80 else 'degraded' if score > 50 else 'critical',
                'total_nodes': total_nodes,
                'ssh_ready_count': ssh_ready_count,
                'issues': issues,
                'score': score
            }
            
        except Exception as e:
            logger.error(f"SSH health check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'score': 0
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # Simple system resource check
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate resource health score
            cpu_score = 100 - cpu_percent
            memory_score = 100 - memory.percent
            disk_score = 100 - (disk.used / disk.total * 100)
            
            overall_score = (cpu_score + memory_score + disk_score) / 3
            
            return {
                'status': 'healthy' if overall_score > 70 else 'degraded' if overall_score > 40 else 'critical',
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.used / disk.total * 100,
                'score': overall_score
            }
            
        except ImportError:
            return {
                'status': 'info',
                'message': 'psutil not available - resource monitoring disabled',
                'score': 85
            }
        except Exception as e:
            logger.error(f"System resources check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'score': 0
            }
    
    def _check_ansible_health(self) -> Dict[str, Any]:
        """Check Ansible configuration and recent operations."""
        try:
            # Check recent operations
            recent_ops = Operation.query.filter(
                Operation.created_at > datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            if not recent_ops:
                return {
                    'status': 'info',
                    'message': 'No recent Ansible operations',
                    'score': 90
                }
            
            successful_ops = sum(1 for op in recent_ops if op.success)
            total_ops = len(recent_ops)
            success_rate = (successful_ops / total_ops) * 100 if total_ops > 0 else 0
            
            failed_ops = [op for op in recent_ops if not op.success]
            issues = []
            
            for op in failed_ops[:5]:  # Limit to 5 most recent failures
                issues.append(f"Operation {op.operation_name}: {op.error_message}")
            
            return {
                'status': 'healthy' if success_rate > 80 else 'degraded' if success_rate > 50 else 'critical',
                'total_operations': total_ops,
                'successful_operations': successful_ops,
                'success_rate': success_rate,
                'issues': issues,
                'score': success_rate
            }
            
        except Exception as e:
            logger.error(f"Ansible health check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'score': 0
            }
    
    def _run_rag_analysis(self) -> Dict[str, Any]:
        """Run local RAG analysis."""
        try:
            # Get RAG insights
            rag_insights = self.rag_system.get_health_insights()
            
            # Get RAG statistics
            rag_stats = self.rag_system.get_statistics()
            
            return {
                'rag_insights': rag_insights,
                'rag_statistics': rag_stats,
                'rag_confidence': rag_insights.get('confidence', 0.5)
            }
            
        except Exception as e:
            logger.error(f"RAG analysis failed: {e}")
            return {
                'rag_insights': {'insights': ['RAG analysis failed'], 'confidence': 0.0},
                'rag_statistics': {'total_documents': 0},
                'rag_confidence': 0.0
            }
    
    def _combine_results(self, traditional: Dict[str, Any], rag: Dict[str, Any]) -> Dict[str, Any]:
        """Combine traditional and RAG results."""
        
        # Calculate traditional health score
        traditional_scores = []
        traditional_issues = []
        
        for check_name, check_result in traditional.items():
            if isinstance(check_result, dict) and 'score' in check_result:
                traditional_scores.append(check_result['score'])
                
                if check_result.get('status') in ['critical', 'degraded']:
                    traditional_issues.append({
                        'category': check_name,
                        'severity': check_result['status'],
                        'issues': check_result.get('issues', [])
                    })
        
        traditional_score = sum(traditional_scores) / len(traditional_scores) if traditional_scores else 50.0
        
        # Get RAG insights
        rag_insights = rag.get('rag_insights', {})
        rag_confidence = rag.get('rag_confidence', 0.5)
        
        # Combine scores (weighted by RAG confidence)
        if rag_confidence > 0.7:
            # High RAG confidence - use weighted average
            combined_score = (traditional_score * 0.7) + (rag_confidence * 30)
        else:
            # Low RAG confidence - rely more on traditional checks
            combined_score = traditional_score * 0.9
        
        # Determine overall status
        if combined_score >= 80:
            overall_status = 'healthy'
        elif combined_score >= 60:
            overall_status = 'degraded'
        elif combined_score >= 40:
            overall_status = 'warning'
        else:
            overall_status = 'critical'
        
        # Combine recommendations
        all_recommendations = []
        
        # Traditional recommendations
        for issue in traditional_issues:
            if issue['issues']:
                all_recommendations.append(f"🔧 {issue['category'].replace('_', ' ').title()}: {', '.join(issue['issues'][:2])}")
        
        # RAG recommendations
        rag_recommendations = rag_insights.get('insights', [])
        all_recommendations.extend(rag_recommendations)
        
        return {
            'overall_score': round(combined_score, 2),
            'overall_status': overall_status,
            'traditional_score': round(traditional_score, 2),
            'rag_score': round(rag_confidence * 100, 2),
            'rag_confidence': rag_confidence,
            'traditional_checks': traditional,
            'rag_analysis': rag,
            'recommendations': all_recommendations,
            'critical_issues': len([i for i in traditional_issues if i['severity'] == 'critical']),
            'total_issues': len(traditional_issues),
            'rag_patterns_found': rag_insights.get('patterns_found', 0),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def analyze_ansible_failure(self, output: str, playbook_name: str, nodes: List[str]) -> Dict[str, Any]:
        """Analyze Ansible failure using local RAG."""
        return self.rag_system.analyze_ansible_output(output, playbook_name, nodes)
    
    def get_health_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get health trend over specified days."""
        try:
            # Get historical data
            historical_checks = [check for check in self.check_history 
                               if (datetime.utcnow() - check['timestamp']).days <= days]
            
            if len(historical_checks) < 2:
                return {
                    'trend': 'insufficient_data',
                    'message': 'Not enough historical data for trend analysis'
                }
            
            # Calculate trend
            scores = [check['results']['overall_score'] for check in historical_checks]
            
            if len(scores) >= 3:
                recent_avg = sum(scores[-3:]) / 3
                older_avg = sum(scores[:-3]) / max(1, len(scores) - 3)
                trend_direction = recent_avg - older_avg
                
                if trend_direction > 5:
                    trend = 'improving'
                elif trend_direction < -5:
                    trend = 'degrading'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            return {
                'trend': trend,
                'current_score': scores[-1] if scores else 0,
                'average_score': sum(scores) / len(scores),
                'data_points': len(scores),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate health trend: {e}")
            return {
                'trend': 'error',
                'message': f'Failed to calculate trend: {str(e)}'
            }
    
    def get_detailed_health_report(self) -> Dict[str, Any]:
        """Get detailed health report with all information."""
        if not self.last_check:
            # Run initial check
            self.run_comprehensive_health_check()
        
        trend_analysis = self.get_health_trend()
        
        return {
            'current_health': self.last_check,
            'trend_analysis': trend_analysis,
            'check_history_count': len(self.check_history),
            'last_check_time': self.last_check['last_updated'] if self.last_check else None,
            'rag_statistics': self.rag_system.get_statistics()
        }

# Global instance
simple_health_monitor = SimpleHealthMonitor()

def get_simple_health_monitor() -> SimpleHealthMonitor:
    """Get the global simple health monitor instance."""
    return simple_health_monitor
