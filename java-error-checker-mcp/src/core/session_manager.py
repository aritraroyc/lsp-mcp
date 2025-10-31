"""
Session Manager for Java Error Checker MCP Service

Manages client sessions, workspace directories, and project structure.

Design Patterns Used:
- Singleton: Single global SessionManager instance
- Repository: CRUD operations for Session objects
- Strategy: Path resolution strategies for different file types
- Observer: Change notification system (future enhancement)
"""

import os
import shutil
import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a client session.

    Attributes:
        session_id: Unique identifier for the session
        workspace_path: Path to the session's workspace directory
        project_name: Name of the Java project
        created_at: Timestamp when session was created
        last_accessed: Timestamp of last activity
    """
    session_id: str
    workspace_path: Path
    project_name: str
    created_at: float
    last_accessed: float


class PathResolutionStrategy:
    """Strategy pattern for resolving file paths in workspace.

    This allows different path resolution rules to be swapped out easily.
    """

    def resolve_path(self, workspace_path: Path, file_path: str) -> Path:
        """Resolve a relative file path to absolute workspace path.

        Args:
            workspace_path: Base workspace path
            file_path: Relative file path

        Returns:
            Absolute path in workspace
        """
        raise NotImplementedError


class JavaMainPathStrategy(PathResolutionStrategy):
    """Strategy for main source files (src/main/java/)."""

    def resolve_path(self, workspace_path: Path, file_path: str) -> Path:
        if file_path.startswith("src/"):
            return workspace_path / file_path
        return workspace_path / "src" / "main" / "java" / file_path


class JavaTestPathStrategy(PathResolutionStrategy):
    """Strategy for test source files (src/test/java/)."""

    def resolve_path(self, workspace_path: Path, file_path: str) -> Path:
        if file_path.startswith("src/"):
            return workspace_path / file_path
        # If starts with "test/", put in src/test/java
        if file_path.startswith("test/"):
            return workspace_path / "src" / "test" / "java" / file_path[5:]
        return workspace_path / "src" / "test" / "java" / file_path


class SessionRepository:
    """Repository pattern for Session persistence.

    Encapsulates session storage and retrieval logic.
    Thread-safe for concurrent access.
    """

    def __init__(self):
        """Initialize the repository."""
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()

    def create(self, session: Session) -> None:
        """Store a new session.

        Args:
            session: Session object to store
        """
        with self._lock:
            self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session object or None if not found
        """
        with self._lock:
            return self._sessions.get(session_id)

    def update(self, session: Session) -> bool:
        """Update an existing session.

        Args:
            session: Session object with updated data

        Returns:
            True if updated, False if not found
        """
        with self._lock:
            if session.session_id in self._sessions:
                self._sessions[session.session_id] = session
                return True
            return False

    def delete(self, session_id: str) -> bool:
        """Remove a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_all(self) -> List[Session]:
        """Get all sessions.

        Returns:
            List of all Session objects
        """
        with self._lock:
            return list(self._sessions.values())

    def clear(self) -> None:
        """Remove all sessions."""
        with self._lock:
            self._sessions.clear()


class SessionManager:
    """Manages sessions and workspace directories for Java projects.

    This class implements:
    - Singleton pattern (optional, see get_instance())
    - Repository pattern for data access
    - Strategy pattern for path resolution
    - Observer pattern hooks for future extensions
    """

    _instance = None
    _lock = Lock()

    def __init__(self, base_workspace_dir: str = "/tmp/jdtls-workspaces"):
        """Initialize the session manager.

        Args:
            base_workspace_dir: Base directory for all workspace sessions
        """
        self.base_workspace_dir = Path(base_workspace_dir)
        self.repository = SessionRepository()
        self.path_strategy = JavaMainPathStrategy()

        # Observer callbacks for session events
        self._on_session_created: List[Callable] = []
        self._on_session_deleted: List[Callable] = []

        self._ensure_base_directory()
        logger.info(f"SessionManager initialized with base dir: {base_workspace_dir}")

    @classmethod
    def get_instance(cls, base_workspace_dir: str = "/tmp/jdtls-workspaces") -> "SessionManager":
        """Get or create singleton instance (optional).

        Args:
            base_workspace_dir: Base directory for workspaces

        Returns:
            SessionManager singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(base_workspace_dir)
        return cls._instance

    def _ensure_base_directory(self) -> None:
        """Ensure the base workspace directory exists."""
        self.base_workspace_dir.mkdir(parents=True, exist_ok=True)

    def set_path_strategy(self, strategy: PathResolutionStrategy) -> None:
        """Set the path resolution strategy.

        Args:
            strategy: PathResolutionStrategy implementation
        """
        self.path_strategy = strategy
        logger.info(f"Path strategy set to {strategy.__class__.__name__}")

    def register_on_session_created(self, callback: Callable) -> None:
        """Register a callback for when sessions are created.

        Args:
            callback: Function to call when session is created
        """
        self._on_session_created.append(callback)

    def register_on_session_deleted(self, callback: Callable) -> None:
        """Register a callback for when sessions are deleted.

        Args:
            callback: Function to call when session is deleted
        """
        self._on_session_deleted.append(callback)

    def _notify_session_created(self, session: Session) -> None:
        """Notify observers that a session was created.

        Args:
            session: The created session
        """
        for callback in self._on_session_created:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Error in session_created callback: {e}")

    def _notify_session_deleted(self, session_id: str) -> None:
        """Notify observers that a session was deleted.

        Args:
            session_id: The deleted session ID
        """
        for callback in self._on_session_deleted:
            try:
                callback(session_id)
            except Exception as e:
                logger.error(f"Error in session_deleted callback: {e}")

    def create_session(self, project_name: str = "default") -> str:
        """Create a new session with a unique workspace.

        Args:
            project_name: Name of the Java project

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        workspace_path = self.base_workspace_dir / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Create standard Java project structure
        src_main_java = workspace_path / "src" / "main" / "java"
        src_test_java = workspace_path / "src" / "test" / "java"
        src_main_java.mkdir(parents=True, exist_ok=True)
        src_test_java.mkdir(parents=True, exist_ok=True)

        current_time = time.time()
        session = Session(
            session_id=session_id,
            workspace_path=workspace_path,
            project_name=project_name,
            created_at=current_time,
            last_accessed=current_time
        )

        self.repository.create(session)
        self._notify_session_created(session)
        logger.info(f"Created session {session_id} for project {project_name}")

        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID and update last_accessed timestamp.

        Args:
            session_id: Session ID

        Returns:
            Session object or None if not found
        """
        session = self.repository.get(session_id)
        if session:
            session.last_accessed = time.time()
            self.repository.update(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up its workspace.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if session not found
        """
        session = self.repository.get(session_id)
        if not session:
            return False

        # Clean up workspace directory
        try:
            if session.workspace_path.exists():
                shutil.rmtree(session.workspace_path)
                logger.info(f"Deleted workspace for session {session_id}")
        except Exception as e:
            logger.error(f"Error deleting workspace for session {session_id}: {e}")

        # Remove from repository
        self.repository.delete(session_id)
        self._notify_session_deleted(session_id)
        return True

    def write_file(self, session_id: str, file_path: str, content: str) -> bool:
        """Write a Java file to the session workspace.

        Args:
            session_id: Session ID
            file_path: Relative file path (e.g., "com/example/Main.java")
            content: File content

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return False

        # Use strategy to resolve path
        full_path = self.path_strategy.resolve_path(session.workspace_path, file_path)

        # Ensure parent directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            full_path.write_text(content, encoding='utf-8')
            logger.info(f"Wrote file {file_path} to session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    def write_multiple_files(self, session_id: str, files: List[Dict[str, str]]) -> Dict[str, any]:
        """Write multiple Java files to the session workspace in a batch operation.

        Args:
            session_id: Session ID
            files: List of dicts with 'file_path' and 'content' keys

        Returns:
            Dict with success count, failure count, and details
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return {
                "success": False,
                "error": "Session not found",
                "written": 0,
                "failed": 0
            }

        written = 0
        failed = 0
        failed_files = []

        for file_info in files:
            file_path = file_info.get("file_path")
            content = file_info.get("content")

            if not file_path or content is None:
                failed += 1
                failed_files.append({
                    "file_path": file_path or "unknown",
                    "error": "Missing file_path or content"
                })
                continue

            # Use strategy to resolve path
            full_path = self.path_strategy.resolve_path(session.workspace_path, file_path)

            # Ensure parent directories exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                full_path.write_text(content, encoding='utf-8')
                written += 1
                logger.info(f"Wrote file {file_path} to session {session_id}")
            except Exception as e:
                failed += 1
                failed_files.append({
                    "file_path": file_path,
                    "error": str(e)
                })
                logger.error(f"Error writing file {file_path}: {e}")

        result = {
            "success": True,
            "written": written,
            "failed": failed,
            "total": len(files)
        }

        if failed_files:
            result["failed_files"] = failed_files

        logger.info(f"Batch write to session {session_id}: {written} written, {failed} failed")
        return result

    def read_file(self, session_id: str, file_path: str) -> Optional[str]:
        """Read a file from the session workspace.

        Args:
            session_id: Session ID
            file_path: Relative file path

        Returns:
            File content or None if not found
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Use strategy to resolve path
        full_path = self.path_strategy.resolve_path(session.workspace_path, file_path)

        try:
            return full_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def list_files(self, session_id: str) -> List[str]:
        """List all Java files in the session workspace.

        Args:
            session_id: Session ID

        Returns:
            List of relative file paths
        """
        session = self.get_session(session_id)
        if not session:
            return []

        java_files = []
        for java_file in session.workspace_path.rglob("*.java"):
            relative_path = java_file.relative_to(session.workspace_path)
            java_files.append(str(relative_path))

        return java_files

    def get_workspace_path(self, session_id: str) -> Optional[Path]:
        """Get the workspace path for a session.

        Args:
            session_id: Session ID

        Returns:
            Workspace path or None if session not found
        """
        session = self.get_session(session_id)
        return session.workspace_path if session else None

    def refresh_session(self, session_id: str) -> bool:
        """Refresh a session to extend its timeout.

        This is useful for long-running agentic workflows.

        Args:
            session_id: Session ID

        Returns:
            True if session was refreshed, False if not found
        """
        session = self.repository.get(session_id)
        if not session:
            return False

        session.last_accessed = time.time()
        self.repository.update(session)
        logger.info(f"Refreshed session {session_id}")
        return True

    def get_session_info(self, session_id: str) -> Optional[Dict[str, any]]:
        """Get detailed information about a session.

        Args:
            session_id: Session ID

        Returns:
            Dict with session information or None if not found
        """
        session = self.repository.get(session_id)
        if not session:
            return None

        current_time = time.time()
        java_files = self.list_files(session_id)

        return {
            "session_id": session.session_id,
            "project_name": session.project_name,
            "workspace_path": str(session.workspace_path),
            "created_at": session.created_at,
            "last_accessed": session.last_accessed,
            "age_seconds": current_time - session.created_at,
            "idle_seconds": current_time - session.last_accessed,
            "file_count": len(java_files),
            "files": java_files
        }

    def cleanup_old_sessions(self, max_idle_seconds: int = 3600) -> int:
        """Clean up sessions idle longer than max_idle_seconds.

        Args:
            max_idle_seconds: Maximum idle time in seconds

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        sessions_to_delete = []

        for session in self.repository.list_all():
            if current_time - session.last_accessed > max_idle_seconds:
                sessions_to_delete.append(session.session_id)

        for session_id in sessions_to_delete:
            self.delete_session(session_id)
            logger.info(f"Cleaned up idle session {session_id}")

        return len(sessions_to_delete)
