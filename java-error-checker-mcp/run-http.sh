#!/bin/bash
# Start the MCP server with HTTP/SSE transport for remote access

python src/server/server_sse.py --host 0.0.0.0 --port 8000
