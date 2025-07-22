"""
Enhanced Session Management for MCP Server
"""

import uuid
import time
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class MCPSession:
    """MCP Session data structure"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    user_email: Optional[str] = None
    initialized: bool = False
    client_info: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = time.time()
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if session is expired"""
        return (time.time() - self.last_accessed) > timeout_seconds

class SessionManager:
    """Enhanced session manager for MCP server"""
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, MCPSession] = {}
        self.session_timeout = session_timeout
        self._lock = Lock()
        logger.info(f"SessionManager initialized with {session_timeout}s timeout")
    
    def create_session(self, session_id: Optional[str] = None) -> MCPSession:
        """Create a new session"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        with self._lock:
            session = MCPSession(session_id=session_id)
            self.sessions[session_id] = session
            logger.info(f"Created new session: {session_id}")
            return session
    
    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """Get session by ID"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                if session.is_expired(self.session_timeout):
                    logger.info(f"Session {session_id} expired, removing")
                    del self.sessions[session_id]
                    return None
                session.touch()
                return session
            return None
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> MCPSession:
        """Get existing session or create new one"""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        # Create new session
        return self.create_session(session_id)
    
    def initialize_session(self, session_id: str, client_info: Dict[str, Any], 
                          capabilities: Dict[str, Any]) -> bool:
        """Initialize session with client info"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot initialize non-existent session: {session_id}")
            return False
        
        session.client_info = client_info
        session.capabilities = capabilities
        session.initialized = True
        session.touch()
        
        logger.info(f"Session {session_id} initialized with client: {client_info.get('name', 'unknown')}")
        return True
    
    def is_session_initialized(self, session_id: str) -> bool:
        """Check if session is initialized"""
        session = self.get_session(session_id)
        return session.initialized if session else False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        with self._lock:
            expired_sessions = [
                sid for sid, session in self.sessions.items()
                if session.is_expired(self.session_timeout)
            ]
            
            for sid in expired_sessions:
                del self.sessions[sid]
                logger.info(f"Cleaned up expired session: {sid}")
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        with self._lock:
            return len(self.sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for debugging"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_accessed": session.last_accessed,
            "age_seconds": time.time() - session.created_at,
            "idle_seconds": time.time() - session.last_accessed,
            "user_email": session.user_email,
            "initialized": session.initialized,
            "client_name": session.client_info.get("name", "unknown"),
            "client_version": session.client_info.get("version", "unknown")
        }

# Global session manager instance
session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    return session_manager

# Cleanup task (could be run periodically)
def cleanup_sessions():
    """Cleanup expired sessions"""
    session_manager.cleanup_expired_sessions()

logger.info("Session manager initialized")
