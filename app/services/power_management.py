"""
Power Management Service for UPS-Cluster integration.
Handles power event monitoring and cluster management actions.
"""

import asyncio
import subprocess
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

from app.models.database import db
from app.models.ups import UPS
from app.models.cluster import Cluster
from app.models.ups_cluster_rule import UPSClusterRule, PowerEventType, ClusterActionType
from app.services.ups_scanner import UPSScanner
from app.services.orchestrator import OrchestrationService


class PowerManagementService:
    """Service for managing power events and cluster actions."""
    
    def __init__(self, app=None):
        self.app = app
        self.scanner = UPSScanner()
        self.orchestrator = OrchestrationService()
        self.logger = logging.getLogger(__name__)
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds
        
    def start_monitoring(self):
        """Start power event monitoring."""
        if self.monitoring_active:
            self.logger.warning("Power monitoring is already active")
            return
        
        self.monitoring_active = True
        self.logger.info("Starting power event monitoring")
        
        # Start monitoring in background
        asyncio.create_task(self._monitor_power_events())
    
    def stop_monitoring(self):
        """Stop power event monitoring."""
        self.monitoring_active = False
        self.logger.info("Stopping power event monitoring")
    
    async def _monitor_power_events(self):
        """Monitor power events and execute cluster actions."""
        while self.monitoring_active:
            try:
                await self._check_power_events()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                self.logger.error(f"Error in power event monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _check_power_events(self):
        """Check for power events and execute applicable rules."""
        try:
            # Get all active UPS devices
            ups_devices = db.session.query(UPS).filter(
                and_(UPS.nut_configured == True, UPS.nut_services_running == True)
            ).all()
            
            for ups in ups_devices:
                # Get current UPS status
                ups_status = self.scanner.get_ups_status(ups.name)
                if 'error' in ups_status:
                    self.logger.warning(f"Failed to get status for UPS {ups.name}: {ups_status['error']}")
                    continue
                
                # Update UPS status in database
                self._update_ups_status(ups, ups_status)
                
                # Check for applicable rules
                rules = db.session.query(UPSClusterRule).filter(
                    and_(
                        UPSClusterRule.ups_id == ups.id,
                        UPSClusterRule.enabled == True
                    )
                ).order_by(UPSClusterRule.priority).all()
                
                for rule in rules:
                    if rule.should_trigger(ups_status):
                        await self._execute_rule(rule, ups_status)
                        
        except Exception as e:
            self.logger.error(f"Error checking power events: {e}")
    
    def _update_ups_status(self, ups: UPS, status: Dict):
        """Update UPS status in database."""
        try:
            ups.status = status.get('ups.status', 'Unknown')
            ups.battery_charge = float(status.get('battery.charge', 0)) if status.get('battery.charge') else None
            ups.battery_voltage = float(status.get('battery.voltage', 0)) if status.get('battery.voltage') else None
            ups.battery_runtime = int(status.get('battery.runtime', 0)) if status.get('battery.runtime') else None
            ups.input_voltage = float(status.get('input.voltage', 0)) if status.get('input.voltage') else None
            ups.output_voltage = float(status.get('output.voltage', 0)) if status.get('output.voltage') else None
            ups.load_percentage = float(status.get('ups.load', 0)) if status.get('ups.load') else None
            ups.temperature = float(status.get('ups.temperature', 0)) if status.get('ups.temperature') else None
            ups.frequency = float(status.get('input.frequency', 0)) if status.get('input.frequency') else None
            ups.last_status_update = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating UPS status: {e}")
            db.session.rollback()
    
    async def _execute_rule(self, rule: UPSClusterRule, ups_status: Dict):
        """Execute a power management rule."""
        try:
            self.logger.info(f"Executing rule: {rule.name} - {rule.get_event_description()}")
            
            # Update rule execution tracking
            rule.last_triggered = datetime.utcnow()
            rule.execution_count += 1
            
            # Apply delay if specified
            if rule.action_delay > 0:
                await asyncio.sleep(rule.action_delay)
            
            # Execute cluster action
            success = await self._execute_cluster_action(rule)
            
            if success:
                rule.last_successful = datetime.utcnow()
                rule.success_count += 1
                self.logger.info(f"Rule {rule.name} executed successfully")
            else:
                rule.last_failed = datetime.utcnow()
                rule.failure_count += 1
                self.logger.error(f"Rule {rule.name} execution failed")
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error executing rule {rule.name}: {e}")
            rule.last_failed = datetime.utcnow()
            rule.failure_count += 1
            db.session.commit()
    
    async def _execute_cluster_action(self, rule: UPSClusterRule) -> bool:
        """Execute cluster action based on rule."""
        try:
            cluster = db.session.query(Cluster).filter(Cluster.id == rule.cluster_id).first()
            if not cluster:
                self.logger.error(f"Cluster {rule.cluster_id} not found")
                return False
            
            if rule.cluster_action == ClusterActionType.GRACEFUL_SHUTDOWN:
                return await self._graceful_shutdown_cluster(cluster)
            
            elif rule.cluster_action == ClusterActionType.FORCE_SHUTDOWN:
                return await self._force_shutdown_cluster(cluster)
            
            elif rule.cluster_action == ClusterActionType.STARTUP:
                return await self._startup_cluster(cluster)
            
            elif rule.cluster_action == ClusterActionType.SCALE_DOWN:
                return await self._scale_down_cluster(cluster)
            
            elif rule.cluster_action == ClusterActionType.SCALE_UP:
                return await self._scale_up_cluster(cluster)
            
            elif rule.cluster_action == ClusterActionType.PAUSE:
                return await self._pause_cluster(cluster)
            
            elif rule.cluster_action == ClusterActionType.RESUME:
                return await self._resume_cluster(cluster)
            
            else:
                self.logger.warning(f"Unknown cluster action: {rule.cluster_action}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing cluster action: {e}")
            return False
    
    async def _graceful_shutdown_cluster(self, cluster: Cluster) -> bool:
        """Gracefully shutdown cluster."""
        try:
            self.logger.info(f"Gracefully shutting down cluster: {cluster.name}")
            
            # Create shutdown operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_shutdown",
                description=f"Graceful shutdown triggered by power management",
                cluster_id=cluster.id
            )
            
            # Execute graceful shutdown on all nodes
            for node in cluster.nodes:
                if node.is_control_plane:
                    # Shutdown control plane nodes last
                    continue
                
                # Shutdown worker nodes first
                result = await self._shutdown_node(node, graceful=True)
                if not result:
                    self.logger.warning(f"Failed to gracefully shutdown node: {node.name}")
            
            # Shutdown control plane nodes
            for node in cluster.nodes:
                if node.is_control_plane:
                    result = await self._shutdown_node(node, graceful=True)
                    if not result:
                        self.logger.warning(f"Failed to gracefully shutdown control plane node: {node.name}")
            
            # Update cluster status
            cluster.status = "offline"
            db.session.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in graceful cluster shutdown: {e}")
            return False
    
    async def _force_shutdown_cluster(self, cluster: Cluster) -> bool:
        """Force shutdown cluster."""
        try:
            self.logger.info(f"Force shutting down cluster: {cluster.name}")
            
            # Create shutdown operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_shutdown",
                description=f"Force shutdown triggered by power management",
                cluster_id=cluster.id
            )
            
            # Force shutdown all nodes
            for node in cluster.nodes:
                result = await self._shutdown_node(node, graceful=False)
                if not result:
                    self.logger.warning(f"Failed to force shutdown node: {node.name}")
            
            # Update cluster status
            cluster.status = "offline"
            db.session.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in force cluster shutdown: {e}")
            return False
    
    async def _startup_cluster(self, cluster: Cluster) -> bool:
        """Startup cluster."""
        try:
            self.logger.info(f"Starting up cluster: {cluster.name}")
            
            # Create startup operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_startup",
                description=f"Startup triggered by power management",
                cluster_id=cluster.id
            )
            
            # Start control plane nodes first
            for node in cluster.nodes:
                if node.is_control_plane:
                    result = await self._startup_node(node)
                    if not result:
                        self.logger.warning(f"Failed to startup control plane node: {node.name}")
                        return False
            
            # Wait for control plane to be ready
            await asyncio.sleep(30)
            
            # Start worker nodes
            for node in cluster.nodes:
                if not node.is_control_plane:
                    result = await self._startup_node(node)
                    if not result:
                        self.logger.warning(f"Failed to startup worker node: {node.name}")
            
            # Update cluster status
            cluster.status = "active"
            db.session.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in cluster startup: {e}")
            return False
    
    async def _scale_down_cluster(self, cluster: Cluster) -> bool:
        """Scale down cluster resources."""
        try:
            self.logger.info(f"Scaling down cluster: {cluster.name}")
            
            # Create scale down operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_scale_down",
                description=f"Scale down triggered by power management",
                cluster_id=cluster.id
            )
            
            # Scale down non-essential workloads
            # This would involve Kubernetes API calls to scale down deployments
            # For now, we'll just log the action
            self.logger.info("Scaling down non-essential workloads")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in cluster scale down: {e}")
            return False
    
    async def _scale_up_cluster(self, cluster: Cluster) -> bool:
        """Scale up cluster resources."""
        try:
            self.logger.info(f"Scaling up cluster: {cluster.name}")
            
            # Create scale up operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_scale_up",
                description=f"Scale up triggered by power management",
                cluster_id=cluster.id
            )
            
            # Scale up workloads
            # This would involve Kubernetes API calls to scale up deployments
            # For now, we'll just log the action
            self.logger.info("Scaling up workloads")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in cluster scale up: {e}")
            return False
    
    async def _pause_cluster(self, cluster: Cluster) -> bool:
        """Pause cluster operations."""
        try:
            self.logger.info(f"Pausing cluster: {cluster.name}")
            
            # Create pause operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_pause",
                description=f"Pause triggered by power management",
                cluster_id=cluster.id
            )
            
            # Pause cluster operations
            # This would involve pausing Kubernetes workloads
            # For now, we'll just log the action
            self.logger.info("Pausing cluster operations")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in cluster pause: {e}")
            return False
    
    async def _resume_cluster(self, cluster: Cluster) -> bool:
        """Resume cluster operations."""
        try:
            self.logger.info(f"Resuming cluster: {cluster.name}")
            
            # Create resume operation
            operation = self.orchestrator.create_operation(
                operation_type="cluster_resume",
                description=f"Resume triggered by power management",
                cluster_id=cluster.id
            )
            
            # Resume cluster operations
            # This would involve resuming Kubernetes workloads
            # For now, we'll just log the action
            self.logger.info("Resuming cluster operations")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in cluster resume: {e}")
            return False
    
    async def _shutdown_node(self, node, graceful: bool = True) -> bool:
        """Shutdown a node."""
        try:
            if graceful:
                # Graceful shutdown
                cmd = f"ssh {node.ssh_user}@{node.ip_address} 'sudo shutdown -h +1'"
            else:
                # Force shutdown
                cmd = f"ssh {node.ssh_user}@{node.ip_address} 'sudo shutdown -h now'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error shutting down node {node.name}: {e}")
            return False
    
    async def _startup_node(self, node) -> bool:
        """Startup a node (requires IPMI or similar)."""
        try:
            # This would require IPMI or similar remote management
            # For now, we'll just log the action
            self.logger.info(f"Starting up node: {node.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting up node {node.name}: {e}")
            return False
    
    def create_power_rule(self, ups_id: int, cluster_id: int, power_event: PowerEventType, 
                         cluster_action: ClusterActionType, **kwargs) -> UPSClusterRule:
        """Create a new power management rule."""
        try:
            rule = UPSClusterRule(
                name=kwargs.get('name', f"Rule_{power_event.value}_{cluster_action.value}"),
                description=kwargs.get('description', ''),
                ups_id=ups_id,
                cluster_id=cluster_id,
                power_event=power_event,
                cluster_action=cluster_action,
                battery_threshold=kwargs.get('battery_threshold'),
                action_delay=kwargs.get('action_delay', 0),
                action_timeout=kwargs.get('action_timeout', 300),
                enabled=kwargs.get('enabled', True),
                priority=kwargs.get('priority', 100),
                auto_reverse=kwargs.get('auto_reverse', False),
                notify_on_trigger=kwargs.get('notify_on_trigger', True),
                notify_on_completion=kwargs.get('notify_on_completion', True),
                notify_on_failure=kwargs.get('notify_on_failure', True)
            )
            
            db.session.add(rule)
            db.session.commit()
            
            self.logger.info(f"Created power management rule: {rule.name}")
            return rule
            
        except Exception as e:
            self.logger.error(f"Error creating power rule: {e}")
            db.session.rollback()
            raise
    
    def get_power_rules(self, ups_id: Optional[int] = None, cluster_id: Optional[int] = None) -> List[UPSClusterRule]:
        """Get power management rules."""
        query = db.session.query(UPSClusterRule)
        
        if ups_id:
            query = query.filter(UPSClusterRule.ups_id == ups_id)
        
        if cluster_id:
            query = query.filter(UPSClusterRule.cluster_id == cluster_id)
        
        return query.order_by(UPSClusterRule.priority).all()
    
    def delete_power_rule(self, rule_id: int) -> bool:
        """Delete a power management rule."""
        try:
            rule = db.session.query(UPSClusterRule).filter(UPSClusterRule.id == rule_id).first()
            if rule:
                db.session.delete(rule)
                db.session.commit()
                self.logger.info(f"Deleted power management rule: {rule.name}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting power rule: {e}")
            db.session.rollback()
            return False
