#!/usr/bin/env python3
"""
Java Error Checker MCP Server - HTTP/SSE Transport

Provides HTTP/SSE transport for remote access from LangGraph agents and other clients.
Eliminates duplication by reusing base_server.JavaErrorCheckerServer.
"""

import asyncio
import json
import logging
import sys
import os
from typing import Any, Dict

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Add src directory to path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.base_server import JavaErrorCheckerServer
from core.transports import JsonResponseTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/java-error-checker-mcp-sse.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

# Global server instance
_server_instance: JavaErrorCheckerServer = None
_transport_instance: JsonResponseTransport = None


class SSETransport(JsonResponseTransport):
    """HTTP/SSE transport implementation for Starlette."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Initialize SSE transport.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        super().__init__()
        self.host = host
        self.port = port
        self.server_instance: JavaErrorCheckerServer = None

    async def run(self, server: JavaErrorCheckerServer) -> None:
        """Start the Starlette HTTP server.

        Args:
            server: JavaErrorCheckerServer instance
        """
        self.server_instance = server
        server._register_handlers()

        # Create Starlette app
        app = Starlette(
            routes=[
                Route("/sse", self.handle_sse, methods=["POST"]),
                Route("/health", self.handle_health, methods=["GET"]),
            ]
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Run with uvicorn
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server_instance = uvicorn.Server(config)
        await server_instance.serve()

    async def handle_sse(self, request):
        """Handle POST requests to /sse endpoint.

        Args:
            request: Starlette request object

        Returns:
            JSONResponse with MCP response
        """
        try:
            body = await request.json()

            # Extract MCP request
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id", 1)

            # Handle different MCP methods
            if method == "tools/list":
                result = self.server_instance._get_tools()
                response = {
                    "jsonrpc": "2.0",
                    "result": [{"name": tool.name, "description": tool.description}
                               for tool in result],
                    "id": request_id
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                # Call the tool
                text_contents = await self.server_instance._route_tool_call(
                    tool_name, arguments
                )

                # Parse the response text as JSON/dict
                if text_contents:
                    response_text = text_contents[0].text
                    try:
                        # If it looks like a dict string, parse it
                        if response_text.startswith("{"):
                            response_data = eval(response_text)
                        else:
                            response_data = json.loads(response_text)
                    except (json.JSONDecodeError, SyntaxError):
                        response_data = {"text": response_text}

                    response = {
                        "jsonrpc": "2.0",
                        "result": response_data,
                        "id": request_id
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": "Internal error"},
                        "id": request_id
                    }
            elif method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {
                            "name": "java-error-checker",
                            "version": "1.0.0"
                        }
                    },
                    "id": request_id
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": request_id
                }

            return JSONResponse(response)

        except Exception as e:
            logger.error(f"Error handling SSE request: {e}", exc_info=True)
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                    "id": 1
                },
                status_code=400
            )

    async def handle_health(self, request):
        """Handle GET requests to /health endpoint.

        Args:
            request: Starlette request object

        Returns:
            JSONResponse with health status
        """
        return JSONResponse({
            "status": "healthy",
            "service": "java-error-checker",
            "version": "1.0.0"
        })


async def main(host: str = "0.0.0.0", port: int = 8000):
    """Entry point for the HTTP/SSE MCP server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    try:
        global _server_instance, _transport_instance

        logger.info(f"Starting Java Error Checker MCP Server on {host}:{port}")
        server = JavaErrorCheckerServer()
        transport = SSETransport(host=host, port=port)

        _server_instance = server
        _transport_instance = transport

        await transport.run(server)

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Java Error Checker MCP Server (HTTP/SSE)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    asyncio.run(main(host=args.host, port=args.port))
