"""
Base MCP Server for Java Error Checking

This module contains the core business logic for Java error checking that is
independent of transport mechanisms (stdio, HTTP, etc.).

It implements the Server design pattern, separating transport-specific logic
from reusable business logic.
"""

import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from mcp.server import Server
from mcp.types import Tool, TextContent

from .session_manager import SessionManager
from .jdtls_client import JDTLSClient
from .error_recommendation_engine import ErrorRecommendationEngine

logger = logging.getLogger(__name__)


class ServerTransport(ABC):
    """Abstract base class for MCP server transports.

    This class defines the interface that different transport implementations
    (stdio, HTTP/SSE, WebSocket, etc.) must implement.
    """

    @abstractmethod
    async def send_response(self, response: Dict[str, Any]) -> List[TextContent]:
        """Convert a response dict to MCP TextContent format.

        Args:
            response: Response dictionary from business logic

        Returns:
            List of TextContent objects for MCP protocol
        """
        pass

    @abstractmethod
    async def run(self, server: "JavaErrorCheckerServer") -> None:
        """Start the transport server.

        Args:
            server: JavaErrorCheckerServer instance to bind to
        """
        pass


class JavaErrorCheckerServer:
    """Core MCP Server for Java error checking.

    This is the business logic layer that is transport-agnostic.
    All transport-specific code is delegated to ServerTransport implementations.
    """

    def __init__(self):
        """Initialize the server with dependencies."""
        self.server = Server("java-error-checker")
        self.session_manager = SessionManager()
        self.jdtls_client = JDTLSClient()
        self.recommendation_engine = ErrorRecommendationEngine()

        logger.info("Java Error Checker MCP Server initialized")

    def _register_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return self._get_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Route tool calls to appropriate handlers."""
            return await self._route_tool_call(name, arguments)

    def _get_tools(self) -> list[Tool]:
        """Return list of available MCP tools.

        This method defines all tool specifications in one place,
        making it easier to maintain and extend.
        """
        return [
            Tool(
                name="create_session",
                description="Create a new Java project session with isolated workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the Java project (optional)",
                            "default": "default"
                        }
                    }
                }
            ),
            Tool(
                name="write_java_file",
                description="Write a Java source file to the session workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID from create_session"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Relative path to Java file (e.g., 'com/example/Main.java')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Java source code content"
                        }
                    },
                    "required": ["session_id", "file_path", "content"]
                }
            ),
            Tool(
                name="write_multiple_files",
                description="Write multiple Java source files to the session workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID from create_session"
                        },
                        "files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "file_path": {"type": "string"},
                                    "content": {"type": "string"}
                                },
                                "required": ["file_path", "content"]
                            },
                            "description": "Array of {file_path, content} objects"
                        }
                    },
                    "required": ["session_id", "files"]
                }
            ),
            Tool(
                name="check_errors",
                description="Check for compilation errors in the Java project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID from create_session"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="list_files",
                description="List all Java files in the session workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID from create_session"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="read_file",
                description="Read the content of a Java file from the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID from create_session"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Relative path to Java file"
                        }
                    },
                    "required": ["session_id", "file_path"]
                }
            ),
            Tool(
                name="delete_session",
                description="Delete a session and clean up its workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to delete"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_recommendations",
                description="Get recommendations for fixing a compilation error",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID"
                        },
                        "error": {
                            "type": "object",
                            "description": "Error object from check_errors"
                        }
                    },
                    "required": ["session_id", "error"]
                }
            ),
            Tool(
                name="refresh_session",
                description="Refresh session timeout to prevent expiration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to refresh"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_session_info",
                description="Get metadata about a session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
        ]

    async def _route_tool_call(self, name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """Route tool calls to appropriate handler methods.

        This method implements the Command pattern, dispatching to specific
        handlers based on tool name.
        """
        handlers = {
            "create_session": self._handle_create_session,
            "write_java_file": self._handle_write_java_file,
            "write_multiple_files": self._handle_write_multiple_files,
            "check_errors": self._handle_check_errors,
            "list_files": self._handle_list_files,
            "read_file": self._handle_read_file,
            "delete_session": self._handle_delete_session,
            "get_recommendations": self._handle_get_recommendations,
            "refresh_session": self._handle_refresh_session,
            "get_session_info": self._handle_get_session_info,
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(type="text", text=str({
                "status": "error",
                "message": f"Unknown tool: {name}"
            }))]

        return await handler(arguments)

    # Tool handler methods
    async def _handle_create_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle create_session tool call."""
        project_name = arguments.get("project_name", "default")

        session_id = self.session_manager.create_session(project_name)

        response = {
            "status": "success",
            "session_id": session_id,
            "project_name": project_name,
            "message": f"Session created successfully. Project: {project_name}"
        }

        return await self._format_response(response)

    async def _handle_write_java_file(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle write_java_file tool call."""
        session_id = arguments["session_id"]
        file_path = arguments["file_path"]
        content = arguments["content"]

        session = self.session_manager.get_session(session_id)

        if session:
            self.session_manager.write_file(session_id, file_path, content)
            response = {
                "status": "success",
                "session_id": session_id,
                "file_path": file_path,
                "message": f"File {file_path} written successfully"
            }
        else:
            response = {
                "status": "error",
                "message": f"Failed to write file {file_path}. Session may not exist."
            }

        return await self._format_response(response)

    async def _handle_write_multiple_files(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle write_multiple_files tool call."""
        session_id = arguments["session_id"]
        files = arguments["files"]

        result = self.session_manager.write_multiple_files(session_id, files)

        if result.get("success"):
            response = {
                "status": "success",
                "session_id": session_id,
                "written": result["written"],
                "failed": result["failed"],
                "total": result["total"],
                "message": f"Batch write complete: {result['written']} files written, {result['failed']} failed"
            }
            if "failed_files" in result:
                response["failed_files"] = result["failed_files"]
        else:
            response = {
                "status": "error",
                "message": result.get("error", "Failed to write files")
            }

        return await self._format_response(response)

    async def _handle_check_errors(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle check_errors tool call."""
        session_id = arguments["session_id"]

        workspace_path = self.session_manager.get_workspace_path(session_id)
        if not workspace_path:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }
            return await self._format_response(response)

        errors = await self.jdtls_client.check_compilation_errors(workspace_path)

        response = {
            "status": "success",
            "session_id": session_id,
            "error_count": len(errors),
            "errors": errors
        }

        if not errors:
            response["message"] = "No compilation errors found!"
        else:
            response["message"] = f"Found {len(errors)} compilation error(s)"

        return await self._format_response(response)

    async def _handle_list_files(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle list_files tool call."""
        session_id = arguments["session_id"]

        files = self.session_manager.list_files(session_id)

        response = {
            "status": "success",
            "session_id": session_id,
            "file_count": len(files),
            "files": files
        }

        return await self._format_response(response)

    async def _handle_read_file(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle read_file tool call."""
        session_id = arguments["session_id"]
        file_path = arguments["file_path"]

        content = self.session_manager.read_file(session_id, file_path)

        if content is not None:
            response = {
                "status": "success",
                "file_path": file_path,
                "content": content
            }
        else:
            response = {
                "status": "error",
                "message": f"File {file_path} not found"
            }

        return await self._format_response(response)

    async def _handle_delete_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle delete_session tool call."""
        session_id = arguments["session_id"]

        success = self.session_manager.delete_session(session_id)

        if success:
            response = {
                "status": "success",
                "message": f"Session {session_id} deleted successfully"
            }
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return await self._format_response(response)

    async def _handle_get_recommendations(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle get_recommendations tool call."""
        session_id = arguments["session_id"]
        error = arguments["error"]

        recommendations = self.recommendation_engine.get_recommendations(error)

        response = {
            "status": "success",
            "session_id": session_id,
            "error": error,
            "recommendations": recommendations
        }

        return await self._format_response(response)

    async def _handle_refresh_session(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle refresh_session tool call."""
        session_id = arguments["session_id"]

        success = self.session_manager.refresh_session(session_id)

        if success:
            response = {
                "status": "success",
                "session_id": session_id,
                "message": "Session timeout refreshed successfully"
            }
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return await self._format_response(response)

    async def _handle_get_session_info(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle get_session_info tool call."""
        session_id = arguments["session_id"]

        info = self.session_manager.get_session_info(session_id)

        if info:
            response = {
                "status": "success",
                **info
            }
        else:
            response = {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return await self._format_response(response)

    async def _format_response(self, response: Dict[str, Any]) -> list[TextContent]:
        """Format response for MCP protocol.

        This method can be overridden by transport-specific implementations
        if needed, but by default converts to string representation.
        """
        return [TextContent(type="text", text=str(response))]
