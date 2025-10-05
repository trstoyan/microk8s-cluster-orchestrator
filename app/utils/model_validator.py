#!/usr/bin/env python3
"""
Model Validator for MicroK8s Cluster Orchestrator.

This module provides comprehensive validation and synchronization tools
for ensuring model-database consistency.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class ModelValidator:
    """Validates and synchronizes SQLAlchemy models with database schema."""
    
    def __init__(self, db_path: str = "cluster_data.db"):
        """
        Initialize the Model Validator.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = Path(db_path)
    
    def validate_model_consistency(self, model_class, table_name: str = None) -> Dict[str, Any]:
        """
        Validate that a SQLAlchemy model matches the database schema.
        
        Args:
            model_class: SQLAlchemy model class
            table_name: Optional table name override
            
        Returns:
            Dict with validation results
        """
        try:
            if not self.db_path.exists():
                return {
                    'valid': False,
                    'error': 'Database file not found',
                    'table_name': table_name or model_class.__tablename__,
                    'details': {}
                }
            
            table_name = table_name or model_class.__tablename__
            
            # Get database schema
            db_columns = self._get_database_schema(table_name)
            if not db_columns:
                return {
                    'valid': False,
                    'error': f'Table {table_name} not found in database',
                    'table_name': table_name,
                    'details': {}
                }
            
            # Get model schema
            model_columns = self._get_model_schema(model_class)
            
            # Compare schemas
            validation_result = self._compare_schemas(model_columns, db_columns)
            validation_result['table_name'] = table_name
            validation_result['model_class'] = model_class.__name__
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'table_name': table_name or model_class.__tablename__,
                'details': {}
            }
    
    def _get_database_schema(self, table_name: str) -> Dict[str, Dict[str, Any]]:
        """Get database schema for a table."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema = {}
            for col in columns:
                col_id, name, col_type, not_null, default, pk = col
                schema[name] = {
                    'type': col_type,
                    'nullable': not not_null,
                    'default': default,
                    'primary_key': bool(pk)
                }
            
            conn.close()
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get database schema: {e}")
            return {}
    
    def _get_model_schema(self, model_class) -> Dict[str, Dict[str, Any]]:
        """Get model schema from SQLAlchemy model."""
        try:
            schema = {}
            for column in model_class.__table__.columns:
                schema[column.name] = {
                    'type': str(column.type),
                    'nullable': column.nullable,
                    'default': column.default.arg if column.default else None,
                    'primary_key': column.primary_key
                }
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get model schema: {e}")
            return {}
    
    def _compare_schemas(self, model_schema: Dict, db_schema: Dict) -> Dict[str, Any]:
        """Compare model schema with database schema."""
        model_columns = set(model_schema.keys())
        db_columns = set(db_schema.keys())
        
        # Find differences
        missing_in_db = model_columns - db_columns
        missing_in_model = db_columns - model_columns
        common_columns = model_columns & db_columns
        
        # Check for type mismatches
        type_mismatches = []
        for col_name in common_columns:
            model_type = str(model_schema[col_name]['type']).lower()
            db_type = str(db_schema[col_name]['type']).lower()
            
            if not self._types_compatible(model_type, db_type):
                type_mismatches.append({
                    'column': col_name,
                    'model_type': model_type,
                    'db_type': db_type
                })
        
        # Check for nullable mismatches
        nullable_mismatches = []
        for col_name in common_columns:
            model_nullable = model_schema[col_name]['nullable']
            db_nullable = db_schema[col_name]['nullable']
            
            if model_nullable != db_nullable:
                nullable_mismatches.append({
                    'column': col_name,
                    'model_nullable': model_nullable,
                    'db_nullable': db_nullable
                })
        
        is_valid = (len(missing_in_db) == 0 and 
                   len(missing_in_model) == 0 and 
                   len(type_mismatches) == 0 and
                   len(nullable_mismatches) == 0)
        
        return {
            'valid': is_valid,
            'missing_in_db': list(missing_in_db),
            'missing_in_model': list(missing_in_model),
            'type_mismatches': type_mismatches,
            'nullable_mismatches': nullable_mismatches,
            'details': {
                'model_columns': len(model_schema),
                'db_columns': len(db_schema),
                'common_columns': len(common_columns),
                'total_differences': len(missing_in_db) + len(missing_in_model) + len(type_mismatches) + len(nullable_mismatches)
            }
        }
    
    def _types_compatible(self, model_type: str, db_type: str) -> bool:
        """Check if two SQL types are compatible."""
        # Normalize types for comparison
        type_mappings = {
            'boolean': ['boolean', 'bool', 'tinyint'],
            'integer': ['integer', 'int', 'bigint', 'smallint'],
            'varchar': ['varchar', 'char', 'text'],
            'text': ['text', 'varchar', 'char'],
            'datetime': ['datetime', 'timestamp'],
            'float': ['float', 'real', 'double']
        }
        
        for compatible_types in type_mappings.values():
            if model_type in compatible_types and db_type in compatible_types:
                return True
        
        return model_type == db_type
    
    def generate_migration_sql(self, model_class, table_name: str = None) -> List[str]:
        """
        Generate SQL statements to synchronize database with model.
        
        Args:
            model_class: SQLAlchemy model class
            table_name: Optional table name override
            
        Returns:
            List of SQL statements
        """
        try:
            validation = self.validate_model_consistency(model_class, table_name)
            if validation['valid']:
                return []
            
            table_name = table_name or model_class.__tablename__
            sql_statements = []
            
            # Add missing columns
            for col_name in validation['missing_in_db']:
                model_schema = self._get_model_schema(model_class)
                col_info = model_schema[col_name]
                
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_info['type']}"
                if not col_info['nullable']:
                    sql += " NOT NULL"
                if col_info['default'] is not None:
                    sql += f" DEFAULT {col_info['default']}"
                
                sql_statements.append(sql)
            
            return sql_statements
            
        except Exception as e:
            logger.error(f"Failed to generate migration SQL: {e}")
            return []
    
    def validate_all_models(self, models: List) -> Dict[str, Any]:
        """
        Validate multiple models at once.
        
        Args:
            models: List of SQLAlchemy model classes
            
        Returns:
            Dict with validation results for all models
        """
        results = {
            'overall_valid': True,
            'models': {},
            'summary': {
                'total_models': len(models),
                'valid_models': 0,
                'invalid_models': 0
            }
        }
        
        for model in models:
            model_name = model.__name__
            validation = self.validate_model_consistency(model)
            
            results['models'][model_name] = validation
            
            if validation['valid']:
                results['summary']['valid_models'] += 1
            else:
                results['summary']['invalid_models'] += 1
                results['overall_valid'] = False
        
        return results
    
    def create_model_sync_report(self, models: List) -> str:
        """
        Create a comprehensive report of model-database synchronization status.
        
        Args:
            models: List of SQLAlchemy model classes
            
        Returns:
            Formatted report string
        """
        validation_results = self.validate_all_models(models)
        
        report = []
        report.append("=" * 80)
        report.append("MODEL-DATABASE SYNCHRONIZATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        summary = validation_results['summary']
        report.append(f"SUMMARY:")
        report.append(f"  Total Models: {summary['total_models']}")
        report.append(f"  Valid Models: {summary['valid_models']}")
        report.append(f"  Invalid Models: {summary['invalid_models']}")
        report.append(f"  Overall Status: {'✅ VALID' if validation_results['overall_valid'] else '❌ INVALID'}")
        report.append("")
        
        # Detailed results
        for model_name, validation in validation_results['models'].items():
            report.append(f"MODEL: {model_name}")
            report.append("-" * 40)
            
            if validation['valid']:
                report.append("✅ Schema is valid and synchronized")
            else:
                report.append("❌ Schema validation failed")
                
                if validation.get('error'):
                    report.append(f"   Error: {validation['error']}")
                
                if validation.get('missing_in_db'):
                    report.append(f"   Missing in DB: {', '.join(validation['missing_in_db'])}")
                
                if validation.get('missing_in_model'):
                    report.append(f"   Missing in Model: {', '.join(validation['missing_in_model'])}")
                
                if validation.get('type_mismatches'):
                    for mismatch in validation['type_mismatches']:
                        report.append(f"   Type Mismatch - {mismatch['column']}: Model={mismatch['model_type']}, DB={mismatch['db_type']}")
                
                if validation.get('nullable_mismatches'):
                    for mismatch in validation['nullable_mismatches']:
                        report.append(f"   Nullable Mismatch - {mismatch['column']}: Model={mismatch['model_nullable']}, DB={mismatch['db_nullable']}")
            
            report.append("")
        
        return "\n".join(report)

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Validator for MicroK8s Cluster Orchestrator")
    parser.add_argument("--db-path", default="cluster_data.db", help="Path to database file")
    parser.add_argument("--model", help="Specific model to validate")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    
    args = parser.parse_args()
    
    validator = ModelValidator(args.db_path)
    
    if args.model:
        # Validate specific model
        try:
            # Import the model
            from app.models.flask_models import Node, Cluster, Operation
            models = {'Node': Node, 'Cluster': Cluster, 'Operation': Operation}
            
            if args.model in models:
                validation = validator.validate_model_consistency(models[args.model])
                print(f"Validation result for {args.model}:")
                print(f"  Valid: {validation['valid']}")
                if not validation['valid']:
                    print(f"  Error: {validation.get('error', 'Unknown error')}")
            else:
                print(f"Model {args.model} not found. Available models: {list(models.keys())}")
        except Exception as e:
            print(f"Error validating model: {e}")
    else:
        # Validate all models
        try:
            from app.models.flask_models import Node, Cluster, Operation
            models = [Node, Cluster, Operation]
            
            if args.report:
                report = validator.create_model_sync_report(models)
                print(report)
            else:
                results = validator.validate_all_models(models)
                print(f"Overall validation: {'✅ VALID' if results['overall_valid'] else '❌ INVALID'}")
                for model_name, validation in results['models'].items():
                    status = "✅" if validation['valid'] else "❌"
                    print(f"  {status} {model_name}")
        except Exception as e:
            print(f"Error validating models: {e}")

if __name__ == "__main__":
    main()
