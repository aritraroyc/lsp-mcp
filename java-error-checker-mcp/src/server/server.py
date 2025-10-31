#!/usr/bin/env python3
"""
Java Error Checker MCP Server - Stdio Transport

This is the entry point for local MCP communication using stdio transport.
It's typically used for Claude Desktop integration.

The server is transport-agnostic, with transport-specific logic delegated to
the transports module.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.base_server import JavaErrorCheckerServer
from core.transports import StdioServerTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/java-error-checker-mcp.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Entry point for the stdio MCP server."""
    try:
        server = JavaErrorCheckerServer()
        transport = StdioServerTransport()
        await transport.run(server)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
