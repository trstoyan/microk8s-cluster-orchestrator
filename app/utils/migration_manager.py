#!/usr/bin/env python3
"""
Migration Manager for MicroK8s Cluster Orchestrator.

This module provides a unified interface for managing database migrations.
It automatically detects and applies pending migrations with comprehensive
validation and error handling.
"""

import os
import sys
import sqlite3
import importlib.util
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import model validator for enhanced validation
try:
    from .model_validator import ModelValidator
except ImportError:
    ModelValidator = None

class MigrationManager:
    """Manages database migrations for the MicroK8s Cluster Orchestrator."""
    
    def __init__(self, db_path: str = "cluster_data.db", migrations_dir: str = "migrations"):
        """
        Initialize the Migration Manager.
        
        Args:
            db_path: Path to the SQLite database
            migrations_dir: Directory containing migration scripts
        """
        self.db_path = Path(db_path)
        self.migrations_dir = Path(migrations_dir)
        self.migrations_table = "schema_migrations"
        
        # Initialize model validator if available
        self.model_validator = ModelValidator(str(self.db_path)) if ModelValidator else None
    
    def ensure_migrations_table(self) -> bool:
        """Ensure the migrations tracking table exists."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create migrations table if it doesn't exist
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1
                )
            """)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            return False
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT migration_name FROM {self.migrations_table} 
                WHERE success = 1 
                ORDER BY applied_at
            """)
            
            applied = [row[0] for row in cursor.fetchall()]
            conn.close()
            return applied
            
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def get_available_migrations(self) -> List[Dict[str, str]]:
        """Get list of available migration files."""
        migrations = []
        
        if not self.migrations_dir.exists():
            return migrations
        
        for migration_file in sorted(self.migrations_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue
                
            migrations.append({
                'name': migration_file.stem,
                'path': str(migration_file),
                'filename': migration_file.name
            })
        
        return migrations
    
    def get_pending_migrations(self) -> List[Dict[str, str]]:
        """Get list of pending migrations."""
        applied = self.get_applied_migrations()
        available = self.get_available_migrations()
        
        pending = []
        for migration in available:
            if migration['name'] not in applied:
                pending.append(migration)
        
        return pending
    
    def run_migration(self, migration_path: str, migration_name: str) -> Tuple[bool, str]:
        """
        Run a single migration.
        
        Args:
            migration_path: Path to the migration script
            migration_name: Name of the migration
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Load the migration module
            spec = importlib.util.spec_from_file_location(migration_name, migration_path)
            migration_module = importlib.util.module_from_spec(spec)
            
            # Add the project root to sys.path for imports
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            spec.loader.exec_module(migration_module)
            
            # Check if the migration has a run_migration function
            if hasattr(migration_module, 'run_migration'):
                success = migration_module.run_migration()
                message = f"Migration '{migration_name}' completed successfully"
            else:
                # Fallback: try to run the migration as a script
                import subprocess
                result = subprocess.run([
                    sys.executable, migration_path
                ], capture_output=True, text=True, cwd=project_root)
                
                success = result.returncode == 0
                message = f"Migration '{migration_name}' {'completed successfully' if success else 'failed'}"
                if result.stdout:
                    message += f"\nOutput: {result.stdout}"
                if result.stderr:
                    message += f"\nError: {result.stderr}"
            
            # Record the migration result
            self.record_migration(migration_name, success)
            
            return success, message
            
        except Exception as e:
            error_msg = f"Failed to run migration '{migration_name}': {str(e)}"
            logger.error(error_msg)
            self.record_migration(migration_name, False)
            return False, error_msg
    
    def record_migration(self, migration_name: str, success: bool):
        """Record a migration result in the database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO {self.migrations_table} 
                (migration_name, success) VALUES (?, ?)
            """, (migration_name, success))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record migration '{migration_name}': {e}")
    
    def run_all_pending_migrations(self, dry_run: bool = False) -> Tuple[bool, List[str]]:
        """
        Run all pending migrations.
        
        Args:
            dry_run: If True, only show what would be run without executing
            
        Returns:
            Tuple of (all_successful, messages)
        """
        if not self.db_path.exists():
            return False, ["Database file not found. Please initialize the system first."]
        
        # Ensure migrations table exists
        if not self.ensure_migrations_table():
            return False, ["Failed to create migrations tracking table."]
        
        pending = self.get_pending_migrations()
        
        if not pending:
            return True, ["No pending migrations found. Database is up to date."]
        
        messages = []
        all_successful = True
        
        if dry_run:
            messages.append(f"DRY RUN: {len(pending)} pending migrations found:")
            for migration in pending:
                messages.append(f"  - {migration['name']}")
            return True, messages
        
        messages.append(f"Found {len(pending)} pending migrations. Applying...")
        
        for migration in pending:
            messages.append(f"Running migration: {migration['name']}")
            success, message = self.run_migration(migration['path'], migration['name'])
            messages.append(f"  {message}")
            
            if not success:
                all_successful = False
                messages.append(f"Migration failed. Stopping migration process.")
                break
        
        if all_successful:
            messages.append("All migrations completed successfully!")
        else:
            messages.append("Some migrations failed. Check the logs for details.")
        
        return all_successful, messages
    
    def get_migration_status(self) -> Dict[str, any]:
        """Get current migration status."""
        if not self.db_path.exists():
            return {
                'database_exists': False,
                'migrations_table_exists': False,
                'applied_migrations': [],
                'pending_migrations': [],
                'total_migrations': 0,
                'status': 'database_not_found'
            }
        
        # Ensure migrations table exists
        self.ensure_migrations_table()
        
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        available = self.get_available_migrations()
        
        return {
            'database_exists': True,
            'migrations_table_exists': True,
            'applied_migrations': applied,
            'pending_migrations': [m['name'] for m in pending],
            'total_migrations': len(available),
            'status': 'up_to_date' if not pending else 'pending_migrations'
        }
    
    def validate_model_consistency(self) -> Dict[str, any]:
        """
        Validate that all models are consistent with the database schema.
        
        Returns:
            Dict with validation results
        """
        if not self.model_validator:
            return {
                'valid': False,
                'error': 'Model validator not available',
                'models': {}
            }
        
        try:
            # Import models
            from app.models.flask_models import Node, Cluster, Operation
            models = [Node, Cluster, Operation]
            
            return self.model_validator.validate_all_models(models)
            
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'models': {}
            }
    
    def run_comprehensive_check(self) -> Dict[str, any]:
        """
        Run a comprehensive check of migrations and model consistency.
        
        Returns:
            Dict with comprehensive status information
        """
        migration_status = self.get_migration_status()
        model_validation = self.validate_model_consistency()
        
        # Determine overall health
        migration_healthy = migration_status['status'] == 'up_to_date'
        model_healthy = model_validation.get('valid', False)
        overall_healthy = migration_healthy and model_healthy
        
        return {
            'overall_healthy': overall_healthy,
            'migration_status': migration_status,
            'model_validation': model_validation,
            'recommendations': self._generate_recommendations(migration_status, model_validation)
        }
    
    def _generate_recommendations(self, migration_status: Dict, model_validation: Dict) -> List[str]:
        """Generate recommendations based on current status."""
        recommendations = []
        
        # Migration recommendations
        if migration_status['status'] == 'pending_migrations':
            recommendations.append("Run pending migrations to update database schema")
        
        if migration_status['status'] == 'database_not_found':
            recommendations.append("Initialize database by running the application")
        
        # Model validation recommendations
        if not model_validation.get('valid', True):
            recommendations.append("Model-database schema mismatch detected")
            
            for model_name, validation in model_validation.get('models', {}).items():
                if not validation.get('valid', True):
                    if validation.get('missing_in_db'):
                        recommendations.append(f"Add missing columns to {model_name} table in database")
                    if validation.get('missing_in_model'):
                        recommendations.append(f"Add missing attributes to {model_name} model")
        
        if not recommendations:
            recommendations.append("System is healthy - no action required")
        
        return recommendations
    
    def create_health_report(self) -> str:
        """
        Create a comprehensive health report.
        
        Returns:
            Formatted health report string
        """
        check_results = self.run_comprehensive_check()
        
        report = []
        report.append("=" * 80)
        report.append("MICROK8S CLUSTER ORCHESTRATOR - SYSTEM HEALTH REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall status
        status_icon = "✅" if check_results['overall_healthy'] else "❌"
        report.append(f"OVERALL STATUS: {status_icon} {'HEALTHY' if check_results['overall_healthy'] else 'NEEDS ATTENTION'}")
        report.append("")
        
        # Migration status
        migration_status = check_results['migration_status']
        report.append("MIGRATION STATUS:")
        report.append(f"  Database exists: {'✅' if migration_status['database_exists'] else '❌'}")
        report.append(f"  Migrations table: {'✅' if migration_status['migrations_table_exists'] else '❌'}")
        report.append(f"  Applied migrations: {len(migration_status['applied_migrations'])}")
        report.append(f"  Pending migrations: {len(migration_status['pending_migrations'])}")
        report.append(f"  Status: {migration_status['status']}")
        report.append("")
        
        # Model validation
        model_validation = check_results['model_validation']
        if model_validation.get('valid') is not None:
            report.append("MODEL VALIDATION:")
            report.append(f"  Overall valid: {'✅' if model_validation['valid'] else '❌'}")
            
            if model_validation.get('models'):
                for model_name, validation in model_validation['models'].items():
                    status_icon = "✅" if validation.get('valid', False) else "❌"
                    report.append(f"  {model_name}: {status_icon}")
            
            if not model_validation.get('valid', True):
                report.append("  Issues detected - see detailed validation report")
        else:
            report.append("MODEL VALIDATION: ⚠️ Not available")
        
        report.append("")
        
        # Recommendations
        recommendations = check_results['recommendations']
        report.append("RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            report.append(f"  {i}. {rec}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MicroK8s Cluster Orchestrator Migration Manager")
    parser.add_argument("--db-path", default="cluster_data.db", help="Path to database file")
    parser.add_argument("--migrations-dir", default="migrations", help="Migrations directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be run without executing")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--health", action="store_true", help="Run comprehensive health check")
    parser.add_argument("--validate-models", action="store_true", help="Validate model-database consistency")
    
    args = parser.parse_args()
    
    manager = MigrationManager(args.db_path, args.migrations_dir)
    
    if args.health:
        # Run comprehensive health check
        report = manager.create_health_report()
        print(report)
        
        # Exit with error code if unhealthy
        check_results = manager.run_comprehensive_check()
        sys.exit(0 if check_results['overall_healthy'] else 1)
        
    elif args.validate_models:
        # Validate model consistency
        validation = manager.validate_model_consistency()
        if validation.get('valid'):
            print("✅ All models are consistent with database schema")
        else:
            print("❌ Model-database consistency issues detected:")
            if validation.get('error'):
                print(f"   Error: {validation['error']}")
            
            for model_name, model_validation in validation.get('models', {}).items():
                if not model_validation.get('valid', True):
                    print(f"   {model_name}: Issues detected")
                    if model_validation.get('missing_in_db'):
                        print(f"     Missing in DB: {', '.join(model_validation['missing_in_db'])}")
                    if model_validation.get('missing_in_model'):
                        print(f"     Missing in Model: {', '.join(model_validation['missing_in_model'])}")
        
        sys.exit(0 if validation.get('valid', False) else 1)
        
    elif args.status:
        status = manager.get_migration_status()
        print("Migration Status:")
        print(f"  Database exists: {status['database_exists']}")
        print(f"  Migrations table exists: {status['migrations_table_exists']}")
        print(f"  Applied migrations: {len(status['applied_migrations'])}")
        print(f"  Pending migrations: {len(status['pending_migrations'])}")
        print(f"  Total migrations: {status['total_migrations']}")
        print(f"  Status: {status['status']}")
        
        if status['applied_migrations']:
            print("\nApplied migrations:")
            for migration in status['applied_migrations']:
                print(f"  ✓ {migration}")
        
        if status['pending_migrations']:
            print("\nPending migrations:")
            for migration in status['pending_migrations']:
                print(f"  ⏳ {migration}")
    else:
        success, messages = manager.run_all_pending_migrations(args.dry_run)
        
        for message in messages:
            print(message)
        
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
