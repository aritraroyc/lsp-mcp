"""
Transport Layer Implementations

This module provides concrete implementations of the ServerTransport interface
for different MCP server communication protocols (stdio, HTTP/SSE, etc.).

Implements the Strategy pattern to allow pluggable transport mechanisms.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from abc import abstractmethod

from mcp.server.stdio import stdio_server
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import TextContent

from .base_server import ServerTransport, JavaErrorCheckerServer

logger = logging.getLogger(__name__)


class StdioServerTransport(ServerTransport):
    """Stdio transport for local MCP communication.

    This transport uses standard input/output for bidirectional communication,
    typically used for Claude Desktop integration.
    """

    async def send_response(self, response: Dict[str, Any]) -> List[TextContent]:
        """Convert response dict to string format for stdio transport.

        Args:
            response: Response dictionary from business logic

        Returns:
            List with single TextContent containing string representation
        """
        return [TextContent(type="text", text=str(response))]

    async def run(self, server: JavaErrorCheckerServer) -> None:
        """Run the stdio transport server.

        Args:
            server: JavaErrorCheckerServer instance to bind to
        """
        server._register_handlers()

        async with stdio_server() as (read_stream, write_stream):
            logger.info("Stdio MCP server started")

            # Run the MCP server with proper initialization
            await server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="java-error-checker",
                    server_version="1.0.0",
                    capabilities=server.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


class JsonResponseTransport(ServerTransport):
    """Base class for transports using JSON responses.

    This is useful for HTTP-based transports that need JSON serialization.
    """

    async def send_response(self, response: Dict[str, Any]) -> List[TextContent]:
        """Convert response dict to JSON-formatted TextContent.

        Args:
            response: Response dictionary from business logic

        Returns:
            List with single TextContent containing JSON string
        """
        json_str = json.dumps(response)
        return [TextContent(type="text", text=json_str)]

    @abstractmethod
    async def run(self, server: JavaErrorCheckerServer) -> None:
        """Must be implemented by subclasses."""
        pass


class SSEServerTransport(JsonResponseTransport):
    """HTTP/SSE transport for remote MCP communication.

    This transport uses HTTP with Server-Sent Events for bidirectional
    communication, suitable for cloud deployments and remote agents.

    This is an abstract base that requires a web framework integration.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Initialize SSE transport with binding parameters.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 8000)
        """
        self.host = host
        self.port = port

    async def run(self, server: JavaErrorCheckerServer) -> None:
        """Run the SSE transport server.

        This method is implemented in the web framework-specific
        integration (see server_sse.py).

        Args:
            server: JavaErrorCheckerServer instance to bind to
        """
        raise NotImplementedError("SSE transport requires web framework integration")


class TransportFactory:
    """Factory for creating transport instances.

    This implements the Factory pattern to decouple transport creation
    from the server initialization logic.
    """

    _transports = {
        "stdio": StdioServerTransport,
        "sse": SSEServerTransport,
    }

    @classmethod
    def create(cls, transport_type: str, **kwargs) -> ServerTransport:
        """Create a transport instance.

        Args:
            transport_type: Type of transport ("stdio", "sse", etc.)
            **kwargs: Additional arguments for transport initialization

        Returns:
            ServerTransport instance

        Raises:
            ValueError: If transport type is not registered
        """
        transport_class = cls._transports.get(transport_type.lower())
        if not transport_class:
            raise ValueError(
                f"Unknown transport type: {transport_type}. "
                f"Available: {', '.join(cls._transports.keys())}"
            )

        logger.info(f"Creating {transport_type} transport")
        return transport_class(**kwargs)

    @classmethod
    def register(cls, name: str, transport_class: type) -> None:
        """Register a custom transport.

        Args:
            name: Transport name
            transport_class: Class implementing ServerTransport
        """
        cls._transports[name.lower()] = transport_class
        logger.info(f"Registered transport: {name}")

    @classmethod
    def list_transports(cls) -> List[str]:
        """List available transports.

        Returns:
            List of registered transport names
        """
        return list(cls._transports.keys())
