"""
AI Assistant Configuration Helper.

This module provides configuration management for the AI assistant features,
allowing users to enable/disable RAG system functionality.
"""

import logging
from typing import Dict, Any, Optional
from .config import config

logger = logging.getLogger(__name__)

class AIConfigManager:
    """Manages AI assistant configuration."""
    
    def __init__(self):
        self.config = config
    
    def is_ai_assistant_enabled(self) -> bool:
        """Check if AI assistant is enabled."""
        return self.config.get('ai_assistant.enabled', False)
    
    def is_rag_system_enabled(self) -> bool:
        """Check if RAG system is enabled."""
        if not self.is_ai_assistant_enabled():
            return False
        return self.config.get('ai_assistant.rag_system.enabled', False)
    
    def is_web_interface_enabled(self) -> bool:
        """Check if web interface is enabled."""
        if not self.is_ai_assistant_enabled():
            return False
        return self.config.get('ai_assistant.web_interface.enabled', False)
    
    def should_show_in_navigation(self) -> bool:
        """Check if assistant should be shown in navigation."""
        if not self.is_web_interface_enabled():
            return False
        return self.config.get('ai_assistant.web_interface.show_in_nav', False)
    
    def is_ansible_analysis_enabled(self) -> bool:
        """Check if Ansible analysis is enabled."""
        if not self.is_ai_assistant_enabled():
            return False
        return self.config.get('ai_assistant.web_interface.allow_ansible_analysis', False)
    
    def is_health_insights_enabled(self) -> bool:
        """Check if health insights are enabled."""
        if not self.is_ai_assistant_enabled():
            return False
        return self.config.get('ai_assistant.web_interface.allow_health_insights', False)
    
    def should_store_chat_history(self) -> bool:
        """Check if chat history should be stored."""
        if not self.is_ai_assistant_enabled():
            return False
        return self.config.get('ai_assistant.privacy.store_chat_history', False)
    
    def should_store_ansible_outputs(self) -> bool:
        """Check if Ansible outputs should be stored."""
        if not self.is_ai_assistant_enabled():
            return False
        return self.config.get('ai_assistant.privacy.store_ansible_outputs', False)
    
    def should_anonymize_data(self) -> bool:
        """Check if data should be anonymized."""
        return self.config.get('ai_assistant.privacy.anonymize_data', False)
    
    def should_auto_learn(self) -> bool:
        """Check if system should auto-learn from operations."""
        if not self.is_rag_system_enabled():
            return False
        return self.config.get('ai_assistant.rag_system.auto_learn', False)
    
    def get_rag_config(self) -> Dict[str, Any]:
        """Get RAG system configuration."""
        return {
            'data_dir': self.config.get('ai_assistant.rag_system.data_dir', 'data/local_rag'),
            'max_documents': self.config.get('ai_assistant.rag_system.max_documents', 10000),
            'max_document_size': self.config.get('ai_assistant.rag_system.max_document_size', 50000),
            'retention_days': self.config.get('ai_assistant.rag_system.retention_days', 365),
            'min_similarity': self.config.get('ai_assistant.rag_system.min_similarity', 0.1),
            'auto_learn': self.should_auto_learn()
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return {
            'max_concurrent_requests': self.config.get('ai_assistant.performance.max_concurrent_requests', 5),
            'response_timeout': self.config.get('ai_assistant.performance.response_timeout', 30),
            'cache_responses': self.config.get('ai_assistant.performance.cache_responses', True),
            'cache_duration': self.config.get('ai_assistant.performance.cache_duration', 300)
        }
    
    def get_privacy_config(self) -> Dict[str, Any]:
        """Get privacy configuration."""
        return {
            'store_chat_history': self.should_store_chat_history(),
            'store_ansible_outputs': self.should_store_ansible_outputs(),
            'anonymize_data': self.should_anonymize_data(),
            'auto_cleanup': self.config.get('ai_assistant.privacy.auto_cleanup', True),
            'cleanup_interval_days': self.config.get('ai_assistant.privacy.cleanup_interval_days', 30)
        }
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get full AI assistant configuration."""
        return {
            'enabled': self.is_ai_assistant_enabled(),
            'rag_system': {
                'enabled': self.is_rag_system_enabled(),
                **self.get_rag_config()
            },
            'web_interface': {
                'enabled': self.is_web_interface_enabled(),
                'show_in_nav': self.should_show_in_navigation(),
                'allow_ansible_analysis': self.is_ansible_analysis_enabled(),
                'allow_health_insights': self.is_health_insights_enabled()
            },
            'performance': self.get_performance_config(),
            'privacy': self.get_privacy_config()
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate AI assistant configuration."""
        issues = []
        warnings = []
        
        # Check if AI assistant is enabled
        if not self.is_ai_assistant_enabled():
            warnings.append("AI assistant is disabled - all AI features will be unavailable")
            return {'valid': True, 'issues': issues, 'warnings': warnings}
        
        # Check RAG system configuration
        if self.is_rag_system_enabled():
            rag_config = self.get_rag_config()
            
            # Validate data directory
            data_dir = rag_config['data_dir']
            if not data_dir:
                issues.append("RAG system data directory is not configured")
            
            # Validate document limits
            max_docs = rag_config['max_documents']
            if max_docs <= 0:
                issues.append("RAG system max_documents must be greater than 0")
            elif max_docs > 100000:
                warnings.append("RAG system max_documents is very high - consider reducing for better performance")
            
            # Validate retention period
            retention = rag_config['retention_days']
            if retention <= 0:
                issues.append("RAG system retention_days must be greater than 0")
            elif retention > 3650:  # 10 years
                warnings.append("RAG system retention_days is very long - consider reducing for storage management")
            
            # Validate similarity threshold
            min_sim = rag_config['min_similarity']
            if min_sim < 0 or min_sim > 1:
                issues.append("RAG system min_similarity must be between 0 and 1")
        
        # Check web interface configuration
        if self.is_web_interface_enabled():
            perf_config = self.get_performance_config()
            
            # Validate concurrent requests
            max_req = perf_config['max_concurrent_requests']
            if max_req <= 0:
                issues.append("Performance max_concurrent_requests must be greater than 0")
            elif max_req > 20:
                warnings.append("Performance max_concurrent_requests is high - consider reducing for stability")
            
            # Validate timeout
            timeout = perf_config['response_timeout']
            if timeout <= 0:
                issues.append("Performance response_timeout must be greater than 0")
            elif timeout > 300:
                warnings.append("Performance response_timeout is very high - consider reducing")
        
        # Check privacy configuration
        privacy_config = self.get_privacy_config()
        
        if privacy_config['auto_cleanup']:
            cleanup_interval = privacy_config['cleanup_interval_days']
            if cleanup_interval <= 0:
                issues.append("Privacy cleanup_interval_days must be greater than 0")
            elif cleanup_interval < 7:
                warnings.append("Privacy cleanup_interval_days is very short - consider increasing")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def log_config_status(self):
        """Log the current AI assistant configuration status."""
        if not self.is_ai_assistant_enabled():
            logger.info("AI Assistant: DISABLED")
            return
        
        logger.info("AI Assistant: ENABLED")
        
        if self.is_rag_system_enabled():
            rag_config = self.get_rag_config()
            logger.info(f"  RAG System: ENABLED (data_dir: {rag_config['data_dir']}, max_docs: {rag_config['max_documents']})")
        else:
            logger.info("  RAG System: DISABLED")
        
        if self.is_web_interface_enabled():
            logger.info("  Web Interface: ENABLED")
            if self.should_show_in_navigation():
                logger.info("    Navigation: ENABLED")
            if self.is_ansible_analysis_enabled():
                logger.info("    Ansible Analysis: ENABLED")
            if self.is_health_insights_enabled():
                logger.info("    Health Insights: ENABLED")
        else:
            logger.info("  Web Interface: DISABLED")
        
        # Log privacy settings
        privacy_config = self.get_privacy_config()
        logger.info(f"  Privacy: store_chat={privacy_config['store_chat_history']}, "
                   f"store_ansible={privacy_config['store_ansible_outputs']}, "
                   f"anonymize={privacy_config['anonymize_data']}")

# Global instance
ai_config = AIConfigManager()

def get_ai_config() -> AIConfigManager:
    """Get the global AI configuration manager."""
    return ai_config
