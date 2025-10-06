"""
Local RAG System for Raspberry Pi 5 - Zero External Dependencies.

A completely local, lightweight RAG system that:
1. Uses only built-in Python libraries + SQLite
2. Implements simple text similarity using TF-IDF
3. Stores and retrieves patterns locally
4. Uses rule-based "AI" responses
5. Builds knowledge base from Ansible outputs
6. Runs efficiently on Raspberry Pi 5
"""

import os
import json
import sqlite3
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter, defaultdict
import math

# Only use built-in libraries
from collections import Counter, defaultdict
import sqlite3
import json
import hashlib
import re
import math
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class LocalDocument:
    """Document stored in the local RAG system."""
    id: str
    content: str
    metadata: Dict[str, Any]
    keywords: List[str]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class LocalRAGResult:
    """Result from local RAG retrieval."""
    document: LocalDocument
    similarity_score: float
    matching_keywords: List[str]

class LocalRAGSystem:
    """Completely local RAG system with zero external dependencies."""
    
    def __init__(self, data_dir: str = None):
        # Get configuration (handle both relative and absolute imports)
        try:
            from ..utils.ai_config import get_ai_config
            ai_config = get_ai_config()
        except ImportError:
            # Fallback for standalone usage
            from utils.ai_config import get_ai_config
            ai_config = get_ai_config()
        
        # Use configured data directory or default
        if data_dir is None:
            data_dir = ai_config.get_rag_config().get('data_dir', 'data/local_rag')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Store configuration reference
        self.ai_config = ai_config
        
        # Initialize databases
        self.documents_db = self.data_dir / "documents.db"
        self.patterns_db = self.data_dir / "patterns.db"
        
        # Initialize components
        self.vocabulary = set()
        self.document_frequencies = Counter()
        self.total_documents = 0
        
        # Initialize databases
        self._initialize_databases()
        self._load_vocabulary()
    
    def _initialize_databases(self):
        """Initialize the SQLite databases."""
        try:
            # Documents database
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for faster searches
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords ON documents(keywords)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON documents(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata ON documents(metadata)")
            
            conn.commit()
            conn.close()
            
            # Patterns database
            conn = sqlite3.connect(str(self.patterns_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    pattern_text TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    success_rate REAL DEFAULT 0.0,
                    solution TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON patterns(pattern_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_frequency ON patterns(frequency)")
            
            conn.commit()
            conn.close()
            
            logger.info("Local RAG databases initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize databases: {e}")
    
    def _load_vocabulary(self):
        """Load vocabulary from existing documents."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT keywords FROM documents")
            all_keywords = []
            
            for row in cursor.fetchall():
                keywords = json.loads(row[0])
                all_keywords.extend(keywords)
                self.vocabulary.update(keywords)
            
            self.document_frequencies = Counter(all_keywords)
            self.total_documents = len(cursor.fetchall())
            
            conn.close()
            
            logger.info(f"Loaded vocabulary with {len(self.vocabulary)} unique terms")
            
        except Exception as e:
            logger.error(f"Failed to load vocabulary: {e}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using simple tokenization."""
        # Convert to lowercase and split on non-alphanumeric characters
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Filter out short words and stop words
        keywords = [word for word in words 
                   if len(word) > 2 and word not in stop_words]
        
        return keywords
    
    def _calculate_tfidf(self, keywords: List[str], document_keywords: List[str]) -> float:
        """Calculate TF-IDF similarity between two keyword lists."""
        if not keywords or not document_keywords:
            return 0.0
        
        # Term frequency for query
        query_tf = Counter(keywords)
        
        # Term frequency for document
        doc_tf = Counter(document_keywords)
        
        # Calculate TF-IDF scores
        similarity_score = 0.0
        total_terms = 0
        
        for term in keywords:
            if term in doc_tf:
                # Term frequency
                tf_query = query_tf[term] / len(keywords)
                tf_doc = doc_tf[term] / len(document_keywords)
                
                # Inverse document frequency
                idf = math.log(self.total_documents / (self.document_frequencies.get(term, 1) + 1))
                
                # TF-IDF score
                tfidf_score = tf_query * tf_doc * idf
                similarity_score += tfidf_score
                total_terms += 1
        
        # Normalize by number of matching terms
        if total_terms > 0:
            similarity_score = similarity_score / total_terms
        
        return similarity_score
    
    def _anonymize_content(self, content: str) -> str:
        """Anonymize sensitive content by replacing usernames, IPs, etc."""
        import re
        
        # Replace common sensitive patterns
        content = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]', content)
        content = re.sub(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '[EMAIL]', content)
        content = re.sub(r'\b[A-Za-z0-9+/]{20,}={0,2}\b', '[TOKEN]', content)  # Base64 tokens
        content = re.sub(r'\b[A-Fa-f0-9]{32,}\b', '[HASH]', content)  # MD5/SHA hashes
        
        return content
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Add a document to the local RAG system.
        
        Args:
            content: Document content (Ansible output, error message, etc.)
            metadata: Additional metadata (operation type, success, etc.)
            
        Returns:
            Document ID
        """
        try:
            # Check if we should store this type of content based on privacy settings
            if metadata and metadata.get('type') == 'chat_interaction' and not self.ai_config.should_store_chat_history():
                return None
            if metadata and metadata.get('type') == 'ansible_output' and not self.ai_config.should_store_ansible_outputs():
                return None
            
            # Anonymize content if configured
            if self.ai_config.should_anonymize_data():
                content = self._anonymize_content(content)
            
            # Generate document ID
            doc_id = hashlib.md5(f"{content}{json.dumps(metadata)}".encode()).hexdigest()[:12]
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            # Create document
            document = LocalDocument(
                id=doc_id,
                content=content,
                metadata=metadata,
                keywords=keywords
            )
            
            # Store in database
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO documents (id, content, metadata, keywords, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc_id,
                content,
                json.dumps(metadata),
                json.dumps(keywords),
                document.created_at
            ))
            
            conn.commit()
            conn.close()
            
            # Update vocabulary and frequencies
            self.vocabulary.update(keywords)
            self.document_frequencies.update(keywords)
            self.total_documents += 1
            
            # Extract and store patterns
            self._extract_and_store_patterns(content, metadata, doc_id)
            
            logger.info(f"Added document {doc_id} to local RAG system")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return None
    
    def _extract_and_store_patterns(self, content: str, metadata: Dict[str, Any], doc_id: str):
        """Extract patterns from content and store them."""
        try:
            # Extract error patterns
            error_patterns = self._extract_error_patterns(content)
            
            # Extract solution patterns
            solution_patterns = self._extract_solution_patterns(content)
            
            # Store patterns
            conn = sqlite3.connect(str(self.patterns_db))
            cursor = conn.cursor()
            
            for pattern in error_patterns:
                pattern_id = hashlib.md5(f"error_{pattern}".encode()).hexdigest()[:8]
                
                cursor.execute("""
                    INSERT OR REPLACE INTO patterns 
                    (id, pattern_type, pattern_text, frequency, first_seen, last_seen)
                    VALUES (?, ?, ?, 
                        COALESCE((SELECT frequency FROM patterns WHERE id = ?), 0) + 1,
                        COALESCE((SELECT first_seen FROM patterns WHERE id = ?), CURRENT_TIMESTAMP),
                        CURRENT_TIMESTAMP)
                """, (pattern_id, 'error', pattern, pattern_id, pattern_id))
            
            for pattern in solution_patterns:
                pattern_id = hashlib.md5(f"solution_{pattern}".encode()).hexdigest()[:8]
                
                cursor.execute("""
                    INSERT OR REPLACE INTO patterns 
                    (id, pattern_type, pattern_text, frequency, first_seen, last_seen)
                    VALUES (?, ?, ?, 
                        COALESCE((SELECT frequency FROM patterns WHERE id = ?), 0) + 1,
                        COALESCE((SELECT first_seen FROM patterns WHERE id = ?), CURRENT_TIMESTAMP),
                        CURRENT_TIMESTAMP)
                """, (pattern_id, 'solution', pattern, pattern_id, pattern_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to extract patterns: {e}")
    
    def _extract_error_patterns(self, content: str) -> List[str]:
        """Extract error patterns from content."""
        patterns = []
        
        # Common error patterns
        error_regexes = [
            r'fatal:.*?=>\s*\{[^}]*"msg":\s*"([^"]+)"',
            r'ERROR:\s*([^\n]+)',
            r'FAILED!\s*=>\s*\{[^}]*"msg":\s*"([^"]+)"',
            r'Permission denied',
            r'Command not found',
            r'Connection refused',
            r'No such file or directory'
        ]
        
        for regex in error_regexes:
            matches = re.findall(regex, content, re.IGNORECASE)
            patterns.extend(matches)
        
        return patterns[:5]  # Limit to 5 patterns
    
    def _extract_solution_patterns(self, content: str) -> List[str]:
        """Extract solution patterns from content."""
        patterns = []
        
        # Look for solution indicators
        solution_indicators = [
            'sudo apt install',
            'systemctl restart',
            'snap install',
            'microk8s enable',
            'kubectl apply',
            'chmod',
            'chown'
        ]
        
        for indicator in solution_indicators:
            if indicator in content.lower():
                # Extract the command line
                lines = content.split('\n')
                for line in lines:
                    if indicator in line.lower():
                        patterns.append(line.strip())
                        break
        
        return patterns[:3]  # Limit to 3 patterns
    
    def retrieve_similar(self, query: str, top_k: int = 5, 
                        min_similarity: float = 0.1) -> List[LocalRAGResult]:
        """
        Retrieve similar documents using local TF-IDF.
        
        Args:
            query: Search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of LocalRAGResult objects
        """
        try:
            # Extract keywords from query
            query_keywords = self._extract_keywords(query)
            
            if not query_keywords:
                return []
            
            # Search database
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, content, metadata, keywords FROM documents ORDER BY created_at DESC")
            results = []
            
            for row in cursor.fetchall():
                doc_id, content, metadata, keywords_json = row
                
                document = LocalDocument(
                    id=doc_id,
                    content=content,
                    metadata=json.loads(metadata),
                    keywords=json.loads(keywords_json)
                )
                
                # Calculate similarity
                similarity = self._calculate_tfidf(query_keywords, document.keywords)
                
                if similarity >= min_similarity:
                    # Find matching keywords
                    matching_keywords = list(set(query_keywords) & set(document.keywords))
                    
                    result = LocalRAGResult(
                        document=document,
                        similarity_score=similarity,
                        matching_keywords=matching_keywords
                    )
                    results.append(result)
            
            conn.close()
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar documents: {e}")
            return []
    
    def generate_response(self, query: str, context_documents: List[LocalDocument] = None) -> Dict[str, Any]:
        """
        Generate response using local pattern matching and rule-based logic.
        
        Args:
            query: User query or problem description
            context_documents: Relevant documents from retrieval
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            if not context_documents:
                # Retrieve relevant documents
                rag_results = self.retrieve_similar(query, top_k=3)
                context_documents = [result.document for result in rag_results]
            
            # Generate response using local patterns
            response = self._generate_local_response(query, context_documents)
            
            return {
                'response': response,
                'context_used': len(context_documents),
                'confidence': self._calculate_local_confidence(context_documents),
                'method': 'local_pattern_matching'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return {
                'response': {'error': str(e)},
                'context_used': 0,
                'confidence': 0.0,
                'method': 'error'
            }
    
    def _generate_local_response(self, query: str, context_documents: List[LocalDocument]) -> Dict[str, Any]:
        """Generate response using local pattern matching."""
        
        # Extract query keywords
        query_keywords = self._extract_keywords(query)
        
        # Initialize response
        response = {
            'diagnosis': 'Unknown issue',
            'solution': 'Manual investigation required',
            'prevention': 'Regular system monitoring',
            'confidence': 3
        }
        
        # Pattern-based diagnosis
        if any(keyword in query.lower() for keyword in ['snap', 'snapd']):
            response['diagnosis'] = 'Snap package manager issue'
            response['solution'] = 'Install snapd: sudo apt install snapd'
            response['confidence'] = 8
        elif any(keyword in query.lower() for keyword in ['permission', 'denied', 'access']):
            response['diagnosis'] = 'Permission or authentication issue'
            response['solution'] = 'Check SSH keys, sudo access, and file permissions'
            response['confidence'] = 7
        elif any(keyword in query.lower() for keyword in ['microk8s', 'kubernetes', 'k8s']):
            response['diagnosis'] = 'MicroK8s installation or configuration issue'
            response['solution'] = 'Check MicroK8s status: microk8s status'
            response['confidence'] = 6
        elif any(keyword in query.lower() for keyword in ['ssh', 'connection', 'connect']):
            response['diagnosis'] = 'SSH connection issue'
            response['solution'] = 'Verify SSH configuration and network connectivity'
            response['confidence'] = 7
        elif any(keyword in query.lower() for keyword in ['ansible', 'playbook']):
            response['diagnosis'] = 'Ansible playbook execution issue'
            response['solution'] = 'Check Ansible configuration and target node connectivity'
            response['confidence'] = 6
        
        # Use context documents to improve response
        if context_documents:
            # Look for successful solutions in context
            successful_docs = [doc for doc in context_documents 
                             if doc.metadata.get('success', False)]
            
            if successful_docs:
                # Extract common solutions
                solutions = []
                for doc in successful_docs:
                    doc_solutions = self._extract_solution_patterns(doc.content)
                    solutions.extend(doc_solutions)
                
                if solutions:
                    response['solution'] = solutions[0]  # Use most common solution
                    response['confidence'] = min(9, response['confidence'] + 2)
            
            # Look for similar error patterns
            error_patterns = []
            for doc in context_documents:
                doc_errors = self._extract_error_patterns(doc.content)
                error_patterns.extend(doc_errors)
            
            if error_patterns:
                # Find most common error pattern
                error_counter = Counter(error_patterns)
                most_common_error = error_counter.most_common(1)[0][0]
                response['diagnosis'] = f"Similar error pattern: {most_common_error}"
        
        # Get patterns from database
        patterns = self._get_relevant_patterns(query_keywords)
        if patterns:
            response['prevention'] = f"Common pattern: {patterns[0]}"
            response['confidence'] = min(10, response['confidence'] + 1)
        
        return response
    
    def _get_relevant_patterns(self, keywords: List[str]) -> List[str]:
        """Get relevant patterns from database."""
        try:
            conn = sqlite3.connect(str(self.patterns_db))
            cursor = conn.cursor()
            
            # Search for patterns containing any of the keywords
            keyword_conditions = " OR ".join([f"pattern_text LIKE '%{keyword}%'" for keyword in keywords])
            
            if keyword_conditions:
                cursor.execute(f"""
                    SELECT pattern_text FROM patterns 
                    WHERE ({keyword_conditions}) AND frequency > 1
                    ORDER BY frequency DESC, last_seen DESC
                    LIMIT 3
                """)
            else:
                cursor.execute("""
                    SELECT pattern_text FROM patterns 
                    WHERE frequency > 2
                    ORDER BY frequency DESC, last_seen DESC
                    LIMIT 3
                """)
            
            patterns = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get relevant patterns: {e}")
            return []
    
    def _calculate_local_confidence(self, context_documents: List[LocalDocument]) -> float:
        """Calculate confidence in the local response."""
        if not context_documents:
            return 0.3
        
        # Base confidence on number of context documents
        base_confidence = min(0.8, 0.3 + (len(context_documents) * 0.15))
        
        # Boost confidence for recent documents
        now = datetime.utcnow()
        recent_docs = [doc for doc in context_documents 
                      if (now - doc.created_at).days <= 7]
        
        if recent_docs:
            base_confidence += 0.1
        
        # Boost confidence for successful documents
        successful_docs = [doc for doc in context_documents 
                          if doc.metadata.get('success', False)]
        
        if successful_docs:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def analyze_ansible_output(self, output: str, playbook_name: str, 
                             affected_hosts: List[str] = None) -> Dict[str, Any]:
        """
        Analyze Ansible output using local RAG system.
        
        Args:
            output: Raw Ansible output
            playbook_name: Name of the playbook
            affected_hosts: List of affected hostnames
            
        Returns:
            Analysis results with local RAG insights
        """
        try:
            # Extract key information from output
            error_lines = [line for line in output.split('\n') if 'fatal:' in line or 'ERROR' in line]
            success = 'PLAY RECAP' in output and 'failed=0' in output
            
            # Create query for local RAG system
            query = f"Ansible playbook {playbook_name} {'successful' if success else 'failed'}: {' '.join(error_lines[:3])}"
            
            # Generate response using local RAG
            rag_response = self.generate_response(query)
            
            # Store this interaction in knowledge base
            metadata = {
                'type': 'ansible_output',
                'playbook': playbook_name,
                'success': success,
                'affected_hosts': affected_hosts or [],
                'error_count': len(error_lines),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            doc_id = self.add_document(output, metadata)
            
            # Return comprehensive analysis
            return {
                'success': success,
                'rag_analysis': rag_response,
                'document_id': doc_id,
                'error_summary': error_lines[:5],
                'recommendations': self._extract_local_recommendations(rag_response),
                'confidence': rag_response['confidence']
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze Ansible output: {e}")
            return {
                'success': False,
                'error': str(e),
                'rag_analysis': None,
                'recommendations': ['Check system logs for detailed error information']
            }
    
    def _extract_local_recommendations(self, rag_response: Dict[str, Any]) -> List[str]:
        """Extract recommendations from local RAG response."""
        recommendations = []
        
        response_data = rag_response.get('response', {})
        
        if 'solution' in response_data:
            recommendations.append(response_data['solution'])
        
        if 'prevention' in response_data:
            recommendations.append(f"Prevention: {response_data['prevention']}")
        
        return recommendations
    
    def get_health_insights(self) -> Dict[str, Any]:
        """Get health insights using local RAG system."""
        try:
            # Get recent documents
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT metadata FROM documents 
                WHERE created_at > datetime('now', '-30 days')
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            recent_metadata = [json.loads(row[0]) for row in cursor.fetchall()]
            conn.close()
            
            if not recent_metadata:
                return {
                    'insights': ['No recent data available for insights'],
                    'confidence': 0.1,
                    'patterns_found': 0
                }
            
            # Analyze patterns
            patterns = self._analyze_local_patterns(recent_metadata)
            
            # Generate insights
            insights = self._generate_local_insights(patterns, recent_metadata)
            
            return {
                'insights': insights,
                'confidence': 0.7,  # Local confidence
                'patterns_found': len(patterns),
                'documents_analyzed': len(recent_metadata)
            }
            
        except Exception as e:
            logger.error(f"Failed to get health insights: {e}")
            return {
                'insights': ['Unable to generate insights - check system logs'],
                'confidence': 0.0,
                'patterns_found': 0
            }
    
    def _analyze_local_patterns(self, metadata_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze patterns in recent metadata."""
        patterns = []
        
        # Group by operation types
        type_groups = defaultdict(list)
        for metadata in metadata_list:
            op_type = metadata.get('type', 'unknown')
            type_groups[op_type].append(metadata)
        
        # Identify patterns
        for op_type, metadata_group in type_groups.items():
            if len(metadata_group) >= 2:
                success_count = sum(1 for m in metadata_group if m.get('success', False))
                success_rate = success_count / len(metadata_group)
                
                pattern = {
                    'type': op_type,
                    'frequency': len(metadata_group),
                    'success_rate': success_rate,
                    'recent_activity': len([m for m in metadata_group 
                                          if datetime.fromisoformat(m.get('timestamp', '1970-01-01')) > 
                                          datetime.utcnow() - timedelta(days=7)])
                }
                patterns.append(pattern)
        
        return patterns
    
    def _generate_local_insights(self, patterns: List[Dict[str, Any]], 
                               metadata_list: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from local patterns."""
        insights = []
        
        if not patterns:
            insights.append("No recurring patterns detected in recent data")
            return insights
        
        # Pattern-based insights
        for pattern in patterns:
            if pattern['frequency'] >= 5:
                insights.append(f"🔍 Frequent {pattern['type']} operations ({pattern['frequency']} in last 30 days)")
            
            if pattern['success_rate'] < 0.5:
                insights.append(f"⚠️ Low success rate for {pattern['type']} operations ({pattern['success_rate']:.1%})")
            elif pattern['success_rate'] > 0.8:
                insights.append(f"✅ High success rate for {pattern['type']} operations ({pattern['success_rate']:.1%})")
        
        # Overall success rate
        total_operations = len(metadata_list)
        successful_operations = sum(1 for m in metadata_list if m.get('success', False))
        overall_success_rate = successful_operations / total_operations if total_operations > 0 else 0
        
        if overall_success_rate < 0.6:
            insights.append(f"🚨 Overall system success rate is low ({overall_success_rate:.1%})")
        elif overall_success_rate > 0.9:
            insights.append(f"🎉 System is performing excellently ({overall_success_rate:.1%} success rate)")
        
        return insights
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get local RAG system statistics."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            # Get document count
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            # Get documents by type
            cursor.execute("""
                SELECT JSON_EXTRACT(metadata, '$.type') as doc_type, COUNT(*) 
                FROM documents 
                GROUP BY doc_type
            """)
            type_counts = {row[0] or 'unknown': row[1] for row in cursor.fetchall()}
            
            # Get recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM documents 
                WHERE created_at > datetime('now', '-7 days')
            """)
            recent_docs = cursor.fetchone()[0]
            
            conn.close()
            
            # Get pattern statistics
            conn = sqlite3.connect(str(self.patterns_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM patterns")
            total_patterns = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM patterns WHERE frequency > 1")
            frequent_patterns = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_documents': total_docs,
                'vocabulary_size': len(self.vocabulary),
                'documents_by_type': type_counts,
                'recent_documents_7d': recent_docs,
                'total_patterns': total_patterns,
                'frequent_patterns': frequent_patterns,
                'system_type': 'local_only',
                'external_dependencies': 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_documents': 0,
                'error': str(e)
            }

# Global instance (lazy initialization to avoid import issues)
local_rag_system = None

def get_local_rag_system() -> LocalRAGSystem:
    """Get or create the global RAG system instance."""
    global local_rag_system
    if local_rag_system is None:
        local_rag_system = LocalRAGSystem()
    return local_rag_system
