"""
Chat Session Manager for AI Assistant.

This module manages multiple chat sessions, allowing users to have
separate conversations for different topics or issues.
"""

import logging
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Represents a single chat message."""
    id: str
    session_id: str
    sender: str  # 'user' or 'assistant'
    message: str
    timestamp: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ChatSession:
    """Represents a chat session."""
    id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int
    last_message: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ChatSessionManager:
    """Manages multiple chat sessions for the AI assistant."""
    
    def __init__(self, data_dir: str = "data/chat_sessions"):
        """
        Initialize the chat session manager.
        
        Args:
            data_dir: Directory to store chat session data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_db = self.data_dir / "sessions.db"
        self.messages_db = self.data_dir / "messages.db"
        
        self._initialize_databases()
    
    def _initialize_databases(self):
        """Initialize the chat session databases."""
        try:
            # Sessions database
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    last_message TEXT,
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC)
            ''')
            
            conn.commit()
            conn.close()
            
            # Messages database
            conn = sqlite3.connect(str(self.messages_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id, timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing chat session databases: {e}")
    
    def create_session(self, title: str = None, metadata: Dict[str, Any] = None) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            title: Session title (auto-generated if None)
            metadata: Additional metadata
            
        Returns:
            Created chat session
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(datetime.now())}"
        
        if not title:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if metadata is None:
            metadata = {}
        
        session = ChatSession(
            id=session_id,
            title=title,
            created_at=datetime.now().timestamp(),
            updated_at=datetime.now().timestamp(),
            message_count=0,
            last_message="",
            metadata=metadata
        )
        
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO chat_sessions 
                (id, title, created_at, updated_at, message_count, last_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.id,
                session.title,
                session.created_at,
                session.updated_at,
                session.message_count,
                session.last_message,
                json.dumps(session.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created new chat session: {session.id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a chat session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Chat session or None if not found
        """
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, updated_at, message_count, last_message, metadata
                FROM chat_sessions WHERE id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                metadata = json.loads(row[6]) if row[6] else {}
                return ChatSession(
                    id=row[0],
                    title=row[1],
                    created_at=row[2],
                    updated_at=row[3],
                    message_count=row[4],
                    last_message=row[5],
                    metadata=metadata
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {e}")
            return None
    
    def list_sessions(self, limit: int = 50) -> List[ChatSession]:
        """
        List all chat sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of chat sessions ordered by last update
        """
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, updated_at, message_count, last_message, metadata
                FROM chat_sessions
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                metadata = json.loads(row[6]) if row[6] else {}
                sessions.append(ChatSession(
                    id=row[0],
                    title=row[1],
                    created_at=row[2],
                    updated_at=row[3],
                    message_count=row[4],
                    last_message=row[5],
                    metadata=metadata
                ))
            
            conn.close()
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing chat sessions: {e}")
            return []
    
    def update_session(self, session_id: str, title: str = None, metadata: Dict[str, Any] = None) -> bool:
        """
        Update a chat session.
        
        Args:
            session_id: Session ID
            title: New title (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if updated successfully
        """
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            # Get current session
            cursor.execute('SELECT metadata FROM chat_sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
            
            current_metadata = json.loads(row[0]) if row[0] else {}
            
            # Update fields
            update_fields = []
            params = []
            
            if title:
                update_fields.append('title = ?')
                params.append(title)
            
            if metadata is not None:
                current_metadata.update(metadata)
                update_fields.append('metadata = ?')
                params.append(json.dumps(current_metadata))
            
            update_fields.append('updated_at = ?')
            params.append(datetime.now().timestamp())
            params.append(session_id)
            
            cursor.execute(f'''
                UPDATE chat_sessions 
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', params)
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating chat session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a chat session and all its messages.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted successfully
        """
        try:
            # Delete messages first
            conn = sqlite3.connect(str(self.messages_db))
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            
            # Delete session
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted chat session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chat session {session_id}: {e}")
            return False
    
    def add_message(self, session_id: str, sender: str, message: str, metadata: Dict[str, Any] = None) -> ChatMessage:
        """
        Add a message to a chat session.
        
        Args:
            session_id: Session ID
            sender: Message sender ('user' or 'assistant')
            message: Message content
            metadata: Additional metadata
            
        Returns:
            Created chat message
        """
        if metadata is None:
            metadata = {}
        
        message_id = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(datetime.now())}"
        timestamp = datetime.now().timestamp()
        
        chat_message = ChatMessage(
            id=message_id,
            session_id=session_id,
            sender=sender,
            message=message,
            timestamp=timestamp,
            metadata=metadata
        )
        
        try:
            # Add message to messages database
            conn = sqlite3.connect(str(self.messages_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO chat_messages 
                (id, session_id, sender, message, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                chat_message.id,
                chat_message.session_id,
                chat_message.sender,
                chat_message.message,
                chat_message.timestamp,
                json.dumps(chat_message.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # Update session
            self._update_session_after_message(session_id, message, timestamp)
            
            return chat_message
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            raise
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[ChatMessage]:
        """
        Get messages from a chat session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of chat messages ordered by timestamp
        """
        try:
            conn = sqlite3.connect(str(self.messages_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, session_id, sender, message, timestamp, metadata
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                metadata = json.loads(row[5]) if row[5] else {}
                messages.append(ChatMessage(
                    id=row[0],
                    session_id=row[1],
                    sender=row[2],
                    message=row[3],
                    timestamp=row[4],
                    metadata=metadata
                ))
            
            conn.close()
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
    
    def _update_session_after_message(self, session_id: str, last_message: str, timestamp: float):
        """Update session after adding a message."""
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            # Update message count and last message
            cursor.execute('''
                UPDATE chat_sessions 
                SET message_count = message_count + 1,
                    last_message = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (last_message[:200], timestamp, session_id))  # Truncate last message
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating session after message: {e}")
    
    def search_sessions(self, query: str) -> List[ChatSession]:
        """
        Search chat sessions by title or content.
        
        Args:
            query: Search query
            
        Returns:
            List of matching sessions
        """
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, updated_at, message_count, last_message, metadata
                FROM chat_sessions
                WHERE title LIKE ? OR last_message LIKE ?
                ORDER BY updated_at DESC
            ''', (f"%{query}%", f"%{query}%"))
            
            sessions = []
            for row in cursor.fetchall():
                metadata = json.loads(row[6]) if row[6] else {}
                sessions.append(ChatSession(
                    id=row[0],
                    title=row[1],
                    created_at=row[2],
                    updated_at=row[3],
                    message_count=row[4],
                    last_message=row[5],
                    metadata=metadata
                ))
            
            conn.close()
            return sessions
            
        except Exception as e:
            logger.error(f"Error searching chat sessions: {e}")
            return []
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics about chat sessions."""
        try:
            conn = sqlite3.connect(str(self.sessions_db))
            cursor = conn.cursor()
            
            # Get total sessions
            cursor.execute('SELECT COUNT(*) FROM chat_sessions')
            total_sessions = cursor.fetchone()[0]
            
            # Get total messages
            cursor.execute('SELECT SUM(message_count) FROM chat_sessions')
            total_messages = cursor.fetchone()[0] or 0
            
            # Get recent activity (sessions created in last 7 days)
            week_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            cursor.execute('SELECT COUNT(*) FROM chat_sessions WHERE created_at > ?', (week_ago,))
            recent_sessions = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'recent_sessions_7d': recent_sessions
            }
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {
                'total_sessions': 0,
                'total_messages': 0,
                'recent_sessions_7d': 0
            }

# Global instance
_chat_session_manager = None

def get_chat_session_manager() -> Optional[ChatSessionManager]:
    """Get the global chat session manager instance."""
    global _chat_session_manager
    if _chat_session_manager is None:
        try:
            from ..utils.ai_config import get_ai_config
            ai_config = get_ai_config()
            
            if ai_config.should_allow_multiple_chats():
                _chat_session_manager = ChatSessionManager()
                logger.info("Chat session manager initialized successfully")
            else:
                logger.info("Multiple chat sessions are disabled in configuration")
                
        except Exception as e:
            logger.error(f"Error initializing chat session manager: {e}")
    
    return _chat_session_manager

def reset_chat_session_manager():
    """Reset the global chat session manager instance."""
    global _chat_session_manager
    _chat_session_manager = None
