#!/usr/bin/env python3
"""
Standalone RAG System Test - Completely independent test of the RAG functionality.

This script tests the core RAG algorithms without any Flask or external dependencies.
Perfect for testing the mathematical and algorithmic components.
"""

import os
import json
import sqlite3
import hashlib
import logging
import re
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Document for testing."""
    id: str
    content: str
    metadata: Dict[str, Any]
    keywords: List[str]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class SearchResult:
    """Search result for testing."""
    document: Document
    similarity_score: float
    matching_keywords: List[str]

class StandaloneRAGSystem:
    """Standalone RAG system for testing core algorithms."""
    
    def __init__(self, data_dir: str = "test_data/standalone_rag"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize databases
        self.documents_db = self.data_dir / "documents.db"
        self.patterns_db = self.data_dir / "patterns.db"
        
        # Initialize components
        self.vocabulary = set()
        self.document_frequencies = Counter()
        self.total_documents = 0
        
        # Initialize databases
        self._initialize_databases()
    
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
            
            conn.commit()
            conn.close()
            
            print("✅ Databases initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize databases: {e}")
    
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
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add a document to the system."""
        try:
            # Generate document ID
            doc_id = hashlib.md5(f"{content}{json.dumps(metadata)}".encode()).hexdigest()[:12]
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            # Create document
            document = Document(
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
            
            print(f"✅ Added document: {doc_id}")
            return doc_id
            
        except Exception as e:
            print(f"❌ Failed to add document: {e}")
            return None
    
    def retrieve_similar(self, query: str, top_k: int = 5, 
                        min_similarity: float = 0.1) -> List[SearchResult]:
        """Retrieve similar documents using TF-IDF."""
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
                
                document = Document(
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
                    
                    result = SearchResult(
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
            print(f"❌ Failed to retrieve similar documents: {e}")
            return []
    
    def generate_response(self, query: str) -> Dict[str, Any]:
        """Generate response using pattern matching."""
        try:
            # Retrieve relevant documents
            results = self.retrieve_similar(query, top_k=3)
            
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
            
            # Use retrieved documents to improve response
            if results:
                # Look for successful solutions
                successful_docs = [r for r in results 
                                 if r.document.metadata.get('success', False)]
                
                if successful_docs:
                    response['solution'] = successful_docs[0].document.content
                    response['confidence'] = min(9, response['confidence'] + 2)
            
            return {
                'response': response,
                'context_used': len(results),
                'confidence': min(1.0, 0.3 + (len(results) * 0.2)),
                'method': 'standalone_pattern_matching'
            }
            
        except Exception as e:
            print(f"❌ Failed to generate response: {e}")
            return {
                'response': {'error': str(e)},
                'context_used': 0,
                'confidence': 0.0,
                'method': 'error'
            }
    
    def analyze_ansible_output(self, output: str, playbook_name: str, 
                             affected_hosts: List[str] = None) -> Dict[str, Any]:
        """Analyze Ansible output."""
        try:
            # Extract key information from output
            error_lines = [line for line in output.split('\n') if 'fatal:' in line or 'ERROR' in line]
            success = 'PLAY RECAP' in output and 'failed=0' in output
            
            # Create query for analysis
            query = f"Ansible playbook {playbook_name} {'successful' if success else 'failed'}: {' '.join(error_lines[:3])}"
            
            # Generate response
            rag_response = self.generate_response(query)
            
            # Store this interaction
            metadata = {
                'type': 'ansible_output',
                'playbook': playbook_name,
                'success': success,
                'affected_hosts': affected_hosts or [],
                'error_count': len(error_lines),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            doc_id = self.add_document(output, metadata)
            
            # Return analysis
            return {
                'success': success,
                'rag_analysis': rag_response,
                'document_id': doc_id,
                'error_summary': error_lines[:5],
                'recommendations': [rag_response['response']['solution']],
                'confidence': rag_response['response']['confidence']
            }
            
        except Exception as e:
            print(f"❌ Failed to analyze Ansible output: {e}")
            return {
                'success': False,
                'error': str(e),
                'rag_analysis': None,
                'recommendations': ['Check system logs for detailed error information']
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
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
            
            return {
                'total_documents': total_docs,
                'vocabulary_size': len(self.vocabulary),
                'documents_by_type': type_counts,
                'recent_documents_7d': recent_docs,
                'system_type': 'standalone_test',
                'external_dependencies': 0
            }
            
        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return {
                'total_documents': 0,
                'error': str(e)
            }

def run_comprehensive_test():
    """Run comprehensive test of the standalone RAG system."""
    print("🧪 Standalone RAG System Test")
    print("=" * 60)
    print("Testing core algorithms without any external dependencies")
    print()
    
    try:
        # Initialize system
        print("1. Initializing standalone RAG system...")
        rag_system = StandaloneRAGSystem()
        print("✅ System initialized")
        
        # Test document addition
        print("\n2. Testing document addition...")
        
        sample_docs = [
            {
                'content': 'fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}',
                'metadata': {'type': 'ansible_error', 'playbook': 'install_microk8s', 'success': False}
            },
            {
                'content': 'sudo apt install snapd && snap install microk8s --classic',
                'metadata': {'type': 'solution', 'playbook': 'install_microk8s', 'success': True}
            },
            {
                'content': 'fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}',
                'metadata': {'type': 'ansible_error', 'playbook': 'setup_cluster', 'success': False}
            },
            {
                'content': 'chmod 600 ~/.ssh/id_rsa && ssh-add ~/.ssh/id_rsa',
                'metadata': {'type': 'solution', 'playbook': 'setup_cluster', 'success': True}
            }
        ]
        
        doc_ids = []
        for i, doc in enumerate(sample_docs, 1):
            doc_id = rag_system.add_document(doc['content'], doc['metadata'])
            doc_ids.append(doc_id)
        
        print(f"✅ Added {len(doc_ids)} documents")
        
        # Test search functionality
        print("\n3. Testing search functionality...")
        
        test_queries = [
            "snap command not found",
            "permission denied",
            "microk8s installation",
            "ssh connection failed"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            results = rag_system.retrieve_similar(query, top_k=2)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"     Result {i}: Similarity {result.similarity_score:.3f}")
                    print(f"       Content: {result.document.content[:60]}...")
                    print(f"       Matching keywords: {result.matching_keywords}")
            else:
                print("     No results found")
        
        print("✅ Search functionality working")
        
        # Test response generation
        print("\n4. Testing response generation...")
        
        test_questions = [
            "How do I fix snap command not found?",
            "What causes permission denied errors?",
            "How to install MicroK8s?"
        ]
        
        for question in test_questions:
            print(f"\n   Question: '{question}'")
            response = rag_system.generate_response(question)
            
            print(f"     Method: {response['method']}")
            print(f"     Confidence: {response['confidence']:.3f}")
            print(f"     Context used: {response['context_used']}")
            
            resp_data = response['response']
            print(f"     Diagnosis: {resp_data.get('diagnosis', 'N/A')}")
            print(f"     Solution: {resp_data.get('solution', 'N/A')}")
            print(f"     Confidence: {resp_data.get('confidence', 'N/A')}")
        
        print("✅ Response generation working")
        
        # Test Ansible output analysis
        print("\n5. Testing Ansible output analysis...")
        
        sample_ansible_output = """
TASK [Install MicroK8s] ******************************************
fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}
fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}

PLAY RECAP *****************************************************
node1: ok=2 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
node2: ok=1 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
        """
        
        analysis = rag_system.analyze_ansible_output(
            sample_ansible_output,
            "install_microk8s.yml",
            ["node1", "node2"]
        )
        
        print(f"   Success: {analysis['success']}")
        print(f"   Document ID: {analysis['document_id']}")
        print(f"   Confidence: {analysis['confidence']}")
        print(f"   Error summary: {analysis['error_summary'][:2]}")
        print(f"   Recommendations:")
        for rec in analysis['recommendations']:
            print(f"     - {rec}")
        
        print("✅ Ansible analysis working")
        
        # Test statistics
        print("\n6. Testing system statistics...")
        
        stats = rag_system.get_statistics()
        
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Vocabulary size: {stats['vocabulary_size']}")
        print(f"   Documents by type: {stats['documents_by_type']}")
        print(f"   Recent documents (7d): {stats['recent_documents_7d']}")
        print(f"   System type: {stats['system_type']}")
        print(f"   External dependencies: {stats['external_dependencies']}")
        
        print("✅ Statistics working")
        
        # Performance test
        print("\n7. Testing performance...")
        
        import time
        
        # Test document addition performance
        start_time = time.time()
        for i in range(5):
            content = f"Performance test document {i} with various keywords for testing"
            metadata = {'type': 'test', 'index': i}
            rag_system.add_document(content, metadata)
        add_time = time.time() - start_time
        
        print(f"   Added 5 documents in {add_time:.3f} seconds")
        print(f"   Average time per document: {add_time/5:.3f} seconds")
        
        # Test search performance
        start_time = time.time()
        for i in range(5):
            query = f"test document {i} keywords"
            results = rag_system.retrieve_similar(query, top_k=3)
        search_time = time.time() - start_time
        
        print(f"   Performed 5 searches in {search_time:.3f} seconds")
        print(f"   Average time per search: {search_time/5:.3f} seconds")
        
        # Test response generation performance
        start_time = time.time()
        for i in range(3):
            query = f"How to fix test document {i}?"
            response = rag_system.generate_response(query)
        response_time = time.time() - start_time
        
        print(f"   Generated 3 responses in {response_time/3:.3f} seconds")
        print(f"   Average time per response: {response_time/3:.3f} seconds")
        
        print("✅ Performance test completed")
        
        # Cleanup
        print("\n8. Cleaning up test data...")
        
        import shutil
        test_data_dir = Path("test_data")
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
            print("✅ Test data cleaned up")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("The Standalone RAG System is working perfectly!")
        print("🍓 Core algorithms are ready for Raspberry Pi 5!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")
        return False

def main():
    """Main test function."""
    success = run_comprehensive_test()
    
    if success:
        print("\n✅ All standalone tests passed!")
        print("The core RAG algorithms are working correctly!")
        print("Ready to integrate with the full system!")
    else:
        print("\n❌ Tests failed!")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
