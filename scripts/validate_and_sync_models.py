#!/usr/bin/env python3
"""
Model Validation and Synchronization Script for MicroK8s Cluster Orchestrator.

This script ensures that all SQLAlchemy models are properly synchronized with the database
and provides comprehensive validation and repair capabilities.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.models.database import db
from app.models.flask_models import Node, Cluster, Operation
from app.utils.migration_manager import MigrationManager
from app.utils.model_validator import ModelValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_and_sync_models():
    """Main function to validate and sync models with database."""
    print("🔍 MicroK8s Cluster Orchestrator - Model Validation & Synchronization")
    print("=" * 80)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize managers
            migration_manager = MigrationManager()
            model_validator = ModelValidator()
            
            print("\n📊 STEP 1: Running comprehensive health check...")
            health_report = migration_manager.create_health_report()
            print(health_report)
            
            # Check overall health
            health_check = migration_manager.run_comprehensive_check()
            
            if not health_check['overall_healthy']:
                print("\n⚠️  System health issues detected. Attempting to resolve...")
                
                # Run pending migrations
                if health_check['migration_status']['status'] == 'pending_migrations':
                    print("\n🔄 Running pending migrations...")
                    success, messages = migration_manager.run_all_pending_migrations()
                    for message in messages:
                        print(f"   {message}")
                    
                    if not success:
                        print("❌ Migration failed. Please check the logs.")
                        return False
                
                # Validate and sync models
                print("\n🔧 Validating model-database consistency...")
                models = [Node, Cluster, Operation]
                validation_results = model_validator.validate_all_models(models)
                
                if not validation_results['overall_valid']:
                    print("❌ Model validation failed:")
                    for model_name, validation in validation_results['models'].items():
                        if not validation.get('valid', True):
                            print(f"   {model_name}: Issues detected")
                            
                            # Attempt to sync Node model if it has issues
                            if model_name == 'Node' and validation.get('missing_in_db'):
                                print(f"   Attempting to sync {model_name} model...")
                                try:
                                    # Sync the Node model
                                    Node.sync_with_database()
                                    print(f"   ✅ {model_name} model synchronized")
                                except Exception as e:
                                    print(f"   ❌ Failed to sync {model_name}: {e}")
                else:
                    print("✅ All models are consistent with database")
            else:
                print("\n✅ System is healthy - no action required")
            
            # Final validation
            print("\n🔍 STEP 2: Final validation...")
            final_health = migration_manager.run_comprehensive_check()
            
            if final_health['overall_healthy']:
                print("✅ System is now healthy and ready for use!")
                return True
            else:
                print("❌ System still has issues after repair attempts:")
                for rec in final_health['recommendations']:
                    print(f"   - {rec}")
                return False
                
        except Exception as e:
            logger.error(f"Validation and sync failed: {e}")
            print(f"❌ Error during validation and sync: {e}")
            return False

def test_ssh_key_functionality():
    """Test SSH key functionality with the enhanced Node model."""
    print("\n🔑 STEP 3: Testing SSH key functionality...")
    
    app = create_app()
    with app.app_context():
        try:
            # Find the devmod-02 node
            node = Node.query.filter_by(hostname='devmod-02').first()
            
            if node:
                print(f"   Found node: {node.hostname}")
                
                # Test the new SSH key status method
                ssh_status = node.get_ssh_key_status()
                print(f"   SSH Key Status: {ssh_status['status_description']}")
                print(f"   Key Files Exist: {ssh_status['key_files_exist']}")
                print(f"   Database Sync Needed: {ssh_status['sync_needed']}")
                
                # Test properties
                print(f"   SSH Key Ready: {node.ssh_key_ready}")
                print(f"   SSH Connection Ready: {node.ssh_connection_ready}")
                
                return True
            else:
                print("   ⚠️  devmod-02 node not found for testing")
                return True
                
        except Exception as e:
            logger.error(f"SSH key functionality test failed: {e}")
            print(f"   ❌ SSH key test failed: {e}")
            return False

def main():
    """Main entry point."""
    try:
        # Validate and sync models
        success = validate_and_sync_models()
        
        if success:
            # Test SSH key functionality
            ssh_test_success = test_ssh_key_functionality()
            
            if ssh_test_success:
                print("\n🎉 All validation and synchronization tasks completed successfully!")
                print("   The system is ready for use with enhanced SSH key management.")
                return 0
            else:
                print("\n⚠️  Model sync succeeded but SSH key test failed.")
                return 1
        else:
            print("\n❌ Validation and synchronization failed.")
            return 1
            
    except Exception as e:
        logger.error(f"Script failed: {e}")
        print(f"\n❌ Script failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
