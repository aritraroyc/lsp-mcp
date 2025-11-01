"""
Configuration for Java Error Checker MCP Service
"""

import os
from pathlib import Path

# Workspace configuration
WORKSPACE_BASE_DIR = os.getenv(
    "JDTLS_WORKSPACE_DIR",
    "/tmp/jdtls-workspaces"
)

# Session timeout (seconds)
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))

# JDTLS configuration
JDTLS_PATH = os.getenv("JDTLS_PATH", str(Path.home() / ".local/share/jdtls"))
JDTLS_MEMORY = os.getenv("JDTLS_MEMORY", "1G")

# Java configuration
JAVA_HOME = os.getenv("JAVA_HOME", "")

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE", "/tmp/java-error-checker-mcp.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
