"""
AI Orchestrator Integration - Bridges AI health monitoring with existing orchestrator.

This module integrates the AI-powered health monitoring system with the existing
orchestrator service to provide intelligent feedback and learning capabilities.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from .enhanced_health_monitor import get_enhanced_health_monitor
from .orchestrator import OrchestrationService
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation

logger = logging.getLogger(__name__)

class AIOrchestratorIntegration:
    """Integration layer between AI health monitoring and orchestrator service."""
    
    def __init__(self):
        self.orchestrator = OrchestrationService()
        self.health_monitor = get_enhanced_health_monitor()
        self.learning_enabled = True
        self.feedback_history = []
    
    def run_operation_with_ai_feedback(self, operation_type: str, operation_name: str,
                                     nodes: List[Node] = None, clusters: List[Cluster] = None,
                                     extra_vars: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run an operation with AI-powered feedback and learning.
        
        Args:
            operation_type: Type of operation (install, configure, etc.)
            operation_name: Name of the operation
            nodes: List of nodes to operate on
            clusters: List of clusters to operate on
            extra_vars: Additional variables for the operation
            
        Returns:
            Dictionary with operation results and AI insights
        """
        logger.info(f"Running AI-enhanced operation: {operation_name}")
        
        # Pre-operation health check
        pre_health = self.health_monitor.run_comprehensive_health_check()
        
        # Create operation record
        operation = self._create_operation_record(operation_type, operation_name, nodes, clusters)
        
        try:
            # Run the operation
            if operation_type == 'install_microk8s':
                success, output = self._run_install_microk8s(nodes, extra_vars)
            elif operation_type == 'setup_cluster':
                success, output = self._run_setup_cluster(clusters, extra_vars)
            elif operation_type == 'troubleshoot':
                success, output = self._run_troubleshoot(nodes, extra_vars)
            else:
                success, output = self._run_generic_operation(operation_type, operation_name, nodes, clusters, extra_vars)
            
            # Update operation record
            operation.success = success
            operation.output = output
            operation.completed_at = datetime.utcnow()
            
            if not success:
                operation.error_message = "Operation failed - see output for details"
            
            db.session.commit()
            
            # AI analysis of results
            ai_insights = self._analyze_operation_results(operation, output, success)
            
            # Post-operation health check
            post_health = self.health_monitor.run_comprehensive_health_check()
            
            # Generate comprehensive report
            report = self._generate_operation_report(
                operation, success, output, ai_insights, pre_health, post_health
            )
            
            # Learn from the operation
            if self.learning_enabled:
                self._learn_from_operation(operation, success, output, ai_insights)
            
            return report
            
        except Exception as e:
            logger.error(f"Operation failed with exception: {e}")
            
            # Update operation record
            operation.success = False
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            db.session.commit()
            
            # AI analysis of the failure
            ai_insights = self._analyze_operation_failure(operation, str(e))
            
            return {
                'success': False,
                'operation_id': operation.id,
                'error': str(e),
                'ai_insights': ai_insights,
                'recommendations': ai_insights.get('recommendations', [])
            }
    
    def _create_operation_record(self, operation_type: str, operation_name: str,
                               nodes: List[Node], clusters: List[Cluster]) -> Operation:
        """Create operation record in database."""
        operation = Operation(
            operation_type=operation_type,
            operation_name=operation_name,
            description=f"AI-enhanced {operation_name} operation",
            status='running',
            started_at=datetime.utcnow()
        )
        
        if nodes and len(nodes) == 1:
            operation.node_id = nodes[0].id
        elif clusters and len(clusters) == 1:
            operation.cluster_id = clusters[0].id
        
        db.session.add(operation)
        db.session.flush()
        
        return operation
    
    def _run_install_microk8s(self, nodes: List[Node], extra_vars: Dict[str, Any]) -> Tuple[bool, str]:
        """Run MicroK8s installation with AI monitoring."""
        try:
            # Generate inventory
            inventory_file = self.orchestrator._generate_inventory(nodes)
            
            # Run playbook
            playbook_path = os.path.join(self.orchestrator.playbooks_dir, 'install_microk8s.yml')
            success, output = self.orchestrator._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            return success, output
            
        except Exception as e:
            logger.error(f"MicroK8s installation failed: {e}")
            return False, str(e)
    
    def _run_setup_cluster(self, clusters: List[Cluster], extra_vars: Dict[str, Any]) -> Tuple[bool, str]:
        """Run cluster setup with AI monitoring."""
        try:
            # Get nodes for clusters
            all_nodes = []
            for cluster in clusters:
                all_nodes.extend(cluster.nodes)
            
            if not all_nodes:
                return False, "No nodes found in clusters"
            
            # Generate inventory
            inventory_file = self.orchestrator._generate_inventory(all_nodes)
            
            # Run playbook
            playbook_path = os.path.join(self.orchestrator.playbooks_dir, 'setup_cluster.yml')
            success, output = self.orchestrator._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            return success, output
            
        except Exception as e:
            logger.error(f"Cluster setup failed: {e}")
            return False, str(e)
    
    def _run_troubleshoot(self, nodes: List[Node], extra_vars: Dict[str, Any]) -> Tuple[bool, str]:
        """Run troubleshooting with AI analysis."""
        try:
            # Generate inventory
            inventory_file = self.orchestrator._generate_inventory(nodes)
            
            # Run playbook
            playbook_path = os.path.join(self.orchestrator.playbooks_dir, 'troubleshoot_cluster.yml')
            success, output = self.orchestrator._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            return success, output
            
        except Exception as e:
            logger.error(f"Troubleshooting failed: {e}")
            return False, str(e)
    
    def _run_generic_operation(self, operation_type: str, operation_name: str,
                             nodes: List[Node], clusters: List[Cluster],
                             extra_vars: Dict[str, Any]) -> Tuple[bool, str]:
        """Run generic operation."""
        try:
            # This would be expanded based on specific operation types
            return False, f"Generic operation {operation_name} not implemented"
            
        except Exception as e:
            logger.error(f"Generic operation failed: {e}")
            return False, str(e)
    
    def _analyze_operation_results(self, operation: Operation, output: str, success: bool) -> Dict[str, Any]:
        """Analyze operation results using AI."""
        try:
            if success:
                return {
                    'analysis_type': 'success',
                    'confidence': 0.8,
                    'insights': ['Operation completed successfully'],
                    'recommendations': ['Monitor system for stability']
                }
            else:
                # Analyze failure with AI
                nodes = [operation.node] if operation.node else []
                node_hostnames = [node.hostname for node in nodes if node]
                
                issues = self.health_monitor.analyze_ansible_failure(
                    output, operation.operation_name, node_hostnames
                )
                
                return {
                    'analysis_type': 'failure',
                    'confidence': 0.7,
                    'issues_found': len(issues),
                    'issues': [issue.__dict__ for issue in issues],
                    'recommendations': self._extract_recommendations(issues)
                }
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'analysis_type': 'error',
                'confidence': 0.0,
                'error': str(e),
                'recommendations': ['AI analysis failed - check logs']
            }
    
    def _analyze_operation_failure(self, operation: Operation, error: str) -> Dict[str, Any]:
        """Analyze operation failure."""
        return {
            'analysis_type': 'exception',
            'confidence': 0.9,
            'error_type': 'system_exception',
            'error_message': error,
            'recommendations': [
                'Check system logs for detailed error information',
                'Verify system resources and permissions',
                'Consider running health check to identify underlying issues'
            ]
        }
    
    def _extract_recommendations(self, issues: List) -> List[str]:
        """Extract recommendations from AI-analyzed issues."""
        recommendations = []
        
        for issue in issues:
            if hasattr(issue, 'suggested_actions') and issue.suggested_actions:
                recommendations.extend(issue.suggested_actions)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:5]  # Limit to top 5
    
    def _generate_operation_report(self, operation: Operation, success: bool, output: str,
                                 ai_insights: Dict[str, Any], pre_health: Dict[str, Any],
                                 post_health: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive operation report."""
        
        # Calculate health impact
        health_impact = post_health['overall_score'] - pre_health['overall_score']
        
        # Determine impact level
        if abs(health_impact) < 5:
            impact_level = 'minimal'
        elif abs(health_impact) < 15:
            impact_level = 'moderate'
        else:
            impact_level = 'significant'
        
        return {
            'success': success,
            'operation_id': operation.id,
            'operation_name': operation.operation_name,
            'operation_type': operation.operation_type,
            'duration': (operation.completed_at - operation.started_at).total_seconds() if operation.completed_at else None,
            'ai_insights': ai_insights,
            'health_impact': {
                'pre_operation_score': pre_health['overall_score'],
                'post_operation_score': post_health['overall_score'],
                'impact': health_impact,
                'impact_level': impact_level
            },
            'recommendations': ai_insights.get('recommendations', []),
            'output_summary': output[:500] + '...' if len(output) > 500 else output,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _learn_from_operation(self, operation: Operation, success: bool, output: str,
                            ai_insights: Dict[str, Any]):
        """Learn from operation results to improve future performance."""
        try:
            # Store feedback for learning
            feedback = {
                'operation_type': operation.operation_type,
                'operation_name': operation.operation_name,
                'success': success,
                'output_length': len(output),
                'ai_confidence': ai_insights.get('confidence', 0.0),
                'issues_found': ai_insights.get('issues_found', 0),
                'timestamp': datetime.utcnow()
            }
            
            self.feedback_history.append(feedback)
            
            # Keep only last 1000 feedback entries
            if len(self.feedback_history) > 1000:
                self.feedback_history = self.feedback_history[-1000:]
            
            # TODO: Implement reinforcement learning updates
            # This would update the AI models based on the feedback
            
            logger.info(f"Learned from operation: {operation.operation_name} (Success: {success})")
            
        except Exception as e:
            logger.error(f"Learning from operation failed: {e}")
    
    def get_operation_recommendations(self, operation_type: str, context: Dict[str, Any] = None) -> List[str]:
        """Get AI-powered recommendations for an operation."""
        try:
            # Analyze historical data for this operation type
            historical_ops = [f for f in self.feedback_history 
                            if f['operation_type'] == operation_type]
            
            if not historical_ops:
                return ['No historical data available for recommendations']
            
            # Calculate success rate
            successful_ops = sum(1 for op in historical_ops if op['success'])
            success_rate = successful_ops / len(historical_ops)
            
            recommendations = []
            
            if success_rate < 0.5:
                recommendations.append(f"⚠️ Low success rate ({success_rate:.1%}) for {operation_type} operations")
                recommendations.append("Consider running health check before operation")
                recommendations.append("Review recent failures for common patterns")
            elif success_rate > 0.8:
                recommendations.append(f"✅ High success rate ({success_rate:.1%}) for {operation_type} operations")
                recommendations.append("System appears stable for this operation type")
            
            # Add context-specific recommendations
            if context:
                if context.get('nodes') and len(context['nodes']) > 5:
                    recommendations.append("Large number of nodes - consider running in batches")
                
                if context.get('clusters') and len(context['clusters']) > 1:
                    recommendations.append("Multiple clusters - ensure proper resource allocation")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get operation recommendations: {e}")
            return ['Unable to generate recommendations - check system logs']
    
    def get_system_insights(self) -> Dict[str, Any]:
        """Get AI-powered system insights."""
        try:
            # Get current health
            health_report = self.health_monitor.get_detailed_health_report()
            
            # Analyze feedback history
            total_operations = len(self.feedback_history)
            successful_operations = sum(1 for f in self.feedback_history if f['success'])
            
            # Calculate operation type success rates
            operation_success_rates = {}
            for op_type in set(f['operation_type'] for f in self.feedback_history):
                type_ops = [f for f in self.feedback_history if f['operation_type'] == op_type]
                type_success = sum(1 for f in type_ops if f['success'])
                operation_success_rates[op_type] = type_success / len(type_ops) if type_ops else 0
            
            # Generate insights
            insights = {
                'overall_health': health_report['current_health'],
                'operation_statistics': {
                    'total_operations': total_operations,
                    'successful_operations': successful_operations,
                    'overall_success_rate': successful_operations / total_operations if total_operations > 0 else 0,
                    'operation_type_success_rates': operation_success_rates
                },
                'trends': health_report['trend_analysis'],
                'recommendations': self._generate_system_recommendations(health_report, operation_success_rates)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get system insights: {e}")
            return {
                'error': str(e),
                'recommendations': ['Unable to generate insights - check system logs']
            }
    
    def _generate_system_recommendations(self, health_report: Dict[str, Any], 
                                       operation_success_rates: Dict[str, float]) -> List[str]:
        """Generate system-wide recommendations."""
        recommendations = []
        
        # Health-based recommendations
        current_health = health_report['current_health']
        if current_health['overall_score'] < 70:
            recommendations.append("🚨 System health is below optimal - investigate critical issues")
        
        if current_health['critical_issues'] > 0:
            recommendations.append(f"⚠️ {current_health['critical_issues']} critical issues require immediate attention")
        
        # Operation-based recommendations
        for op_type, success_rate in operation_success_rates.items():
            if success_rate < 0.6:
                recommendations.append(f"🔧 {op_type} operations have low success rate ({success_rate:.1%}) - review procedures")
        
        # Trend-based recommendations
        trend = health_report['trend_analysis'].get('trend', 'stable')
        if trend == 'degrading':
            recommendations.append("📉 System health is degrading - investigate root causes")
        elif trend == 'improving':
            recommendations.append("📈 System health is improving - continue current practices")
        
        if not recommendations:
            recommendations.append("✅ System is performing well - no immediate action required")
        
        return recommendations

# Global instance
ai_orchestrator = AIOrchestratorIntegration()

def get_ai_orchestrator() -> AIOrchestratorIntegration:
    """Get the global AI orchestrator instance."""
    return ai_orchestrator
