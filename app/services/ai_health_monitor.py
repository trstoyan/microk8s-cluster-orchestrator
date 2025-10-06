"""
AI-Powered Health Monitoring System for MicroK8s Cluster Orchestrator.

This system uses machine learning and small LLMs to:
1. Parse and understand Ansible output intelligently
2. Build a knowledge base of system patterns and solutions
3. Provide accurate health scoring with detailed insights
4. Learn from past issues to improve future predictions
5. Use reinforcement learning to optimize system performance
"""

import os
import json
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import pickle
from pathlib import Path

# AI/ML imports
try:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML libraries not available. AI features will be limited.")

# Small LLM integration (using lightweight models)
try:
    # For production, you could use:
    # - Ollama with small models (llama3.2:1b, phi3:mini)
    # - Hugging Face transformers with quantized models
    # - OpenAI API for GPT-3.5-turbo (cost-effective)
    import requests
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

class HealthSeverity(Enum):
    """Health issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class HealthCategory(Enum):
    """Health check categories."""
    SYSTEM = "system"
    NETWORK = "network"
    STORAGE = "storage"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    DEPENDENCIES = "dependencies"
    ANSIBLE = "ansible"

@dataclass
class HealthIssue:
    """Represents a health issue with AI-generated insights."""
    id: str
    category: HealthCategory
    severity: HealthSeverity
    title: str
    description: str
    affected_components: List[str]
    ansible_output: Optional[str] = None
    suggested_actions: List[str] = None
    confidence_score: float = 0.0
    pattern_id: Optional[str] = None
    first_seen: datetime = None
    last_seen: datetime = None
    frequency: int = 1
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.first_seen is None:
            self.first_seen = datetime.utcnow()
        if self.last_seen is None:
            self.last_seen = datetime.utcnow()
        if self.suggested_actions is None:
            self.suggested_actions = []

@dataclass
class HealthScore:
    """Comprehensive health score with breakdown."""
    overall_score: float  # 0-100
    category_scores: Dict[HealthCategory, float]
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    total_issues: int
    confidence: float
    last_updated: datetime
    trend: str  # "improving", "stable", "degrading"
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

class AnsibleOutputParser:
    """AI-powered Ansible output parser using small LLMs."""
    
    def __init__(self, llm_endpoint: str = None):
        self.llm_endpoint = llm_endpoint or os.getenv('LLM_ENDPOINT', 'http://localhost:11434/api/generate')
        self.llm_model = os.getenv('LLM_MODEL', 'llama3.2:1b')
        
    def parse_ansible_output(self, output: str, playbook_name: str = None) -> Dict[str, Any]:
        """
        Parse Ansible output using AI to extract meaningful information.
        
        Args:
            output: Raw Ansible output
            playbook_name: Name of the playbook that generated this output
            
        Returns:
            Dictionary with parsed information
        """
        if not LLM_AVAILABLE:
            return self._fallback_parse(output)
        
        try:
            # Prepare prompt for small LLM
            prompt = self._create_analysis_prompt(output, playbook_name)
            
            # Call LLM (using Ollama as example)
            response = self._call_llm(prompt)
            
            # Parse LLM response
            return self._parse_llm_response(response)
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return self._fallback_parse(output)
    
    def _create_analysis_prompt(self, output: str, playbook_name: str) -> str:
        """Create a prompt for the LLM to analyze Ansible output."""
        return f"""
Analyze this Ansible playbook output and extract key information:

Playbook: {playbook_name or 'Unknown'}
Output:
{output[:2000]}  # Limit to avoid token limits

Please provide a JSON response with:
1. success: boolean (was the playbook successful?)
2. failed_tasks: list of failed task names
3. error_messages: list of error messages
4. warnings: list of warning messages
5. affected_hosts: list of affected hostnames
6. severity: "critical", "high", "medium", "low" (overall severity)
7. suggested_actions: list of suggested actions to fix issues
8. confidence: float 0-1 (confidence in analysis)

