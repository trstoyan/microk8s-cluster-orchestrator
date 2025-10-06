"""
Content Search Service for AI Assistant.

This module provides search functionality for playbooks, documentation,
and operation logs to enhance the AI assistant's knowledge base.
"""

import logging
import os
import re
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentSearchService:
    """Service for searching and indexing content files."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the content search service.
        
        Args:
            config: Searchable content configuration
        """
        self.config = config
        self.data_dir = Path("data/content_search")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_db = self.data_dir / "content_index.db"
        self._initialize_database()
        
        # Content directories to search
        self.playbooks_dir = Path("ansible/playbooks")
        self.docs_dir = Path("docs")
        self.logs_dir = Path("logs")
        
    def _initialize_database(self):
        """Initialize the content index database."""
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    content_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    keywords TEXT,
                    last_modified REAL,
                    indexed_at REAL,
                    file_size INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_content_type ON content_index(content_type)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_keywords ON content_index(keywords)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing content index database: {e}")
    
    def index_content(self, force_reindex: bool = False) -> Dict[str, Any]:
        """
        Index all searchable content.
        
        Args:
            force_reindex: Force reindexing of all content
            
        Returns:
            Dictionary with indexing results
        """
        results = {
            'playbooks': 0,
            'documentation': 0,
            'operation_logs': 0,
            'errors': []
        }
        
        try:
            # Index playbooks
            if self.config.get('include_playbooks', True):
                results['playbooks'] = self._index_playbooks(force_reindex)
            
            # Index documentation
            if self.config.get('include_documentation', True):
                results['documentation'] = self._index_documentation(force_reindex)
            
            # Index operation logs
            if self.config.get('include_operation_logs', True):
                results['operation_logs'] = self._index_operation_logs(force_reindex)
                
        except Exception as e:
            logger.error(f"Error during content indexing: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def _index_playbooks(self, force_reindex: bool = False) -> int:
        """Index Ansible playbooks."""
        indexed_count = 0
        
        if not self.playbooks_dir.exists():
            logger.warning(f"Playbooks directory not found: {self.playbooks_dir}")
            return 0
        
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()
            
            for playbook_file in self.playbooks_dir.glob("*.yml"):
                try:
                    # Check if already indexed and not forced to reindex
                    if not force_reindex:
                        cursor.execute(
                            "SELECT last_modified FROM content_index WHERE file_path = ?",
                            (str(playbook_file),)
                        )
                        existing = cursor.fetchone()
                        if existing and existing[0] >= playbook_file.stat().st_mtime:
                            continue
                    
                    # Read and parse playbook
                    content = playbook_file.read_text(encoding='utf-8')
                    title = self._extract_playbook_title(content, playbook_file.name)
                    keywords = self._extract_playbook_keywords(content)
                    
                    # Insert or update index
                    cursor.execute('''
                        INSERT OR REPLACE INTO content_index 
                        (file_path, content_type, title, content, keywords, last_modified, indexed_at, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(playbook_file),
                        'playbook',
                        title,
                        content,
                        keywords,
                        playbook_file.stat().st_mtime,
                        datetime.now().timestamp(),
                        playbook_file.stat().st_size
                    ))
                    
                    indexed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error indexing playbook {playbook_file}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error indexing playbooks: {e}")
        
        return indexed_count
    
    def _index_documentation(self, force_reindex: bool = False) -> int:
        """Index documentation files."""
        indexed_count = 0
        
        if not self.docs_dir.exists():
            logger.warning(f"Documentation directory not found: {self.docs_dir}")
            return 0
        
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()
            
            # Index markdown files
            for doc_file in self.docs_dir.glob("*.md"):
                try:
                    # Check if already indexed and not forced to reindex
                    if not force_reindex:
                        cursor.execute(
                            "SELECT last_modified FROM content_index WHERE file_path = ?",
                            (str(doc_file),)
                        )
                        existing = cursor.fetchone()
                        if existing and existing[0] >= doc_file.stat().st_mtime:
                            continue
                    
                    # Read and parse documentation
                    content = doc_file.read_text(encoding='utf-8')
                    title = self._extract_doc_title(content, doc_file.name)
                    keywords = self._extract_doc_keywords(content)
                    
                    # Insert or update index
                    cursor.execute('''
                        INSERT OR REPLACE INTO content_index 
                        (file_path, content_type, title, content, keywords, last_modified, indexed_at, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(doc_file),
                        'documentation',
                        title,
                        content,
                        keywords,
                        doc_file.stat().st_mtime,
                        datetime.now().timestamp(),
                        doc_file.stat().st_size
                    ))
                    
                    indexed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error indexing documentation {doc_file}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error indexing documentation: {e}")
        
        return indexed_count
    
    def _index_operation_logs(self, force_reindex: bool = False) -> int:
        """Index operation logs from the database."""
        indexed_count = 0
        
        try:
            from ..models.database import db
            from ..models.flask_models import Operation
            
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()
            
            # Get recent operations
            operations = Operation.query.filter(
                Operation.output.isnot(None),
                Operation.output != ''
            ).order_by(Operation.created_at.desc()).limit(1000).all()
            
            for operation in operations:
                try:
                    # Create a unique identifier for the operation log
                    log_id = f"operation_{operation.id}"
                    
                    # Check if already indexed and not forced to reindex
                    if not force_reindex:
                        cursor.execute(
                            "SELECT indexed_at FROM content_index WHERE file_path = ?",
                            (log_id,)
                        )
                        existing = cursor.fetchone()
                        if existing:
                            continue
                    
                    # Extract content and keywords
                    content = operation.output or ""
                    title = f"Operation {operation.id}: {operation.operation_type}"
                    keywords = self._extract_log_keywords(content, operation)
                    
                    # Insert into index
                    cursor.execute('''
                        INSERT OR REPLACE INTO content_index 
                        (file_path, content_type, title, content, keywords, last_modified, indexed_at, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        log_id,
                        'operation_log',
                        title,
                        content,
                        keywords,
                        operation.created_at.timestamp() if operation.created_at else datetime.now().timestamp(),
                        datetime.now().timestamp(),
                        len(content)
                    ))
                    
                    indexed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error indexing operation {operation.id}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error indexing operation logs: {e}")
        
        return indexed_count
    
    def _extract_playbook_title(self, content: str, filename: str) -> str:
        """Extract title from playbook content."""
        # Look for name field in YAML
        name_match = re.search(r'^\s*-\s*name:\s*(.+)$', content, re.MULTILINE)
        if name_match:
            return name_match.group(1).strip().strip('"\'')
        
        # Fallback to filename
        return filename.replace('.yml', '').replace('_', ' ').title()
    
    def _extract_playbook_keywords(self, content: str) -> str:
        """Extract keywords from playbook content."""
        keywords = set()
        
        # Extract common Ansible modules and tasks
        module_matches = re.findall(r'^\s*-\s*(\w+):', content, re.MULTILINE)
        keywords.update(module_matches)
        
        # Extract service names and common terms
        service_matches = re.findall(r'(microk8s|kubernetes|docker|nginx|apache|mysql|postgresql)', content, re.IGNORECASE)
        keywords.update(service_matches)
        
        # Extract file paths and names
        path_matches = re.findall(r'/([\w.-]+)', content)
        keywords.update(path_matches)
        
        return ', '.join(sorted(keywords))
    
    def _extract_doc_title(self, content: str, filename: str) -> str:
        """Extract title from documentation content."""
        # Look for first heading
        heading_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()
        
        # Fallback to filename
        return filename.replace('.md', '').replace('_', ' ').title()
    
    def _extract_doc_keywords(self, content: str) -> str:
        """Extract keywords from documentation content."""
        keywords = set()
        
        # Extract headings
        heading_matches = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        keywords.update(heading_matches)
        
        # Extract code blocks and technical terms
        code_matches = re.findall(r'`([^`]+)`', content)
        keywords.update(code_matches)
        
        # Extract common technical terms
        tech_terms = re.findall(r'\b(microk8s|kubernetes|ansible|docker|cluster|node|pod|service|deployment)\b', content, re.IGNORECASE)
        keywords.update(tech_terms)
        
        return ', '.join(sorted(keywords))
    
    def _extract_log_keywords(self, content: str, operation) -> str:
        """Extract keywords from operation log content."""
        keywords = set()
        
        # Add operation type
        keywords.add(operation.operation_type)
        
        # Add status
        if operation.status:
            keywords.add(operation.status)
        
        # Extract error patterns
        error_matches = re.findall(r'(error|failed|exception|timeout)', content, re.IGNORECASE)
        keywords.update(error_matches)
        
        # Extract service names
        service_matches = re.findall(r'(microk8s|kubernetes|docker|nginx|apache)', content, re.IGNORECASE)
        keywords.update(service_matches)
        
        # Extract IP addresses and hostnames
        ip_matches = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', content)
        keywords.update(ip_matches)
        
        hostname_matches = re.findall(r'\b[a-zA-Z0-9-]+\.local\b', content)
        keywords.update(hostname_matches)
        
        return ', '.join(sorted(keywords))
    
    def search_content(self, query: str, content_types: List[str] = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Search indexed content.
        
        Args:
            query: Search query
            content_types: List of content types to search (playbook, documentation, operation_log)
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        if not query.strip():
            return []
        
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()
            
            # Build search query
            search_terms = query.lower().split()
            where_conditions = []
            params = []
            
            # Search in content and keywords
            for term in search_terms:
                where_conditions.append("(LOWER(content) LIKE ? OR LOWER(keywords) LIKE ? OR LOWER(title) LIKE ?)")
                params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
            
            where_clause = " OR ".join(where_conditions)
            
            # Add content type filter
            if content_types:
                type_conditions = " OR ".join(["content_type = ?" for _ in content_types])
                where_clause = f"({where_clause}) AND ({type_conditions})"
                params.extend(content_types)
            
            # Build final query
            sql = f"""
                SELECT file_path, content_type, title, content, keywords, last_modified, indexed_at
                FROM content_index
                WHERE {where_clause}
                ORDER BY 
                    CASE 
                        WHEN LOWER(title) LIKE ? THEN 1
                        WHEN LOWER(keywords) LIKE ? THEN 2
                        ELSE 3
                    END,
                    indexed_at DESC
            """
            
            # Add title/keyword preference
            params.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
            
            if limit:
                sql += f" LIMIT {limit}"
            else:
                sql += f" LIMIT {self.config.get('max_search_results', 50)}"
            
            cursor.execute(sql, params)
            results = []
            
            for row in cursor.fetchall():
                results.append({
                    'file_path': row[0],
                    'content_type': row[1],
                    'title': row[2],
                    'content': row[3],
                    'keywords': row[4],
                    'last_modified': row[5],
                    'indexed_at': row[6]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return []
    
    def get_content_statistics(self) -> Dict[str, Any]:
        """Get statistics about indexed content."""
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()
            
            # Get counts by content type
            cursor.execute("SELECT content_type, COUNT(*) FROM content_index GROUP BY content_type")
            type_counts = dict(cursor.fetchall())
            
            # Get total size
            cursor.execute("SELECT SUM(file_size) FROM content_index")
            total_size = cursor.fetchone()[0] or 0
            
            # Get last indexed time
            cursor.execute("SELECT MAX(indexed_at) FROM content_index")
            last_indexed = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_documents': sum(type_counts.values()),
                'type_counts': type_counts,
                'total_size_bytes': total_size,
                'last_indexed': last_indexed
            }
            
        except Exception as e:
            logger.error(f"Error getting content statistics: {e}")
            return {
                'total_documents': 0,
                'type_counts': {},
                'total_size_bytes': 0,
                'last_indexed': None
            }

# Global instance
_content_search_service = None

def get_content_search_service() -> Optional[ContentSearchService]:
    """Get the global content search service instance."""
    global _content_search_service
    if _content_search_service is None:
        try:
            from ..utils.ai_config import get_ai_config
            ai_config = get_ai_config()
            
            if ai_config.is_searchable_content_enabled():
                search_config = ai_config.get_searchable_content_config()
                _content_search_service = ContentSearchService(search_config)
                logger.info("Content search service initialized successfully")
            else:
                logger.info("Content search service is disabled in configuration")
                
        except Exception as e:
            logger.error(f"Error initializing content search service: {e}")
    
    return _content_search_service

def reset_content_search_service():
    """Reset the global content search service instance."""
    global _content_search_service
    _content_search_service = None
