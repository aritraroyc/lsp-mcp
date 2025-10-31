"""
LangGraph Integration for Java Error Checker MCP Service

Provides utilities and tools for consuming the MCP service from LangGraph agents.
"""

import json
import httpx
from typing import Any, Dict, List, Optional, Callable
from functools import wraps


class JavaErrorCheckerClient:
    """
    Client for consuming Java Error Checker MCP service from LangGraph agents.

    This client provides a simple Python interface to the MCP service over HTTP/SSE.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the MCP server (e.g., "http://localhost:8000")
        """
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool via HTTP.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response as dict
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/sse",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 1
                }
            )
            response.raise_for_status()
            result = response.json()

            # Parse the result
            if "result" in result and "content" in result["result"]:
                content_text = result["result"]["content"][0]["text"]
                return json.loads(content_text)
            elif "error" in result:
                raise Exception(f"MCP Error: {result['error']}")
            else:
                raise Exception(f"Unexpected response format: {result}")

    async def create_session(self, project_name: str = "langgraph-project") -> str:
        """
        Create a new Java project session.

        Args:
            project_name: Name of the Java project

        Returns:
            Session ID
        """
        result = await self._call_tool("create_session", {"project_name": project_name})
        self.session_id = result["session_id"]
        return self.session_id

    async def write_file(self, file_path: str, content: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Write a Java file to the session.

        Args:
            file_path: Relative path to Java file
            content: Java source code
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("write_java_file", {
            "session_id": sid,
            "file_path": file_path,
            "content": content
        })

    async def write_multiple_files(
        self,
        files: List[Dict[str, str]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write multiple Java files in batch.

        Args:
            files: List of dicts with 'file_path' and 'content' keys
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict with written/failed counts
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("write_multiple_files", {
            "session_id": sid,
            "files": files
        })

    async def check_errors(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check for compilation errors.

        Args:
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict with error_count and errors list
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("check_errors", {"session_id": sid})

    async def get_recommendations(
        self,
        error: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recommendations for fixing an error.

        Args:
            error: Error object from check_errors
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict with recommendations list
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("get_recommendations", {
            "session_id": sid,
            "error": error
        })

    async def list_files(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List all Java files in the session.

        Args:
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict with file list
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("list_files", {"session_id": sid})

    async def read_file(self, file_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Read a Java file from the session.

        Args:
            file_path: Relative path to Java file
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict with file content
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("read_file", {
            "session_id": sid,
            "file_path": file_path
        })

    async def refresh_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Refresh session to extend timeout.

        Args:
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("refresh_session", {"session_id": sid})

    async def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session information.

        Args:
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict with session details
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        return await self._call_tool("get_session_info", {"session_id": sid})

    async def delete_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a session and cleanup.

        Args:
            session_id: Session ID (uses stored session_id if not provided)

        Returns:
            Response dict
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id available. Call create_session() first.")

        result = await self._call_tool("delete_session", {"session_id": sid})

        # Clear stored session_id if it was the one deleted
        if sid == self.session_id:
            self.session_id = None

        return result

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the MCP server is healthy.

        Returns:
            Health status dict
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()


# LangGraph Tool Wrappers
def create_langgraph_tools(client: JavaErrorCheckerClient) -> List[Callable]:
    """
    Create LangGraph-compatible tool functions from the MCP client.

    Args:
        client: JavaErrorCheckerClient instance

    Returns:
        List of tool functions suitable for LangGraph
    """

    async def create_java_session(project_name: str = "langgraph-project") -> str:
        """Create a new Java project session for code generation."""
        result = await client.create_session(project_name)
        return f"Session created: {result}"

    async def write_java_files(files_json: str) -> str:
        """
        Write multiple Java files to the session.

        Args:
            files_json: JSON string containing array of {file_path, content} objects

        Example:
            files_json = '[{"file_path": "com/example/Main.java", "content": "..."}]'
        """
        files = json.loads(files_json)
        result = await client.write_multiple_files(files)
        return json.dumps(result)

    async def check_java_errors() -> str:
        """Check for Java compilation errors in the current session."""
        result = await client.check_errors()
        return json.dumps(result)

    async def get_error_fix_recommendations(error_json: str) -> str:
        """
        Get recommendations for fixing a Java compilation error.

        Args:
            error_json: JSON string containing error object

        Example:
            error_json = '{"file": "Main.java", "line": 10, "message": "cannot find symbol"}'
        """
        error = json.loads(error_json)
        result = await client.get_recommendations(error)
        return json.dumps(result)

    async def list_java_files() -> str:
        """List all Java files in the current session."""
        result = await client.list_files()
        return json.dumps(result)

    async def refresh_java_session() -> str:
        """Refresh the session to extend timeout for long-running workflows."""
        result = await client.refresh_session()
        return json.dumps(result)

    async def get_java_session_info() -> str:
        """Get information about the current Java project session."""
        result = await client.get_session_info()
        return json.dumps(result)

    async def cleanup_java_session() -> str:
        """Delete the current session and cleanup workspace."""
        result = await client.delete_session()
        return json.dumps(result)

    return [
        create_java_session,
        write_java_files,
        check_java_errors,
        get_error_fix_recommendations,
        list_java_files,
        refresh_java_session,
        get_java_session_info,
        cleanup_java_session,
    ]


# Context manager for automatic cleanup
class JavaProjectSession:
    """
    Context manager for Java project sessions with automatic cleanup.

    Usage:
        async with JavaProjectSession(client, "my-project") as session:
            await session.write_multiple_files([...])
            errors = await session.check_errors()
    """

    def __init__(self, client: JavaErrorCheckerClient, project_name: str = "project"):
        """
        Initialize session context.

        Args:
            client: JavaErrorCheckerClient instance
            project_name: Name of the Java project
        """
        self.client = client
        self.project_name = project_name
        self.session_id = None

    async def __aenter__(self):
        """Enter context and create session."""
        self.session_id = await self.client.create_session(self.project_name)
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and cleanup session."""
        if self.session_id:
            try:
                await self.client.delete_session(self.session_id)
            except Exception as e:
                print(f"Error cleaning up session: {e}")
        return False
