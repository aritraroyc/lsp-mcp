# Java Error Checker MCP Service

A Python-based Model Context Protocol (MCP) server that provides Java compilation error checking using the Eclipse JDT Language Server (JDTLS) or javac compiler.

## Table of Contents

1. [Features](#features)
2. [Prerequisites & Installation](#prerequisites--installation)
3. [Quick Start](#quick-start)
4. [Usage Guide](#usage-guide)
5. [Design & Architecture](#design--architecture)
6. [Design Patterns](#design-patterns)
7. [Agentic Workflows](#agentic-workflows)
8. [Remote Deployment](#remote-deployment)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

## Features

- **Session Management**: Create isolated workspace sessions for each client
- **Project Structure Replication**: Automatically maintains standard Java project structure
- **Compilation Error Checking**: Detects and reports Java compilation errors
- **Error Recommendations**: Provides intelligent suggestions for fixing common errors
- **Multi-file Support**: Handle complex projects with multiple Java source files
- **File Operations**: Read, write, and list Java files in session workspaces
- **Batch File Writing**: Write multiple Java files in a single operation
- **Session Persistence**: Sessions persist across multiple operations for incremental code generation
- **Session Refresh**: Extend session timeout for long-running workflows
- **Session Tracking**: Monitor session state, file count, and workspace details
- **Transport Flexibility**: Support for stdio (local) and HTTP/SSE (remote) transports
- **OOP Design Patterns**: Strategy, Repository, Singleton, Factory, Command, and Observer patterns

## Prerequisites & Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Java JDK 11+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install openjdk-17-jdk
```

**macOS:**
```bash
brew install openjdk@17
```

**Windows:**
Download from https://adoptium.net/ and install.

**Verify installation:**
```bash
java -version
javac -version
```

### 3. Install Eclipse JDTLS (Optional)

For enhanced language server features:

```bash
mkdir -p ~/.local/share/jdtls
cd ~/.local/share/jdtls
wget https://download.eclipse.org/jdtls/milestones/1.9.0/jdt-language-server-1.9.0-202203031534.tar.gz
tar -xzf jdt-language-server-*.tar.gz
```

**Note:** The server works with just `javac` if JDTLS is not installed.

## Quick Start

### 1. Start the Server

**Stdio Transport (for Claude Desktop):**
```bash
python src/server/server.py
```

**HTTP/SSE Transport (for remote access):**
```bash
python src/server/server_sse.py --host 0.0.0.0 --port 8000
```

### 2. Test with Example Client

```bash
python src/examples/example_client.py
```

### 3. Health Check (for HTTP/SSE)

```bash
curl http://localhost:8000/health
```

## Usage Guide

### Available Tools

#### 1. `create_session`

Create a new isolated Java project session.

**Parameters:**
- `project_name` (optional): Name of the Java project (default: "default")

**Example:**
```json
{"project_name": "my-java-project"}
```

**Returns:**
```json
{
  "session_id": "uuid-string",
  "project_name": "my-java-project",
  "status": "success"
}
```

#### 2. `write_java_file`

Write a single Java source file to the workspace.

**Parameters:**
- `session_id` (required): Session ID from `create_session`
- `file_path` (required): Relative path (e.g., "com/example/Main.java")
- `content` (required): Java source code

**Example:**
```json
{
  "session_id": "uuid-string",
  "file_path": "com/example/Main.java",
  "content": "package com.example;\n\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello World\");\n    }\n}"
}
```

#### 3. `write_multiple_files`

Write multiple Java files in a single batch operation.

**Parameters:**
- `session_id` (required): Session ID
- `files` (required): Array of {file_path, content} objects

**Example:**
```json
{
  "session_id": "uuid-string",
  "files": [
    {
      "file_path": "com/example/User.java",
      "content": "package com.example;\n\npublic class User {\n    private String name;\n    // ...\n}"
    },
    {
      "file_path": "com/example/Product.java",
      "content": "package com.example;\n\npublic class Product {\n    private String id;\n    // ...\n}"
    }
  ]
}
```

#### 4. `check_errors`

Check for Java compilation errors in the workspace.

**Parameters:**
- `session_id` (required): Session ID

**Returns:**
```json
{
  "status": "success",
  "error_count": 0,
  "errors": [],
  "message": "No compilation errors found!"
}
```

#### 5. `list_files`

List all Java files in the workspace.

**Parameters:**
- `session_id` (required): Session ID

**Returns:**
```json
{
  "status": "success",
  "file_count": 2,
  "files": ["src/main/java/com/example/Main.java", "src/main/java/com/example/Utils.java"]
}
```

#### 6. `read_file`

Read the content of a specific Java file.

**Parameters:**
- `session_id` (required): Session ID
- `file_path` (required): Relative file path

**Returns:**
```json
{
  "status": "success",
  "file_path": "com/example/Main.java",
  "content": "package com.example;\n..."
}
```

#### 7. `get_recommendations`

Get intelligent suggestions for fixing a specific compilation error.

**Parameters:**
- `session_id` (required): Session ID
- `error` (required): Error object from `check_errors`

**Returns:**
```json
{
  "status": "success",
  "error": {"message": "cannot find symbol"},
  "recommendations": [
    "Check that the class, variable, or method name is spelled correctly",
    "Ensure the required import statement is present",
    "Verify that the variable is declared before use"
  ]
}
```

#### 8. `refresh_session`

Extend the session timeout to prevent expiration during long workflows.

**Parameters:**
- `session_id` (required): Session ID

**Returns:**
```json
{
  "status": "success",
  "message": "Session timeout refreshed successfully"
}
```

#### 9. `get_session_info`

Get detailed metadata about a session.

**Parameters:**
- `session_id` (required): Session ID

**Returns:**
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "project_name": "my-project",
  "workspace_path": "/tmp/jdtls-workspaces/uuid-string",
  "created_at": 1698765432.123,
  "last_accessed": 1698765500.456,
  "age_seconds": 68.333,
  "idle_seconds": 0.789,
  "file_count": 2,
  "files": [...]
}
```

#### 10. `delete_session`

Delete a session and clean up its workspace.

**Parameters:**
- `session_id` (required): Session ID

**Returns:**
```json
{
  "status": "success",
  "message": "Session uuid-string deleted successfully"
}
```

## Design & Architecture

### High-Level Architecture

```
┌────────────────────────────────────────────────┐
│              CLIENT LAYER                      │
│  Claude Desktop / Custom Clients / LangGraph   │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│           TRANSPORT LAYER                      │
│  ├─ StdioServerTransport (stdio)               │
│  └─ SSEServerTransport (HTTP/SSE)              │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│        MCP PROTOCOL LAYER                      │
│  JavaErrorCheckerServer (Tool routing)         │
└─────────────────┬──────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼──────────┐   ┌────▼─────────────────┐
│ SessionManager   │   │  ErrorRecommendation │
│ + Repository     │   │  Engine              │
│ + Strategies     │   │  + Strategies        │
└───────┬──────────┘   └─────────────────────┘
        │
┌───────▼──────────────────────────────────────┐
│        BUSINESS LOGIC LAYER                  │
│  ├─ JDTLSClient (Java compilation)           │
│  ├─ File I/O operations                      │
│  └─ Error parsing                            │
└────────────────────────────────────────────┐
                                              │
        ┌─────────────────────────────────────┤
        │                                      │
┌───────▼──────────────┐        ┌──────────────▼────┐
│    File System       │        │  Java Compiler     │
│ /tmp/jdtls-...      │        │  (javac/JDTLS)     │
└──────────────────────┘        └───────────────────┘
```

### Project Structure

```
java-error-checker-mcp/
├── Core Modules
│   ├── base_server.py             # Core business logic (transport-agnostic)
│   ├── transports.py              # Transport implementations (stdio, SSE)
│   ├── session_manager.py          # Session & workspace management
│   ├── jdtls_client.py             # Java compilation & error parsing
│   ├── error_recommendation_engine.py  # Error fix recommendations
│   └── config.py                   # Configuration management
│
├── Server Entry Points
│   ├── server.py                   # Stdio transport entry point
│   └── server_sse.py               # HTTP/SSE transport entry point
│
├── Tests & Examples
│   ├── test_server.py              # Unit tests
│   ├── test_end_to_end.py          # Integration tests
│   ├── example_client.py            # Simple example
│   ├── agentic_workflow_example.py  # Multi-stage workflow
│   ├── langgraph_agent_example.py   # LangGraph integration
│   └── langgraph_integration.py     # LangGraph bridge
│
├── Configuration
│   ├── requirements.txt             # Python dependencies
│   ├── setup.py                    # Package setup
│   └── .env (optional)             # Environment variables
│
└── Documentation
    ├── README.md                    # Main documentation (this file)
    ├── ARCHITECTURE.md              # Detailed architecture docs
    └── CHANGELOG.md                 # Version history
```

## Design Patterns

### 1. **Transport Abstraction (Strategy Pattern)**

```python
class ServerTransport(ABC):
    @abstractmethod
    async def run(self, server: JavaErrorCheckerServer) -> None:
        pass

class StdioServerTransport(ServerTransport):
    async def run(self, server):
        # Stdio-specific implementation

class SSEServerTransport(ServerTransport):
    async def run(self, server):
        # HTTP/SSE-specific implementation
```

**Benefit:** Easy to add new transports (WebSocket, gRPC, etc.) without modifying core logic.

### 2. **Command Pattern (Tool Routing)**

```python
async def _route_tool_call(self, name: str, arguments: Dict) -> list[TextContent]:
    handlers = {
        "create_session": self._handle_create_session,
        "write_java_file": self._handle_write_java_file,
        # ... more handlers
    }
    handler = handlers.get(name)
    return await handler(arguments)
```

**Benefit:** Centralized tool routing, easy to add/remove tools.

### 3. **Strategy Pattern (Error Recommendations)**

```python
class RecommendationStrategy(ABC):
    def can_handle(self, error: Dict) -> bool:
        raise NotImplementedError

    def get_recommendations(self, error: Dict) -> List[str]:
        raise NotImplementedError

class CannotFindSymbolStrategy(RecommendationStrategy):
    # Specific recommendations for this error type

class TypeMismatchStrategy(RecommendationStrategy):
    # Specific recommendations for this error type
```

**Benefit:** Easy to add new error patterns without modifying core engine.

### 4. **Strategy Pattern (Path Resolution)**

```python
class PathResolutionStrategy(ABC):
    def resolve_path(self, workspace: Path, file_path: str) -> Path:
        raise NotImplementedError

class JavaMainPathStrategy(PathResolutionStrategy):
    # Resolves to src/main/java/

class JavaTestPathStrategy(PathResolutionStrategy):
    # Resolves to src/test/java/
```

**Benefit:** Support different project structures without code duplication.

### 5. **Repository Pattern (Data Access)**

```python
class SessionRepository:
    def create(self, session: Session) -> None
    def get(self, session_id: str) -> Optional[Session]
    def update(self, session: Session) -> bool
    def delete(self, session_id: str) -> bool
    def list_all(self) -> List[Session]
```

**Benefit:** Encapsulated data access, thread-safe operations, easy to swap implementations.

### 6. **Singleton Pattern (SessionManager)**

```python
class SessionManager:
    _instance = None
    _lock = Lock()

    @classmethod
    def get_instance(cls) -> "SessionManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
```

**Benefit:** Single authority for session management, optional singleton usage.

### 7. **Factory Pattern (Transport Creation)**

```python
class TransportFactory:
    @classmethod
    def create(cls, transport_type: str, **kwargs) -> ServerTransport:
        transport_class = cls._transports.get(transport_type)
        return transport_class(**kwargs)
```

**Benefit:** Decouple transport instantiation from usage.

### 8. **Observer Pattern (Session Events)**

```python
class SessionManager:
    def register_on_session_created(self, callback: Callable) -> None:
        self._on_session_created.append(callback)

    def register_on_session_deleted(self, callback: Callable) -> None:
        self._on_session_deleted.append(callback)
```

**Benefit:** Extensible event notifications without modifying core code.

## Agentic Workflows

### Multi-Stage Code Generation Pattern

Ideal for AI agents that generate code in multiple stages:

```python
# Stage 1: Create session
session_id = create_session("e-commerce-app")

# Stage 2: Generate data models
write_multiple_files(session_id, [
    {"file_path": "com/example/User.java", "content": "..."},
    {"file_path": "com/example/Product.java", "content": "..."}
])
check_errors(session_id)

# Stage 3: Generate services (incremental)
write_multiple_files(session_id, [
    {"file_path": "com/example/UserService.java", "content": "..."},
    {"file_path": "com/example/ProductService.java", "content": "..."}
])
errors = check_errors(session_id)

# Stage 4: Fix errors if needed
for error in errors:
    recommendations = get_recommendations(session_id, error)
    # Generate fix and write corrected file
    write_java_file(session_id, error["file"], corrected_content)

# Stage 5: Final validation
errors = check_errors(session_id)
if not errors:
    print("✓ Project compiles successfully!")

# Stage 6: Cleanup
delete_session(session_id)
```

### Session Timeout Management

Sessions automatically expire after 3600 seconds (1 hour) of inactivity:

```python
# Extend timeout during long workflows
refresh_session(session_id)  # Resets idle timer
```

### Batch File Writing Benefits

For efficiency, use `write_multiple_files` for multiple files:

```python
# Efficient: Single operation, single error check
write_multiple_files(session_id, large_file_list)

# Less efficient: Multiple operations, multiple latencies
for file in large_file_list:
    write_java_file(session_id, file["path"], file["content"])
```

## Remote Deployment

### Starting HTTP/SSE Server

```bash
python src/server/server_sse.py --host 0.0.0.0 --port 8000
```

### Health Endpoint

```bash
curl http://localhost:8000/health
```

### Making Tool Calls

```bash
curl -X POST http://localhost:8000/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_session",
      "arguments": {"project_name": "test"}
    },
    "id": 1
  }'
```

### Docker Deployment

```bash
# Build image
docker build -t java-error-checker .

# Run container
docker run -p 8000:8000 \
  -e JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
  java-error-checker
```

### Kubernetes Deployment

See `k8s-deployment.yaml` in deployment examples.

## Configuration

### Environment Variables

```bash
# Java configuration
JAVA_HOME=/usr/lib/jvm/java-17-openjdk
JDTLS_PATH=$HOME/.local/share/jdtls
JDTLS_MEMORY=1G

# Session & workspace
JDTLS_WORKSPACE_DIR=/tmp/jdtls-workspaces
SESSION_TIMEOUT=3600

# Logging
LOG_FILE=/tmp/java-error-checker-mcp.log
LOG_LEVEL=INFO
```

### Customizing Path Strategies

```python
from session_manager import SessionManager, JavaTestPathStrategy

manager = SessionManager()
manager.set_path_strategy(JavaTestPathStrategy())
```

### Registering Custom Recommendation Strategies

```python
from error_recommendation_engine import ErrorRecommendationEngine, RecommendationStrategy

class CustomErrorStrategy(RecommendationStrategy):
    def can_handle(self, error: Dict) -> bool:
        return "custom error pattern" in error.get("message", "").lower()

    def get_recommendations(self, error: Dict) -> List[str]:
        return ["Custom recommendation"]

engine = ErrorRecommendationEngine()
engine.register_strategy(CustomErrorStrategy())
```

## Troubleshooting

### Issue: "java: command not found"

**Solution:** Ensure Java is installed and in PATH:
```bash
sudo apt install openjdk-17-jdk  # Linux
brew install openjdk@17          # macOS
```

### Issue: "javac: command not found"

**Solution:** Ensure javac is in PATH:
```bash
export JAVA_HOME=/path/to/jdk17
export PATH=$JAVA_HOME/bin:$PATH
```

### Issue: Session workspace not cleaning up

**Solution:** Call cleanup manually:
```python
from session_manager import SessionManager

manager = SessionManager()
deleted_count = manager.cleanup_old_sessions(max_idle_seconds=300)
print(f"Cleaned up {deleted_count} sessions")
```

### Issue: HTTP server won't start on port 8000

**Solution:** Check if port is in use:
```bash
lsof -i :8000
# Then use different port:
python src/server/server_sse.py --port 8001
```

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
python src/server/server.py
tail -f /tmp/java-error-checker-mcp.log
```

## Performance Considerations

- **Full Recompilation:** Every `check_errors` call recompiles all Java files
- **Concurrent Sessions:** Thread-safe, supports multiple concurrent sessions
- **Memory Usage:** Each session's workspace is isolated on disk
- **Batch Operations:** Use `write_multiple_files` for better performance

## Testing

### Run All Tests

```bash
python -m pytest test_server.py test_end_to_end.py -v
```

### Run Specific Test

```bash
python -m pytest test_server.py::TestSessionManager::test_create_session -v
```

### Test Coverage

```bash
python -m pytest --cov=. --cov-report=html
```

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- Code follows PEP 8 style guide
- New features include tests
- Documentation is updated

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review example files
3. Check logs: `tail -f /tmp/java-error-checker-mcp.log`
4. Open an issue on GitHub
