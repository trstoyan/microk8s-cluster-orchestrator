"""
Light RAG Health System for MicroK8s Cluster Orchestrator.

A lightweight Retrieval-Augmented Generation system that:
1. Stores Ansible outputs and solutions in a vector database
2. Retrieves similar past issues when new problems occur
3. Uses a small LLM to generate contextual solutions
4. Continuously learns from system operations
5. Provides accurate health scoring and recommendations
"""

import os
import json
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle

# Lightweight ML imports
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss  # For fast vector similarity search
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG dependencies not available. Install: pip install sentence-transformers faiss-cpu")

# Small LLM integration
try:
    import requests
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class RAGDocument:
    """Document stored in the RAG system."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class RAGResult:
    """Result from RAG retrieval."""
    document: RAGDocument
    similarity_score: float
    relevance_explanation: str

class LightRAGHealthSystem:
    """Lightweight RAG system for health monitoring and issue resolution."""
    
    def __init__(self, data_dir: str = "data/rag_health"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.embedding_model = None
        self.vector_index = None
        self.documents_db = self.data_dir / "documents.db"
        self.llm_endpoint = os.getenv('LLM_ENDPOINT', 'http://localhost:11434/api/generate')
        self.llm_model = os.getenv('LLM_MODEL', 'llama3.2:1b')
        
        # Initialize RAG components
        self._initialize_rag_system()
    
    def _initialize_rag_system(self):
        """Initialize the RAG system components."""
        try:
            if not RAG_AVAILABLE:
                logger.warning("RAG components not available - using fallback mode")
                return
            
            # Initialize embedding model (lightweight)
            model_name = "all-MiniLM-L6-v2"  # Small, fast model
            self.embedding_model = SentenceTransformer(model_name)
            
            # Initialize vector index
            self._load_or_create_vector_index()
            
            # Initialize documents database
            self._initialize_documents_db()
            
            logger.info("RAG system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            self.embedding_model = None
    
    def _load_or_create_vector_index(self):
        """Load existing vector index or create new one."""
        index_path = self.data_dir / "vector_index.faiss"
        
        if index_path.exists():
            try:
                self.vector_index = faiss.read_index(str(index_path))
                logger.info(f"Loaded vector index with {self.vector_index.ntotal} documents")
            except Exception as e:
                logger.error(f"Failed to load vector index: {e}")
                self._create_new_vector_index()
        else:
            self._create_new_vector_index()
    
    def _create_new_vector_index(self):
        """Create a new vector index."""
        if not self.embedding_model:
            return
        
        # Get embedding dimension
        sample_embedding = self.embedding_model.encode(["sample"])
        dimension = sample_embedding.shape[1]
        
        # Create FAISS index (L2 distance)
        self.vector_index = faiss.IndexFlatL2(dimension)
        
        # Load existing documents if any
        self._load_existing_documents()
        
        logger.info(f"Created new vector index with dimension {dimension}")
    
    def _initialize_documents_db(self):
        """Initialize the documents database."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize documents database: {e}")
    
    def _load_existing_documents(self):
        """Load existing documents into the vector index."""
        if not self.vector_index or not self.embedding_model:
            return
        
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, content FROM documents ORDER BY created_at")
            documents = cursor.fetchall()
            conn.close()
            
            if not documents:
                return
            
            # Process documents in batches
            batch_size = 32
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                contents = [doc[1] for doc in batch]
                
                # Generate embeddings
                embeddings = self.embedding_model.encode(contents)
                
                # Add to index
                self.vector_index.add(embeddings)
            
            logger.info(f"Loaded {len(documents)} existing documents into vector index")
            
        except Exception as e:
            logger.error(f"Failed to load existing documents: {e}")
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Add a document to the RAG system.
        
        Args:
            content: Document content (Ansible output, error message, etc.)
            metadata: Additional metadata (operation type, success, etc.)
            
        Returns:
            Document ID
        """
        try:
            # Generate document ID
            doc_id = hashlib.md5(f"{content}{json.dumps(metadata)}".encode()).hexdigest()[:12]
            
            # Check if document already exists
            if self._document_exists(doc_id):
                return doc_id
            
            # Create document
            document = RAGDocument(
                id=doc_id,
                content=content,
                metadata=metadata
            )
            
            # Store in database
            self._store_document(document)
            
            # Add to vector index if RAG is available
            if self.embedding_model and self.vector_index:
                embedding = self.embedding_model.encode([content])
                self.vector_index.add(embedding)
                self._save_vector_index()
            
            logger.info(f"Added document {doc_id} to RAG system")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return None
    
    def _document_exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM documents WHERE id = ?", (doc_id,))
            exists = cursor.fetchone() is not None
            
            conn.close()
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check document existence: {e}")
            return False
    
    def _store_document(self, document: RAGDocument):
        """Store document in database."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO documents (id, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                document.id,
                document.content,
                json.dumps(document.metadata),
                document.created_at,
                datetime.utcnow()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store document: {e}")
    
    def _save_vector_index(self):
        """Save vector index to disk."""
        if not self.vector_index:
            return
        
        try:
            index_path = self.data_dir / "vector_index.faiss"
            faiss.write_index(self.vector_index, str(index_path))
        except Exception as e:
            logger.error(f"Failed to save vector index: {e}")
    
    def retrieve_similar(self, query: str, top_k: int = 5, 
                        min_similarity: float = 0.3) -> List[RAGResult]:
        """
        Retrieve similar documents for a query.
        
        Args:
            query: Search query (error message, Ansible output, etc.)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of RAGResult objects
        """
        try:
            if not self.embedding_model or not self.vector_index:
                return self._fallback_retrieval(query, top_k)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Search vector index
            similarities, indices = self.vector_index.search(query_embedding, top_k)
            
            results = []
            for similarity, idx in zip(similarities[0], indices[0]):
                if idx == -1 or similarity < min_similarity:
                    continue
                
                # Get document from database
                document = self._get_document_by_index(idx)
                if document:
                    result = RAGResult(
                        document=document,
                        similarity_score=float(1.0 / (1.0 + similarity)),  # Convert distance to similarity
                        relevance_explanation=f"Similarity: {float(1.0 / (1.0 + similarity)):.3f}"
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar documents: {e}")
            return self._fallback_retrieval(query, top_k)
    
    def _fallback_retrieval(self, query: str, top_k: int) -> List[RAGResult]:
        """Fallback text-based retrieval when RAG is not available."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            # Simple text search
            cursor.execute("""
                SELECT id, content, metadata FROM documents 
                WHERE content LIKE ? OR content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{query[:50]}%", f"%{query[-50:]}%", top_k))
            
            results = []
            for row in cursor.fetchall():
                doc_id, content, metadata = row
                
                document = RAGDocument(
                    id=doc_id,
                    content=content,
                    metadata=json.loads(metadata)
                )
                
                result = RAGResult(
                    document=document,
                    similarity_score=0.5,  # Default similarity
                    relevance_explanation="Text-based match"
                )
                results.append(result)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Fallback retrieval failed: {e}")
            return []
    
    def _get_document_by_index(self, index: int) -> Optional[RAGDocument]:
        """Get document by vector index position."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            # Get document at index position
            cursor.execute("""
                SELECT id, content, metadata, created_at FROM documents 
                ORDER BY created_at LIMIT 1 OFFSET ?
            """, (index,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return RAGDocument(
                    id=row[0],
                    content=row[1],
                    metadata=json.loads(row[2]),
                    created_at=datetime.fromisoformat(row[3])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by index: {e}")
            return None
    
    def generate_response(self, query: str, context_documents: List[RAGDocument] = None) -> Dict[str, Any]:
        """
        Generate response using small LLM with RAG context.
        
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
            
            # Prepare context
            context = self._prepare_context(context_documents)
            
            # Generate prompt for small LLM
            prompt = self._create_rag_prompt(query, context)
            
            if LLM_AVAILABLE:
                # Call small LLM
                response = self._call_llm(prompt)
                
                # Parse response
                parsed_response = self._parse_llm_response(response)
                
                return {
                    'response': parsed_response,
                    'context_used': len(context_documents),
                    'confidence': self._calculate_response_confidence(context_documents),
                    'method': 'rag_llm'
                }
            else:
                # Fallback to rule-based response
                return self._generate_fallback_response(query, context_documents)
                
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return {
                'response': {'error': str(e)},
                'context_used': 0,
                'confidence': 0.0,
                'method': 'error'
            }
    
    def _prepare_context(self, documents: List[RAGDocument]) -> str:
        """Prepare context string from documents."""
        if not documents:
            return "No relevant context found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"Example {i}:")
            context_parts.append(f"Content: {doc.content[:500]}...")
            context_parts.append(f"Metadata: {doc.metadata}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _create_rag_prompt(self, query: str, context: str) -> str:
        """Create prompt for RAG-based LLM generation."""
        return f"""
You are an expert system administrator helping with MicroK8s cluster issues. 

Based on the following context from similar past issues, provide a helpful response to the current problem.

CONTEXT FROM SIMILAR ISSUES:
{context}

CURRENT PROBLEM:
{query}

Please provide:
1. A diagnosis of the problem
2. Step-by-step solution
3. Prevention tips
4. Confidence level (1-10)

Format your response as JSON with keys: diagnosis, solution, prevention, confidence
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call the small LLM."""
        try:
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            
            response = requests.post(self.llm_endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            return response.json().get('response', '')
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    'diagnosis': 'Unable to parse response',
                    'solution': 'Check system logs',
                    'prevention': 'Regular monitoring',
                    'confidence': 1
                }
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                'diagnosis': 'Response parsing failed',
                'solution': 'Manual investigation required',
                'prevention': 'Improve system monitoring',
                'confidence': 1
            }
    
    def _calculate_response_confidence(self, context_documents: List[RAGDocument]) -> float:
        """Calculate confidence in the generated response."""
        if not context_documents:
            return 0.3
        
        # Base confidence on number and recency of context documents
        base_confidence = min(0.8, 0.3 + (len(context_documents) * 0.15))
        
        # Boost confidence for recent documents
        now = datetime.utcnow()
        recent_docs = [doc for doc in context_documents 
                      if (now - doc.created_at).days <= 30]
        
        if recent_docs:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _generate_fallback_response(self, query: str, context_documents: List[RAGDocument]) -> Dict[str, Any]:
        """Generate fallback response without LLM."""
        if not context_documents:
            return {
                'response': {
                    'diagnosis': 'No similar issues found in knowledge base',
                    'solution': 'Manual investigation required',
                    'prevention': 'Add this issue to knowledge base after resolution',
                    'confidence': 2
                },
                'context_used': 0,
                'confidence': 0.2,
                'method': 'fallback'
            }
        
        # Simple pattern matching
        content = ' '.join([doc.content for doc in context_documents])
        
        if 'snap' in query.lower() and 'snap' in content.lower():
            diagnosis = "Snap package manager issue detected"
            solution = "Install snapd or use alternative package manager"
        elif 'permission' in query.lower():
            diagnosis = "Permission/authentication issue"
            solution = "Check SSH keys, sudo access, and file permissions"
        elif 'microk8s' in query.lower():
            diagnosis = "MicroK8s installation or configuration issue"
            solution = "Verify MicroK8s installation and cluster status"
        else:
            diagnosis = "System configuration or deployment issue"
            solution = "Check logs, verify prerequisites, and system status"
        
        return {
            'response': {
                'diagnosis': diagnosis,
                'solution': solution,
                'prevention': 'Regular system monitoring and maintenance',
                'confidence': 5
            },
            'context_used': len(context_documents),
            'confidence': 0.6,
            'method': 'pattern_matching'
        }
    
    def analyze_ansible_output(self, output: str, playbook_name: str, 
                             affected_hosts: List[str] = None) -> Dict[str, Any]:
        """
        Analyze Ansible output using RAG system.
        
        Args:
            output: Raw Ansible output
            playbook_name: Name of the playbook
            affected_hosts: List of affected hostnames
            
        Returns:
            Analysis results with RAG-based insights
        """
        try:
            # Extract key information from output
            error_lines = [line for line in output.split('\n') if 'fatal:' in line or 'ERROR' in line]
            success = 'PLAY RECAP' in output and 'failed=0' in output
            
            # Create query for RAG system
            query = f"Ansible playbook {playbook_name} failed with errors: {' '.join(error_lines[:3])}"
            
            # Generate response using RAG
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
                'recommendations': self._extract_recommendations(rag_response),
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
    
    def _extract_recommendations(self, rag_response: Dict[str, Any]) -> List[str]:
        """Extract recommendations from RAG response."""
        recommendations = []
        
        response_data = rag_response.get('response', {})
        
        if 'solution' in response_data:
            # Split solution into steps
            solution = response_data['solution']
            if isinstance(solution, str):
                # Split by common delimiters
                steps = [step.strip() for step in solution.split('\n') if step.strip()]
                recommendations.extend(steps)
        
        if 'prevention' in response_data:
            prevention = response_data['prevention']
            if isinstance(prevention, str):
                recommendations.append(f"Prevention: {prevention}")
        
        return recommendations[:5]  # Limit to top 5
    
    def get_health_insights(self) -> Dict[str, Any]:
        """Get health insights using RAG system."""
        try:
            # Query for recent issues and solutions
            recent_query = "recent system issues and health problems"
            rag_results = self.retrieve_similar(recent_query, top_k=5)
            
            if not rag_results:
                return {
                    'insights': ['No historical data available for insights'],
                    'confidence': 0.1,
                    'patterns_found': 0
                }
            
            # Analyze patterns
            patterns = self._analyze_patterns(rag_results)
            
            # Generate insights
            insights = self._generate_health_insights(patterns, rag_results)
            
            return {
                'insights': insights,
                'confidence': sum(result.similarity_score for result in rag_results) / len(rag_results),
                'patterns_found': len(patterns),
                'documents_analyzed': len(rag_results)
            }
            
        except Exception as e:
            logger.error(f"Failed to get health insights: {e}")
            return {
                'insights': ['Unable to generate insights - check system logs'],
                'confidence': 0.0,
                'patterns_found': 0
            }
    
    def _analyze_patterns(self, rag_results: List[RAGResult]) -> List[Dict[str, Any]]:
        """Analyze patterns in retrieved documents."""
        patterns = []
        
        # Group by metadata types
        type_groups = {}
        for result in rag_results:
            doc_type = result.document.metadata.get('type', 'unknown')
            if doc_type not in type_groups:
                type_groups[doc_type] = []
            type_groups[doc_type].append(result)
        
        # Identify patterns
        for doc_type, results in type_groups.items():
            if len(results) >= 2:  # At least 2 similar documents
                pattern = {
                    'type': doc_type,
                    'frequency': len(results),
                    'avg_similarity': sum(r.similarity_score for r in results) / len(results),
                    'common_issues': self._extract_common_issues(results)
                }
                patterns.append(pattern)
        
        return patterns
    
    def _extract_common_issues(self, results: List[RAGResult]) -> List[str]:
        """Extract common issues from results."""
        issues = []
        
        for result in results:
            content = result.document.content
            # Extract error patterns
            if 'fatal:' in content:
                fatal_lines = [line for line in content.split('\n') if 'fatal:' in line]
                issues.extend(fatal_lines[:2])  # Top 2 fatal errors
        
        # Remove duplicates
        return list(set(issues))[:5]
    
    def _generate_health_insights(self, patterns: List[Dict[str, Any]], 
                                rag_results: List[RAGResult]) -> List[str]:
        """Generate health insights from patterns."""
        insights = []
        
        if not patterns:
            insights.append("No recurring patterns detected")
            return insights
        
        # Pattern-based insights
        for pattern in patterns:
            if pattern['frequency'] >= 3:
                insights.append(f"🚨 Recurring {pattern['type']} issues detected ({pattern['frequency']} occurrences)")
            
            if pattern['avg_similarity'] > 0.7:
                insights.append(f"🔍 High similarity pattern in {pattern['type']} issues")
        
        # Success rate insights
        successful_docs = [r for r in rag_results 
                          if r.document.metadata.get('success', False)]
        success_rate = len(successful_docs) / len(rag_results) if rag_results else 0
        
        if success_rate < 0.5:
            insights.append("⚠️ Low success rate in recent operations")
        elif success_rate > 0.8:
            insights.append("✅ High success rate in recent operations")
        
        return insights
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        try:
            conn = sqlite3.connect(str(self.documents_db))
            cursor = conn.cursor()
            
            # Get document count
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            # Get documents by type
            cursor.execute("""
                SELECT metadata, COUNT(*) FROM documents 
                GROUP BY JSON_EXTRACT(metadata, '$.type')
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
                'vector_index_size': self.vector_index.ntotal if self.vector_index else 0,
                'documents_by_type': type_counts,
                'recent_documents_7d': recent_docs,
                'rag_available': RAG_AVAILABLE and self.embedding_model is not None,
                'llm_available': LLM_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_documents': 0,
                'error': str(e)
            }

# Global instance
light_rag_system = LightRAGHealthSystem()

def get_light_rag_system() -> LightRAGHealthSystem:
    """Get the global Light RAG system instance."""
    return light_rag_system
