# Java Error Checker MCP Service

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue)](https://github.com/anthropics/java-error-checker-mcp)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

A Python-based Model Context Protocol (MCP) server that provides Java compilation error checking using the Eclipse JDT Language Server (JDTLS) or javac compiler. Designed for AI agents and LangGraph workflows.

## Quick Start

### 1. Install Dependencies

```bash
make install
# or: pip install -r requirements.txt
```

### 2. Start the Server

**For Claude Desktop (stdio transport):**
```bash
./run-stdio.sh
# or: make run-stdio
```

**For Remote Access (HTTP/SSE transport):**
```bash
./run-http.sh
# or: make run-http
```

### 3. Test with Example Client

```bash
make run-example
# or: python src/examples/example_client.py
```

## Documentation

📚 **Complete documentation is in the `docs/` directory:**

- **[docs/README.md](docs/README.md)** - Main guide with features, installation, and all tool documentation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design, design patterns, and architecture
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment options (Docker, Kubernetes, Cloud), examples, and LangGraph integration
- **[docs/REFACTORING.md](docs/REFACTORING.md)** - Code refactoring summary and design pattern details
- **[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - File organization and navigation guide

## Key Features

✅ **Session Management** - Isolated workspaces for concurrent clients
✅ **Compilation Checking** - Real-time Java error detection
✅ **Smart Recommendations** - AI-friendly error fix suggestions
✅ **Batch Operations** - Write multiple files efficiently
✅ **Two Transports** - Local (stdio) and remote (HTTP/SSE) communication
✅ **LangGraph Ready** - First-class integration with LangGraph agents
✅ **Production-Grade** - 8 OOP design patterns, comprehensive error handling
✅ **Well-Documented** - 5 detailed markdown guides

## Project Structure

```
java-error-checker-mcp/
├── src/
│   ├── core/           # Business logic (SessionManager, JDTLSClient, etc.)
│   ├── server/         # Entry points (server.py, server_sse.py)
│   ├── client/         # Client libraries (langgraph_integration.py)
│   ├── tests/          # Test suites
│   └── examples/       # Example implementations
├── docs/               # Documentation (5 comprehensive guides)
├── Makefile            # Common commands
├── run-stdio.sh        # Quick start script for Claude Desktop
├── run-http.sh         # Quick start script for HTTP/SSE
└── requirements.txt    # Python dependencies
```

## Common Commands

```bash
# Development
make install          # Install dependencies
make dev              # Install with development tools
make test             # Run all tests
make lint             # Check code quality

# Running
make run-stdio        # Start stdio server
make run-http         # Start HTTP server
make run-example      # Run example client

# Docker
make docker-build     # Build Docker image
make docker-run       # Run in Docker

# Maintenance
make clean            # Clean temporary files
make clean-workspaces # Reset session workspaces
```

## Prerequisites

- **Python 3.10+**
- **Java JDK 11+** (for javac compiler)
- **Eclipse JDTLS** (optional, for enhanced features)

Install Java:
```bash
# Ubuntu/Debian
sudo apt install openjdk-17-jdk

# macOS
brew install openjdk@17

# Verify
java -version && javac -version
```

## Available Tools

The MCP server provides 10 tools for Java code management:

1. **create_session** - Create isolated project session
2. **write_java_file** - Write single Java file
3. **write_multiple_files** - Batch write multiple files
4. **check_errors** - Check compilation errors
5. **list_files** - List Java files in workspace
6. **read_file** - Read file content
7. **get_recommendations** - Get error fix suggestions
8. **refresh_session** - Extend session timeout
9. **get_session_info** - Get session metadata
10. **delete_session** - Clean up session

See [docs/README.md](docs/README.md) for complete tool documentation.

## Example: Simple Compilation Check

```python
import asyncio
from src.client.langgraph_integration import JavaErrorCheckerClient

async def check_java_code():
    client = JavaErrorCheckerClient(base_url="http://localhost:8000")

    # Create session
    session_id = await client.create_session("my-project")

    # Write Java file
    java_code = """
    public class HelloWorld {
        public static void main(String[] args) {
            System.out.println("Hello, World!");
        }
    }
    """
    await client.write_file(session_id, "HelloWorld.java", java_code)

    # Check for errors
    result = await client.check_errors(session_id)

    if result["error_count"] == 0:
        print("✓ Code compiles successfully!")
    else:
        for error in result["errors"]:
            print(f"❌ {error['file']}:{error['line']} - {error['message']}")

    await client.delete_session(session_id)

asyncio.run(check_java_code())
```

## Design Highlights

### OOP Design Patterns
- **Strategy** - Multiple error recommendations and path resolution strategies
- **Repository** - Thread-safe session data access
- **Singleton** - Global SessionManager instance (optional)
- **Factory** - Transport creation abstraction
- **Command** - Tool routing and dispatching
- **Observer** - Session event callbacks
- **Adapter** - Unified transport interface
- **Adapter** - HTTP/SSE response formatting

### Clean Architecture
- **Transport-Agnostic Core** - Business logic independent of communication mechanism
- **Separation of Concerns** - Clear module boundaries
- **Extensibility** - Easy to add new tools, strategies, and transports
- **Type Safety** - Full type hints throughout

## Testing

```bash
# Run all tests
make test

# Run specific test suite
make test-unit
make test-e2e

# Generate coverage report
make test-coverage
```

## Deployment

### Docker
```bash
docker build -t java-error-checker .
docker run -p 8000:8000 java-error-checker
```

### Kubernetes, AWS, GCP
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for cloud deployment guides.

## Contributing

1. Follow the existing code patterns and design
2. Add tests for new features
3. Run `make lint` and `make format` before committing
4. Update relevant documentation

## License

MIT License - See [LICENSE](LICENSE) for details

## Support

- 📖 **Documentation**: See `docs/` directory
- 🐛 **Issues**: Report on GitHub
- 💬 **Discussions**: Start a GitHub discussion

---

**For detailed information, start with [docs/README.md](docs/README.md)**