Focus on actionable insights and specific error patterns.
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        if not self.llm_endpoint:
            raise Exception("No LLM endpoint configured")
        
        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        response = requests.post(self.llm_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json().get('response', '')
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM's JSON response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in LLM response")
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {"success": False, "error": str(e)}
    
    def _fallback_parse(self, output: str) -> Dict[str, Any]:
        """Fallback parsing when LLM is not available."""
        result = {
            "success": True,
            "failed_tasks": [],
            "error_messages": [],
            "warnings": [],
            "affected_hosts": [],
            "severity": "low",
            "suggested_actions": [],
            "confidence": 0.3
        }
        
        # Basic pattern matching
        if "FAILED" in output or "ERROR" in output:
            result["success"] = False
            result["severity"] = "high"
            
            # Extract failed tasks
            failed_matches = re.findall(r'fatal:.*?=> (.*?)\n', output, re.IGNORECASE)
            result["failed_tasks"] = failed_matches[:5]  # Limit to 5
            
            # Extract error messages
            error_matches = re.findall(r'ERROR: (.*?)\n', output, re.IGNORECASE)
            result["error_messages"] = error_matches[:3]  # Limit to 3
        
        if "WARNING" in output:
            warning_matches = re.findall(r'WARNING: (.*?)\n', output, re.IGNORECASE)
            result["warnings"] = warning_matches[:3]
        
        return result

class PatternRecognizer:
    """ML-based pattern recognition for system issues."""
    
    def __init__(self, data_dir: str = "data/ai_health"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.vectorizer = None
        self.clusterer = None
        self.classifier = None
        self.patterns_db = self.data_dir / "patterns.db"
        
        if ML_AVAILABLE:
            self._initialize_ml_components()
    
    def _initialize_ml_components(self):
        """Initialize ML components."""
        try:
            # Load or create vectorizer
            vectorizer_path = self.data_dir / "vectorizer.pkl"
            if vectorizer_path.exists():
                self.vectorizer = joblib.load(vectorizer_path)
            else:
                self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            
            # Load or create clusterer
            clusterer_path = self.data_dir / "clusterer.pkl"
            if clusterer_path.exists():
                self.clusterer = joblib.load(clusterer_path)
            else:
                self.clusterer = KMeans(n_clusters=10, random_state=42)
            
            # Load or create classifier
            classifier_path = self.data_dir / "classifier.pkl"
            if classifier_path.exists():
                self.classifier = joblib.load(classifier_path)
            else:
                self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
                
        except Exception as e:
            logger.error(f"Failed to initialize ML components: {e}")
    
    def analyze_pattern(self, issue: HealthIssue) -> Optional[str]:
        """
        Analyze an issue to find similar patterns.
        
        Returns:
            Pattern ID if a similar pattern is found, None otherwise
        """
        if not ML_AVAILABLE or not self.vectorizer:
            return None
        
        try:
            # Create feature vector from issue
            text_features = f"{issue.title} {issue.description} {' '.join(issue.affected_components)}"
            
            if issue.ansible_output:
                text_features += f" {issue.ansible_output[:500]}"
            
            # Vectorize
            vector = self.vectorizer.transform([text_features])
            
            # Find cluster
            cluster = self.clusterer.predict(vector)[0]
            
            # Check if this cluster has been seen before
            pattern_id = self._get_pattern_id(cluster, issue)
            
            return pattern_id
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return None
    
    def _get_pattern_id(self, cluster: int, issue: HealthIssue) -> Optional[str]:
        """Get or create pattern ID for a cluster."""
        try:
            conn = sqlite3.connect(str(self.patterns_db))
            cursor = conn.cursor()
            
            # Create patterns table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    cluster_id INTEGER,
                    title TEXT,
                    description TEXT,
                    category TEXT,
                    severity TEXT,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    frequency INTEGER,
                    resolution TEXT
                )
            """)
            
            # Check if pattern exists for this cluster
            cursor.execute("""
                SELECT id, frequency FROM patterns 
                WHERE cluster_id = ? AND category = ? AND severity = ?
            """, (cluster, issue.category.value, issue.severity.value))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing pattern
                pattern_id, frequency = result
                cursor.execute("""
                    UPDATE patterns 
                    SET last_seen = ?, frequency = frequency + 1
                    WHERE id = ?
                """, (datetime.utcnow(), pattern_id))
                conn.commit()
                conn.close()
                return pattern_id
            else:
                # Create new pattern
                pattern_id = f"pattern_{cluster}_{issue.category.value}_{int(datetime.utcnow().timestamp())}"
                cursor.execute("""
                    INSERT INTO patterns (id, cluster_id, title, description, category, severity, first_seen, last_seen, frequency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pattern_id, cluster, issue.title, issue.description, issue.category.value, 
                      issue.severity.value, issue.first_seen, issue.last_seen, 1))
                conn.commit()
                conn.close()
                return pattern_id
                
        except Exception as e:
            logger.error(f"Failed to get pattern ID: {e}")
            return None
    
    def get_pattern_suggestions(self, pattern_id: str) -> List[str]:
        """Get suggested actions for a pattern."""
        try:
            conn = sqlite3.connect(str(self.patterns_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT resolution FROM patterns WHERE id = ?", (pattern_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return result[0].split('|')  # Actions separated by |
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get pattern suggestions: {e}")
            return []

class AIHealthMonitor:
    """Main AI-powered health monitoring system."""
    
    def __init__(self, db_path: str = "cluster_data.db"):
        self.db_path = Path(db_path)
        self.ansible_parser = AnsibleOutputParser()
        self.pattern_recognizer = PatternRecognizer()
        self.issues_db = Path("data/ai_health/issues.db")
        self.issues_db.parent.mkdir(parents=True, exist_ok=True)
        
        self._initialize_databases()
    
    def _initialize_databases(self):
        """Initialize the issues database."""
        try:
            conn = sqlite3.connect(str(self.issues_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_issues (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    severity TEXT,
                    title TEXT,
                    description TEXT,
                    affected_components TEXT,
                    ansible_output TEXT,
                    suggested_actions TEXT,
                    confidence_score REAL,
                    pattern_id TEXT,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    frequency INTEGER,
                    resolved BOOLEAN,
                    resolution_notes TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    overall_score REAL,
                    category_scores TEXT,
                    critical_issues INTEGER,
                    high_issues INTEGER,
                    medium_issues INTEGER,
                    low_issues INTEGER,
                    total_issues INTEGER,
                    confidence REAL,
                    trend TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize databases: {e}")
    
    def analyze_ansible_output(self, output: str, playbook_name: str = None, 
                             affected_hosts: List[str] = None) -> List[HealthIssue]:
        """
        Analyze Ansible output and create health issues.
        
        Args:
            output: Raw Ansible output
            playbook_name: Name of the playbook
            affected_hosts: List of affected hostnames
            
        Returns:
            List of HealthIssue objects
        """
        issues = []
        
        # Parse output with AI
        parsed = self.ansible_parser.parse_ansible_output(output, playbook_name)
        
        if not parsed.get('success', True):
            # Create main issue
            issue = HealthIssue(
                id=self._generate_issue_id(output, playbook_name),
                category=HealthCategory.ANSIBLE,
                severity=HealthSeverity(parsed.get('severity', 'medium')),
                title=f"Ansible Playbook Failed: {playbook_name or 'Unknown'}",
                description=f"Playbook execution failed with {len(parsed.get('failed_tasks', []))} failed tasks",
                affected_components=affected_hosts or parsed.get('affected_hosts', []),
                ansible_output=output[:1000],  # Limit size
                suggested_actions=parsed.get('suggested_actions', []),
                confidence_score=parsed.get('confidence', 0.5)
            )
            
            # Analyze pattern
            pattern_id = self.pattern_recognizer.analyze_pattern(issue)
            if pattern_id:
                issue.pattern_id = pattern_id
                # Add pattern-based suggestions
                pattern_suggestions = self.pattern_recognizer.get_pattern_suggestions(pattern_id)
                issue.suggested_actions.extend(pattern_suggestions)
            
            issues.append(issue)
            
            # Create sub-issues for specific failures
            for i, task in enumerate(parsed.get('failed_tasks', [])[:3]):  # Limit to 3
                sub_issue = HealthIssue(
                    id=f"{issue.id}_task_{i}",
                    category=HealthCategory.ANSIBLE,
                    severity=HealthSeverity.HIGH,
                    title=f"Failed Task: {task}",
                    description=f"Task '{task}' failed during playbook execution",
                    affected_components=affected_hosts or [],
                    confidence_score=parsed.get('confidence', 0.5) * 0.8
                )
                issues.append(sub_issue)
        
        # Store issues
        for issue in issues:
            self._store_issue(issue)
        
        return issues
    
    def calculate_health_score(self) -> HealthScore:
        """
        Calculate comprehensive health score using AI analysis.
        
        Returns:
            HealthScore object with detailed breakdown
        """
        try:
            # Get recent issues (last 24 hours)
            recent_issues = self._get_recent_issues(hours=24)
            
            # Calculate category scores
            category_scores = {}
            for category in HealthCategory:
                category_issues = [i for i in recent_issues if i.category == category]
                category_scores[category] = self._calculate_category_score(category_issues)
            
            # Calculate overall score (weighted average)
            weights = {
                HealthCategory.SYSTEM: 0.25,
                HealthCategory.NETWORK: 0.20,
                HealthCategory.SECURITY: 0.20,
                HealthCategory.PERFORMANCE: 0.15,
                HealthCategory.ANSIBLE: 0.10,
                HealthCategory.STORAGE: 0.05,
                HealthCategory.CONFIGURATION: 0.03,
                HealthCategory.DEPENDENCIES: 0.02
            }
            
            overall_score = sum(
                category_scores[cat] * weights.get(cat, 0.1)
                for cat in category_scores
            )
            
            # Count issues by severity
            severity_counts = {
                HealthSeverity.CRITICAL: len([i for i in recent_issues if i.severity == HealthSeverity.CRITICAL]),
                HealthSeverity.HIGH: len([i for i in recent_issues if i.severity == HealthSeverity.HIGH]),
                HealthSeverity.MEDIUM: len([i for i in recent_issues if i.severity == HealthSeverity.MEDIUM]),
                HealthSeverity.LOW: len([i for i in recent_issues if i.severity == HealthSeverity.LOW])
            }
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(recent_issues)
            
            # Determine trend
            trend = self._calculate_trend()
            
            score = HealthScore(
                overall_score=round(overall_score, 2),
                category_scores={k: round(v, 2) for k, v in category_scores.items()},
                critical_issues=severity_counts[HealthSeverity.CRITICAL],
                high_issues=severity_counts[HealthSeverity.HIGH],
                medium_issues=severity_counts[HealthSeverity.MEDIUM],
                low_issues=severity_counts[HealthSeverity.LOW],
                total_issues=len(recent_issues),
                confidence=confidence,
                trend=trend
            )
            
            # Store score
            self._store_health_score(score)
            
            return score
            
        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}")
            # Return default score
            return HealthScore(
                overall_score=50.0,
                category_scores={},
                critical_issues=0,
                high_issues=0,
                medium_issues=0,
                low_issues=0,
                total_issues=0,
                confidence=0.0,
                trend="unknown"
            )
    
    def _calculate_category_score(self, issues: List[HealthIssue]) -> float:
        """Calculate health score for a specific category."""
        if not issues:
            return 100.0
        
        # Weight issues by severity
        severity_weights = {
            HealthSeverity.CRITICAL: 0.0,
            HealthSeverity.HIGH: 25.0,
            HealthSeverity.MEDIUM: 50.0,
            HealthSeverity.LOW: 75.0,
            HealthSeverity.INFO: 90.0
        }
        
        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        
        for issue in issues:
            weight = severity_weights.get(issue.severity, 50.0)
            confidence = issue.confidence_score
            
            total_weight += confidence
            weighted_sum += weight * confidence
        
        if total_weight == 0:
            return 50.0
        
        return max(0.0, min(100.0, weighted_sum / total_weight))
    
    def _calculate_confidence(self, issues: List[HealthIssue]) -> float:
        """Calculate confidence in the health assessment."""
        if not issues:
            return 0.5  # Low confidence when no data
        
        # Average confidence of issues
        avg_confidence = sum(i.confidence_score for i in issues) / len(issues)
        
        # Boost confidence if we have pattern recognition
        pattern_boost = sum(0.1 for i in issues if i.pattern_id) / len(issues)
        
        return min(1.0, avg_confidence + pattern_boost)
    
    def _calculate_trend(self) -> str:
        """Calculate health trend over time."""
        try:
            # Get scores from last 7 days
            conn = sqlite3.connect(str(self.issues_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT overall_score FROM health_scores 
                WHERE timestamp > datetime('now', '-7 days')
                ORDER BY timestamp
            """)
            
            scores = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if len(scores) < 2:
                return "stable"
            
            # Simple trend calculation
            recent_avg = sum(scores[-3:]) / min(3, len(scores))
            older_avg = sum(scores[:-3]) / max(1, len(scores) - 3)
            
            diff = recent_avg - older_avg
            
            if diff > 5:
                return "improving"
            elif diff < -5:
                return "degrading"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"Failed to calculate trend: {e}")
            return "unknown"
    
    def _generate_issue_id(self, output: str, playbook_name: str) -> str:
        """Generate unique issue ID."""
        content = f"{playbook_name}_{output[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _store_issue(self, issue: HealthIssue):
        """Store issue in database."""
        try:
            conn = sqlite3.connect(str(self.issues_db))
            cursor = conn.cursor()
            
            # Check if issue already exists
            cursor.execute("SELECT id FROM health_issues WHERE id = ?", (issue.id,))
            if cursor.fetchone():
                # Update existing issue
                cursor.execute("""
                    UPDATE health_issues 
                    SET last_seen = ?, frequency = frequency + 1, 
                        suggested_actions = ?, confidence_score = ?
                    WHERE id = ?
                """, (issue.last_seen, '|'.join(issue.suggested_actions), 
                      issue.confidence_score, issue.id))
            else:
                # Insert new issue
                cursor.execute("""
                    INSERT INTO health_issues (
                        id, category, severity, title, description, affected_components,
                        ansible_output, suggested_actions, confidence_score, pattern_id,
                        first_seen, last_seen, frequency, resolved, resolution_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue.id, issue.category.value, issue.severity.value,
                    issue.title, issue.description, '|'.join(issue.affected_components),
                    issue.ansible_output, '|'.join(issue.suggested_actions),
                    issue.confidence_score, issue.pattern_id,
                    issue.first_seen, issue.last_seen, issue.frequency,
                    issue.resolved, issue.resolution_notes
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store issue: {e}")
    
    def _get_recent_issues(self, hours: int = 24) -> List[HealthIssue]:
        """Get recent issues from database."""
        try:
            conn = sqlite3.connect(str(self.issues_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM health_issues 
                WHERE last_seen > datetime('now', '-{} hours') AND resolved = 0
                ORDER BY last_seen DESC
            """.format(hours))
            
            issues = []
            for row in cursor.fetchall():
                issue = HealthIssue(
                    id=row[0],
                    category=HealthCategory(row[1]),
                    severity=HealthSeverity(row[2]),
                    title=row[3],
                    description=row[4],
                    affected_components=row[5].split('|') if row[5] else [],
                    ansible_output=row[6],
                    suggested_actions=row[7].split('|') if row[7] else [],
                    confidence_score=row[8],
                    pattern_id=row[9],
                    first_seen=datetime.fromisoformat(row[10]),
                    last_seen=datetime.fromisoformat(row[11]),
                    frequency=row[12],
                    resolved=bool(row[13]),
                    resolution_notes=row[14]
                )
                issues.append(issue)
            
            conn.close()
            return issues
            
        except Exception as e:
            logger.error(f"Failed to get recent issues: {e}")
            return []
    
    def _store_health_score(self, score: HealthScore):
        """Store health score in database."""
        try:
            conn = sqlite3.connect(str(self.issues_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO health_scores (
                    timestamp, overall_score, category_scores, critical_issues,
                    high_issues, medium_issues, low_issues, total_issues,
                    confidence, trend
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.last_updated, score.overall_score,
                json.dumps({k.value: v for k, v in score.category_scores.items()}),
                score.critical_issues, score.high_issues, score.medium_issues,
                score.low_issues, score.total_issues, score.confidence, score.trend
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store health score: {e}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        score = self.calculate_health_score()
        recent_issues = self._get_recent_issues(hours=24)
        
        return {
            "health_score": asdict(score),
            "recent_issues": [asdict(issue) for issue in recent_issues[:10]],  # Top 10
            "recommendations": self._generate_recommendations(score, recent_issues),
            "patterns_identified": len([i for i in recent_issues if i.pattern_id]),
            "ai_confidence": score.confidence,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _generate_recommendations(self, score: HealthScore, issues: List[HealthIssue]) -> List[str]:
        """Generate AI-powered recommendations."""
        recommendations = []
        
        # Critical issues
        if score.critical_issues > 0:
            recommendations.append(f"🚨 {score.critical_issues} critical issues require immediate attention")
        
        # High issues
        if score.high_issues > 0:
            recommendations.append(f"⚠️ {score.high_issues} high-priority issues need resolution")
        
        # Category-specific recommendations
        for category, cat_score in score.category_scores.items():
            if cat_score < 70:
                recommendations.append(f"🔧 {category.value.title()} health is poor ({cat_score:.1f}%) - investigate issues")
        
        # Pattern-based recommendations
        pattern_issues = [i for i in issues if i.pattern_id]
        if pattern_issues:
            recommendations.append(f"🧠 {len(pattern_issues)} recurring patterns detected - consider implementing permanent fixes")
        
        # Trend recommendations
        if score.trend == "degrading":
            recommendations.append("📉 System health is degrading - investigate root causes")
        elif score.trend == "improving":
            recommendations.append("📈 System health is improving - continue current practices")
        
        if not recommendations:
            recommendations.append("✅ System is healthy - no immediate action required")
        
        return recommendations

# Example usage and integration
def integrate_with_orchestrator():
    """Example of how to integrate AI health monitor with existing orchestrator."""
    
    # Initialize AI health monitor
    ai_monitor = AIHealthMonitor()
    
    # Example: After running Ansible playbook
    def on_ansible_complete(output: str, playbook_name: str, success: bool, nodes: List[str]):
        """Callback when Ansible playbook completes."""
        if not success:
            # Analyze the failure with AI
            issues = ai_monitor.analyze_ansible_output(output, playbook_name, nodes)
            
            # Log issues
            for issue in issues:
                logger.warning(f"Health Issue: {issue.title} (Severity: {issue.severity.value})")
                if issue.suggested_actions:
                    logger.info(f"Suggested actions: {', '.join(issue.suggested_actions)}")
    
    # Example: Get health report
    def get_system_health():
        """Get current system health."""
        report = ai_monitor.get_health_report()
        return report
    
    return ai_monitor, on_ansible_complete, get_system_health

if __name__ == "__main__":
    # Example usage
    monitor = AIHealthMonitor()
    
    # Simulate Ansible output analysis
    sample_output = """
    TASK [Install MicroK8s] ******************************************
    fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}
    fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}
    
    PLAY RECAP *****************************************************
    node1: ok=2 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
    node2: ok=1 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
    """
    
    issues = monitor.analyze_ansible_output(sample_output, "install_microk8s.yml", ["node1", "node2"])
    
    for issue in issues:
        print(f"Issue: {issue.title}")
        print(f"Severity: {issue.severity.value}")
        print(f"Actions: {issue.suggested_actions}")
        print("---")
    
    # Get health score
    score = monitor.calculate_health_score()
    print(f"Overall Health: {score.overall_score}%")
    print(f"Confidence: {score.confidence}")
    print(f"Trend: {score.trend}")
