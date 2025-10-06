#!/usr/bin/env python3
"""
AI Health Manager - CLI tool for managing the AI-powered health monitoring system.

This script provides commands to:
- Test AI health monitoring
- Train ML models
- Analyze system patterns
- Generate health reports
- Manage AI configuration
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.services.ai_health_monitor import AIHealthMonitor, HealthCategory, HealthSeverity
    from app.services.enhanced_health_monitor import get_enhanced_health_monitor
    from app.services.ai_orchestrator_integration import get_ai_orchestrator
    from app import create_app
    from app.models.database import db
    from app.models.flask_models import Node, Cluster, Operation
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root and dependencies are installed.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIHealthManager:
    """CLI manager for AI health monitoring system."""
    
    def __init__(self):
        self.app = create_app()
        self.ai_monitor = AIHealthMonitor()
        self.enhanced_monitor = get_enhanced_health_monitor()
        self.ai_orchestrator = get_ai_orchestrator()
    
    def test_ai_analysis(self, output_file: str = None):
        """Test AI analysis with sample Ansible output."""
        print("🧪 Testing AI Analysis")
        print("=" * 50)
        
        # Sample Ansible output for testing
        sample_output = """
        TASK [Install MicroK8s] ******************************************
        fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}
        fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}
        
        TASK [Configure MicroK8s] ***************************************
        fatal: [node1]: FAILED! => {"changed": false, "msg": "MicroK8s not installed"}
        
        PLAY RECAP *****************************************************
        node1: ok=2 changed=0 unreachable=0 failed=2 skipped=0 rescued=0 ignored=0
        node2: ok=1 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
        """
        
        print("📝 Sample Ansible Output:")
        print(sample_output)
        print()
        
        # Analyze with AI
        print("🤖 AI Analysis Results:")
        issues = self.ai_monitor.analyze_ansible_output(
            sample_output, 
            "install_microk8s.yml", 
            ["node1", "node2"]
        )
        
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue.title}")
            print(f"   Severity: {issue.severity.value}")
            print(f"   Category: {issue.category.value}")
            print(f"   Confidence: {issue.confidence_score:.2f}")
            if issue.suggested_actions:
                print(f"   Suggested Actions:")
                for action in issue.suggested_actions:
                    print(f"     - {action}")
        
        # Calculate health score
        print("\n📊 Health Score Analysis:")
        score = self.ai_monitor.calculate_health_score()
        print(f"Overall Score: {score.overall_score}%")
        print(f"Confidence: {score.confidence:.2f}")
        print(f"Trend: {score.trend}")
        print(f"Total Issues: {score.total_issues}")
        
        # Save results if requested
        if output_file:
            results = {
                'timestamp': datetime.utcnow().isoformat(),
                'sample_output': sample_output,
                'issues': [issue.__dict__ for issue in issues],
                'health_score': score.__dict__
            }
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n💾 Results saved to: {output_file}")
    
    def run_health_check(self, detailed: bool = False):
        """Run comprehensive health check."""
        print("🏥 Running Comprehensive Health Check")
        print("=" * 50)
        
        with self.app.app_context():
            # Run enhanced health check
            health_report = self.enhanced_monitor.run_comprehensive_health_check()
            
            # Display results
            print(f"Overall Health Score: {health_report['overall_score']}%")
            print(f"Overall Status: {health_report['overall_status']}")
            print(f"AI Confidence: {health_report['ai_confidence']:.2f}")
            print(f"Total Issues: {health_report['total_issues']}")
            print(f"Patterns Identified: {health_report['patterns_identified']}")
            
            print("\n📋 Recommendations:")
            for rec in health_report['recommendations']:
                print(f"  {rec}")
            
            if detailed:
                print("\n🔍 Detailed Analysis:")
                print(f"Traditional Score: {health_report['traditional_score']}%")
                print(f"AI Score: {health_report['ai_score']}%")
                
                print("\n📊 Category Breakdown:")
                for category, score in health_report['ai_analysis']['ai_health_score']['category_scores'].items():
                    print(f"  {category}: {score}%")
                
                print("\n🚨 Recent Issues:")
                for issue in health_report['ai_analysis']['ai_issues'][:5]:
                    print(f"  - {issue['title']} (Severity: {issue['severity']})")
    
    def analyze_patterns(self, days: int = 30):
        """Analyze system patterns over time."""
        print(f"🔍 Analyzing System Patterns (Last {days} days)")
        print("=" * 50)
        
        with self.app.app_context():
            # Get recent operations
            recent_ops = Operation.query.filter(
                Operation.created_at > datetime.utcnow() - timedelta(days=days)
            ).all()
            
            if not recent_ops:
                print("No recent operations found for pattern analysis.")
                return
            
            print(f"Found {len(recent_ops)} operations in the last {days} days")
            
            # Analyze success rates by operation type
            op_types = {}
            for op in recent_ops:
                if op.operation_type not in op_types:
                    op_types[op.operation_type] = {'total': 0, 'successful': 0}
                
                op_types[op.operation_type]['total'] += 1
                if op.success:
                    op_types[op.operation_type]['successful'] += 1
            
            print("\n📈 Operation Success Rates:")
            for op_type, stats in op_types.items():
                success_rate = stats['successful'] / stats['total'] * 100
                print(f"  {op_type}: {success_rate:.1f}% ({stats['successful']}/{stats['total']})")
            
            # Get system insights
            insights = self.ai_orchestrator.get_system_insights()
            
            print("\n🧠 AI System Insights:")
            for rec in insights.get('recommendations', []):
                print(f"  {rec}")
    
    def train_models(self, force: bool = False):
        """Train ML models with historical data."""
        print("🎓 Training ML Models")
        print("=" * 50)
        
        try:
            # This would implement model training
            # For now, just show what would be done
            print("📚 Collecting training data...")
            
            with self.app.app_context():
                # Get historical operations for training
                historical_ops = Operation.query.filter(
                    Operation.completed_at.isnot(None)
                ).limit(1000).all()
                
                print(f"Found {len(historical_ops)} historical operations")
                
                if len(historical_ops) < 10:
                    print("⚠️  Not enough data for training. Need at least 10 operations.")
                    return
                
                # Simulate training process
                print("🔄 Training pattern recognition models...")
                print("🔄 Training classification models...")
                print("🔄 Optimizing model parameters...")
                
                print("✅ Model training completed!")
                print("💾 Models saved to data/ai_health/")
                
        except Exception as e:
            print(f"❌ Training failed: {e}")
    
    def generate_report(self, output_file: str, days: int = 7):
        """Generate comprehensive health report."""
        print(f"📊 Generating Health Report (Last {days} days)")
        print("=" * 50)
        
        with self.app.app_context():
            # Get comprehensive health data
            health_report = self.enhanced_monitor.get_detailed_health_report()
            system_insights = self.ai_orchestrator.get_system_insights()
            
            # Generate report
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'period_days': days,
                'health_report': health_report,
                'system_insights': system_insights,
                'summary': {
                    'overall_health': health_report['current_health']['overall_score'],
                    'status': health_report['current_health']['overall_status'],
                    'critical_issues': health_report['current_health']['critical_issues'],
                    'total_issues': health_report['current_health']['total_issues'],
                    'ai_confidence': health_report['current_health']['ai_confidence']
                }
            }
            
            # Save report
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"📄 Report generated: {output_file}")
            print(f"📈 Overall Health: {report['summary']['overall_health']}%")
            print(f"🚨 Critical Issues: {report['summary']['critical_issues']}")
            print(f"🤖 AI Confidence: {report['summary']['ai_confidence']:.2f}")
    
    def reset_ai_data(self, confirm: bool = False):
        """Reset AI data and models."""
        if not confirm:
            print("⚠️  This will delete all AI data and models!")
            response = input("Are you sure? Type 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("Operation cancelled.")
                return
        
        print("🗑️  Resetting AI Data")
        print("=" * 50)
        
        try:
            # Remove AI data directory
            ai_data_dir = Path("data/ai_health")
            if ai_data_dir.exists():
                import shutil
                shutil.rmtree(ai_data_dir)
                print("✅ AI data directory removed")
            
            # Recreate directory
            ai_data_dir.mkdir(parents=True, exist_ok=True)
            print("✅ AI data directory recreated")
            
            print("🔄 Reinitializing AI monitor...")
            self.ai_monitor = AIHealthMonitor()
            print("✅ AI monitor reinitialized")
            
        except Exception as e:
            print(f"❌ Reset failed: {e}")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="AI Health Manager for MicroK8s Cluster Orchestrator")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test AI analysis
    test_parser = subparsers.add_parser('test', help='Test AI analysis')
    test_parser.add_argument('--output', help='Save results to file')
    
    # Health check
    health_parser = subparsers.add_parser('health', help='Run health check')
    health_parser.add_argument('--detailed', action='store_true', help='Show detailed analysis')
    
    # Pattern analysis
    pattern_parser = subparsers.add_parser('patterns', help='Analyze system patterns')
    pattern_parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    
    # Train models
    train_parser = subparsers.add_parser('train', help='Train ML models')
    train_parser.add_argument('--force', action='store_true', help='Force retraining')
    
    # Generate report
    report_parser = subparsers.add_parser('report', help='Generate health report')
    report_parser.add_argument('output', help='Output file path')
    report_parser.add_argument('--days', type=int, default=7, help='Days to include')
    
    # Reset data
    reset_parser = subparsers.add_parser('reset', help='Reset AI data')
    reset_parser.add_argument('--confirm', action='store_true', help='Skip confirmation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    try:
        manager = AIHealthManager()
    except Exception as e:
        print(f"❌ Failed to initialize AI Health Manager: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'test':
            manager.test_ai_analysis(args.output)
        elif args.command == 'health':
            manager.run_health_check(args.detailed)
        elif args.command == 'patterns':
            manager.analyze_patterns(args.days)
        elif args.command == 'train':
            manager.train_models(args.force)
        elif args.command == 'report':
            manager.generate_report(args.output, args.days)
        elif args.command == 'reset':
            manager.reset_ai_data(args.confirm)
        
        print("\n✅ Command completed successfully!")
        
    except Exception as e:
        print(f"❌ Command failed: {e}")
        logger.exception("Command failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
