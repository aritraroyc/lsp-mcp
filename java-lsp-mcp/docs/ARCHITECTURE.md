# Architecture & Design Details

Comprehensive guide to the Java Error Checker MCP Service architecture, design patterns, and internal implementation.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Module Details](#module-details)
3. [Data Flow](#data-flow)
4. [Design Patterns](#design-patterns-in-depth)
5. [Thread Safety](#thread-safety)
6. [Error Handling](#error-handling)
7. [Extension Points](#extension-points)
8. [Performance Optimization](#performance-optimization)

## System Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│                  CLIENT LAYER                       │
│  ├─ Claude Desktop integration                      │
│  ├─ Custom MCP Clients                              │
│  ├─ LangGraph agents                                │
│  └─ HTTP clients                                    │
└──────────────────────┬────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────┐
│              TRANSPORT LAYER                      │
│  ├─ StdioServerTransport                          │
│  │  └─ stdio_server from mcp.server.stdio          │
│  │                                                  │
│  ├─ SSEServerTransport                            │
│  │  └─ Starlette + Uvicorn HTTP server             │
│  │                                                  │
│  └─ TransportFactory (Strategy pattern)            │
└──────────────────────┬────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────┐
│           MCP PROTOCOL LAYER                      │
│  ├─ Server (from mcp.server)                      │
│  ├─ _register_handlers()                          │
│  ├─ _route_tool_call()  [Command pattern]         │
│  └─ Tool definitions (10 tools)                   │
└──────────────────────┬────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────┐
│         BUSINESS LOGIC LAYER                      │
│  ├─ JavaErrorCheckerServer (core logic)           │
│  │  └─ Handler methods (async)                     │
│  │                                                  │
│  ├─ SessionManager                                │
│  │  ├─ Session lifecycle                          │
│  │  ├─ SessionRepository [Repository pattern]     │
│  │  └─ Path strategies [Strategy pattern]         │
│  │                                                  │
│  ├─ JDTLSClient                                   │
│  │  ├─ Java compilation                           │
│  │  └─ Error parsing                              │
│  │                                                  │
│  └─ ErrorRecommendationEngine                     │
│     ├─ RecommendationStrategy [Strategy pattern]  │
│     └─ Error pattern matchers                     │
└──────────────────────┬────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────┐
│         EXTERNAL DEPENDENCIES                     │
│  ├─ File System: /tmp/jdtls-workspaces/           │
│  ├─ Java Compiler: javac or JDTLS                 │
│  └─ Python Standard Library                       │
└──────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
Client Request (JSON-RPC)
        │
        ▼
   server.py or server_sse.py (entry points)
        │
        ▼
   JavaErrorCheckerServer._route_tool_call()
        │
        ├─→ _handle_create_session()
        │        │→ SessionManager.create_session()
        │        │→ SessionRepository.create()
        │        └─→ return session_id
        │
        ├─→ _handle_write_java_file()
        │        │→ SessionManager.get_session()
        │        │→ SessionManager.write_file()
        │        │   (uses PathResolutionStrategy)
        │        └─→ File written to /tmp/jdtls-...
        │
        ├─→ _handle_check_errors()
        │        │→ SessionManager.get_workspace_path()
        │        │→ JDTLSClient.check_compilation_errors()
        │        │   ├─ Find all *.java files
        │        │   ├─ Compile with javac
        │        │   └─ Parse errors via regex
        │        └─→ Return errors[]
        │
        ├─→ _handle_get_recommendations()
        │        │→ ErrorRecommendationEngine.get_recommendations()
        │        │   ├─ Check each RecommendationStrategy
        │        │   └─ Match error pattern
        │        └─→ Return recommendations[]
        │
        └─→ ... (other handlers)
                │
                ▼
        Format response
                │
                ▼
        Transport-specific response
                │
                ▼
        Send to client
```

## Module Details

### 1. base_server.py (500+ lines)

**Purpose:** Core business logic, transport-agnostic

**Key Classes:**
- `ServerTransport` (ABC)
  - Abstract base class for all transports
  - Methods: `send_response()`, `run()`

- `JavaErrorCheckerServer`
  - Main server class
  - Depends on: `SessionManager`, `JDTLSClient`, `ErrorRecommendationEngine`
  - Methods: ~20 handler methods + tool routing
  - Pattern: Command pattern for tool routing

**Key Methods:**
```python
_register_handlers()        # Register all 10 tools
_route_tool_call()          # Command pattern dispatcher
_get_tools()                # Return tool definitions
_handle_create_session()    # Session creation handler
_handle_write_java_file()   # File write handler
_handle_check_errors()      # Error checking handler
# ... etc (10 total handlers)
```

### 2. transports.py (200+ lines)

**Purpose:** Transport-specific implementations

**Key Classes:**
- `ServerTransport` (ABC)
  - Base class imported from base_server

- `StdioServerTransport`
  - Uses: `stdio_server()` from MCP
  - Returns: String-formatted responses
  - Use case: Claude Desktop, local stdio

- `JsonResponseTransport` (ABC)
  - Base for JSON-based transports
  - Returns: JSON-formatted responses

- `SSEServerTransport`
  - Uses: Starlette + Uvicorn
  - Routes: `/sse` POST endpoint, `/health` GET endpoint
  - Use case: Remote HTTP/SSE clients

- `TransportFactory`
  - Factory pattern implementation
  - Registers and creates transports
  - Extensible for custom transports

**Key Methods:**
```python
StdioServerTransport.run()
    └─ Registers handlers
    └─ Starts stdio_server()

SSEServerTransport.run()
    ├─ Creates Starlette app
    ├─ Adds CORS middleware
    ├─ Registers routes (/sse, /health)
    └─ Starts Uvicorn server

TransportFactory.create()
    └─ Instantiates transport by type

TransportFactory.register()
    └─ Register custom transport (extensible)
```

### 3. session_manager.py (550+ lines)

**Purpose:** Session and workspace management

**Key Classes:**
- `Session` (dataclass)
  - Immutable session metadata
  - Fields: session_id, workspace_path, project_name, created_at, last_accessed

- `PathResolutionStrategy` (ABC)
  - Strategy pattern for path resolution
  - Subclasses: JavaMainPathStrategy, JavaTestPathStrategy

- `SessionRepository`
  - Repository pattern for CRUD operations
  - Thread-safe with Lock
  - Methods: create, get, update, delete, list_all, clear
  - Storage: In-memory Dict[session_id, Session]

- `SessionManager`
  - Orchestrates session lifecycle
  - Implements: Singleton (optional), Repository, Strategy, Observer patterns
  - Contains: SessionRepository instance, PathResolutionStrategy

**Key Methods:**
```python
# Session lifecycle
create_session()            # Create new session with UUID
get_session()               # Get session, update last_accessed
delete_session()            # Delete session, cleanup workspace
refresh_session()           # Update last_accessed timestamp

# File operations
write_file()                # Single file write
write_multiple_files()      # Batch write with error tracking
read_file()                 # Read file content
list_files()                # Find all *.java files

# Metadata
get_workspace_path()        # Get workspace Path object
get_session_info()          # Return session metadata
cleanup_old_sessions()      # Delete idle sessions

# Observer pattern
register_on_session_created()
register_on_session_deleted()
_notify_session_created()
_notify_session_deleted()

# Strategy pattern
set_path_strategy()         # Swap path resolution strategy
```

### 4. jdtls_client.py (350+ lines)

**Purpose:** Java compilation and error parsing

**Key Classes:**
- `JDTLSClient`
  - Wrapper around Java compiler
  - Uses: javac (fallback) or JDTLS (preferred)
  - Async: All methods are async

**Key Methods:**
```python
check_compilation_errors()  # Main entry point
    └─ Find all *.java files
    └─ For each file:
        ├─ _compile_file()  # Run javac
        └─ _parse_javac_errors()  # Regex parse stderr
    └─ Return errors[]

_compile_file()             # Async javac invocation
    └─ subprocess.run() with timeout

_parse_javac_errors()       # Regex-based parsing
    ├─ Pattern: "File.java:line: severity: message"
    └─ Extract: file, line, column, severity, message, code

_find_jdtls()               # Discover JDTLS installation
_find_java_home()           # Discover Java
_find_launcher_jar()        # Find JDTLS JAR
_find_config_dir()          # Find platform-specific config
```

**Error Parsing Detail:**

Input (javac stderr):
```
src/main/java/com/example/Main.java:5: error: cannot find symbol
    System.out.prinln("Hello");
                    ^
  symbol:   method prinln(String)
  location: class PrintStream
```

Output (structured error):
```json
{
  "file": "com/example/Main.java",
  "line": 5,
  "column": 20,
  "severity": "error",
  "message": "cannot find symbol",
  "code": "System.out.prinln(\"Hello\");"
}
```

### 5. error_recommendation_engine.py (300+ lines)

**Purpose:** Intelligent error fix suggestions

**Key Classes:**
- `RecommendationStrategy` (ABC)
  - Strategy pattern base class
  - Methods: can_handle(), get_recommendations()

- Strategy Implementations (8 total)
  - `CannotFindSymbolStrategy`
  - `SyntaxErrorStrategy`
  - `MissingSemicolonStrategy`
  - `TypeMismatchStrategy`
  - `MethodSignatureStrategy`
  - `DuplicateDeclarationStrategy`
  - `PackageNotFoundStrategy`
  - `UnreachableCodeStrategy`

- `ErrorRecommendationEngine`
  - Registry pattern for strategies
  - Ordered matching (first match wins)
  - Fallback to default recommendations

**Key Methods:**
```python
get_recommendations()       # Main entry point
    ├─ For each strategy (in order):
    │  └─ if strategy.can_handle(error):
    │     └─ return strategy.get_recommendations()
    └─ Default recommendations (fallback)

register_strategy()         # Add custom strategy (extensible)
    └─ Insert at beginning (custom first)
```

## Data Flow

### Typical Workflow: Create → Write → Check → Get Recommendations

```
User/Client
    │
    ├─1─→ create_session("my-project")
    │      │
    │      ▼ JavaErrorCheckerServer._handle_create_session()
    │      │
    │      ├─→ SessionManager.create_session()
    │      │    ├─ UUID generation: abc123...
    │      │    ├─ Create /tmp/jdtls-workspaces/abc123/
    │      │    ├─ Create src/main/java/ and src/test/java/
    │      │    ├─ Create Session dataclass
    │      │    └─ SessionRepository.create(session)
    │      │
    │      └─ Return: {"session_id": "abc123", "status": "created"}
    │
    ├─2─→ write_java_file(session_id, "com/example/Main.java", code)
    │      │
    │      ▼ JavaErrorCheckerServer._handle_write_java_file()
    │      │
    │      ├─→ SessionManager.get_session(session_id)
    │      │    └─ Update last_accessed timestamp
    │      │
    │      ├─→ SessionManager.write_file()
    │      │    ├─ Path resolution (JavaMainPathStrategy):
    │      │    │  "com/example/Main.java" →
    │      │    │  /tmp/jdtls-workspaces/abc123/src/main/java/com/example/Main.java
    │      │    │
    │      │    ├─ Create parent directories
    │      │    └─ Write file to disk
    │      │
    │      └─ Return: {"status": "success", "file_path": "com/example/Main.java"}
    │
    ├─3─→ check_errors(session_id)
    │      │
    │      ▼ JavaErrorCheckerServer._handle_check_errors()
    │      │
    │      ├─→ SessionManager.get_workspace_path(session_id)
    │      │    └─ Return: /tmp/jdtls-workspaces/abc123/
    │      │
    │      ├─→ JDTLSClient.check_compilation_errors()
    │      │    ├─ rglob("*.java") → find all Java files
    │      │    │
    │      │    ├─ For each file:
    │      │    │  ├─ Run: javac -d temp -cp src/main/java file.java
    │      │    │  ├─ Capture stderr
    │      │    │  └─ _parse_javac_errors() → extract structured error
    │      │    │
    │      │    └─ Return: [error1, error2, ...]
    │      │
    │      └─ Return: {
    │            "status": "success",
    │            "error_count": N,
    │            "errors": [...]
    │          }
    │
    └─4─→ get_recommendations(session_id, error)
           │
           ▼ JavaErrorCheckerServer._handle_get_recommendations()
           │
           ├─→ ErrorRecommendationEngine.get_recommendations()
           │    │
           │    ├─ error.message = "cannot find symbol"
           │    │
           │    ├─ For each strategy:
           │    │  ├─ CannotFindSymbolStrategy.can_handle() → true
           │    │  └─ Return strategy.get_recommendations()
           │    │
           │    └─ Return: [
           │        "Check that name is spelled correctly",
           │        "Ensure required import is present",
           │        "Verify variable is declared"
           │      ]
           │
           └─ Return: {
                "status": "success",
                "recommendations": [...]
              }
```

### Batch Write Workflow

```
write_multiple_files(session_id, [
    {"file_path": "A.java", "content": "..."},
    {"file_path": "B.java", "content": "..."},
    {"file_path": "C.java", "content": "..."}
])
    │
    ├─ SessionManager.write_multiple_files()
    │   │
    │   ├─ Get session (update last_accessed)
    │   │
    │   ├─ For each file:
    │   │  ├─ Validate file_path and content
    │   │  ├─ Resolve path using strategy
    │   │  ├─ Create parent directories
    │   │  ├─ Write file (catch exceptions)
    │   │  └─ Track written/failed counts
    │   │
    │   └─ Return: {
    │        "success": true,
    │        "written": 3,
    │        "failed": 0,
    │        "total": 3,
    │        "failed_files": []
    │      }
```

## Design Patterns In-Depth

### 1. Transport Abstraction (Strategy/Adapter)

**Pattern:** Separate transport mechanism from core logic

**Implementation:**
- Abstract `ServerTransport` base class
- Multiple implementations: Stdio, SSE, (future: WebSocket, gRPC)
- Core `JavaErrorCheckerServer` knows nothing about transport

**Benefits:**
- Easy to add new transports
- Testable: Can mock transport
- Reusable across different deployment scenarios

**Code:**
```python
# Transport interface
class ServerTransport(ABC):
    @abstractmethod
    async def run(self, server: JavaErrorCheckerServer) -> None:
        pass

# Implementations
class StdioServerTransport(ServerTransport):
    async def run(self, server):
        server._register_handlers()
        async with stdio_server(server.server) as (read, write):
            pass

class SSEServerTransport(ServerTransport):
    async def run(self, server):
        app = Starlette(routes=[...])
        await uvicorn_run(app, ...)

# Usage
server = JavaErrorCheckerServer()
transport = StdioServerTransport()  # or SSEServerTransport()
await transport.run(server)
```

### 2. Command Pattern (Tool Routing)

**Pattern:** Encapsulate tool requests as objects

**Implementation:**
- `_route_tool_call()` dispatches to handler methods
- Handlers named `_handle_<tool_name>()`
- Dictionary mapping tool names to handlers

**Benefits:**
- Centralized routing logic
- Easy to add/remove tools
- Consistent handler interface

**Code:**
```python
async def _route_tool_call(self, name: str, arguments: Dict) -> list[TextContent]:
    handlers = {
        "create_session": self._handle_create_session,
        "write_java_file": self._handle_write_java_file,
        "check_errors": self._handle_check_errors,
        # ...
    }
    handler = handlers.get(name)
    if handler:
        return await handler(arguments)
    else:
        return [TextContent(type="text", text="Unknown tool")]
```

### 3. Strategy Pattern (Error Recommendations)

**Pattern:** Encapsulate different error handling strategies

**Implementation:**
- Base `RecommendationStrategy` class
- 8 concrete strategy implementations
- Registry in `ErrorRecommendationEngine`
- Ordered matching (first match wins)

**Benefits:**
- Extensible without modifying engine
- Easy to add new error patterns
- Testable in isolation

**Code:**
```python
class RecommendationStrategy(ABC):
    @abstractmethod
    def can_handle(self, error: Dict) -> bool:
        pass

    @abstractmethod
    def get_recommendations(self, error: Dict) -> List[str]:
        pass

class CannotFindSymbolStrategy(RecommendationStrategy):
    def can_handle(self, error):
        return "cannot find symbol" in error.get("message", "").lower()

    def get_recommendations(self, error):
        return [...]

# Usage
engine = ErrorRecommendationEngine()
recommendations = engine.get_recommendations(error)
```

### 4. Strategy Pattern (Path Resolution)

**Pattern:** Different path resolution rules for different file types

**Implementation:**
- Base `PathResolutionStrategy` class
- `JavaMainPathStrategy`: src/main/java/
- `JavaTestPathStrategy`: src/test/java/
- Swappable via `set_path_strategy()`

**Benefits:**
- Support different project structures
- No hardcoded path logic
- Easy to extend for custom layouts

**Code:**
```python
class PathResolutionStrategy(ABC):
    @abstractmethod
    def resolve_path(self, workspace: Path, file_path: str) -> Path:
        pass

class JavaMainPathStrategy(PathResolutionStrategy):
    def resolve_path(self, workspace, file_path):
        if file_path.startswith("src/"):
            return workspace / file_path
        return workspace / "src" / "main" / "java" / file_path

# Usage
manager = SessionManager()
manager.set_path_strategy(JavaTestPathStrategy())
```

### 5. Repository Pattern (Data Access)

**Pattern:** Encapsulate data access logic

**Implementation:**
- `SessionRepository` class with CRUD methods
- Thread-safe with locks
- In-memory Dict backing store
- Could be swapped for database

**Benefits:**
- Encapsulated data access
- Thread-safe operations
- Easy to swap implementation (database, Redis, etc.)

**Code:**
```python
class SessionRepository:
    def __init__(self):
        self._sessions = {}
        self._lock = Lock()

    def create(self, session):
        with self._lock:
            self._sessions[session.session_id] = session

    def get(self, session_id):
        with self._lock:
            return self._sessions.get(session_id)

    # ... update, delete, list_all, clear
```

### 6. Singleton Pattern (SessionManager - Optional)

**Pattern:** Ensure single instance and global access point

**Implementation:**
- Class method `get_instance()` returns singleton
- Thread-safe initialization with lock
- Optional: Direct instantiation still works

**Benefits:**
- Single authority for session management
- Global access point
- Optional: Can be used as regular class too

**Code:**
```python
class SessionManager:
    _instance = None
    _lock = Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

# Usage
manager = SessionManager.get_instance()  # Singleton
# OR
manager = SessionManager()  # Regular instantiation
```

### 7. Factory Pattern (Transport Creation)

**Pattern:** Decouple transport instantiation

**Implementation:**
- `TransportFactory` class with registry
- `create()` method for instantiation
- `register()` method for custom transports

**Benefits:**
- Decouple transport creation from usage
- Easy to add custom transports
- Runtime selection of transport

**Code:**
```python
class TransportFactory:
    _transports = {
        "stdio": StdioServerTransport,
        "sse": SSEServerTransport,
    }

    @classmethod
    def create(cls, transport_type, **kwargs):
        transport_class = cls._transports.get(transport_type)
        return transport_class(**kwargs)

    @classmethod
    def register(cls, name, transport_class):
        cls._transports[name] = transport_class

# Usage
transport = TransportFactory.create("sse", host="0.0.0.0", port=8000)
```

### 8. Observer Pattern (Session Events)

**Pattern:** Notify interested parties of session events

**Implementation:**
- `register_on_session_created()` and `register_on_session_deleted()`
- Callback list in SessionManager
- `_notify_*()` methods trigger callbacks

**Benefits:**
- Extensible without modifying SessionManager
- Decoupled event handling
- Ready for monitoring, logging, analytics

**Code:**
```python
class SessionManager:
    def __init__(self):
        self._on_session_created = []
        self._on_session_deleted = []

    def register_on_session_created(self, callback):
        self._on_session_created.append(callback)

    def _notify_session_created(self, session):
        for callback in self._on_session_created:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Callback error: {e}")

# Usage
manager = SessionManager()
manager.register_on_session_created(lambda s: print(f"Session created: {s.session_id}"))
manager.register_on_session_deleted(lambda sid: print(f"Session deleted: {sid}"))
```

## Thread Safety

### Thread-Safe Components

**SessionRepository:**
```python
class SessionRepository:
    def __init__(self):
        self._sessions = {}
        self._lock = Lock()  # Protects _sessions

    def create(self, session):
        with self._lock:  # Acquire lock
            self._sessions[session.session_id] = session
        # Release lock automatically
```

**SessionManager Singleton:**
```python
class SessionManager:
    _instance = None
    _lock = Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:  # Double-checked locking
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
```

### Safe Concurrent Access Pattern

```
Session 1: create_session("proj1")
    ├─ Get lock → Create session → Release lock → Return sid1

Session 2: create_session("proj2") [concurrent]
    ├─ Wait for lock (Session 1 holding) →
    └─ When released: Get lock → Create session → Release lock → Return sid2

Both sessions proceed in exclusive lock sections
```

## Error Handling

### Hierarchy of Error Handling

```
Level 1: Tool Handler (try-catch entire operation)
    └─ _handle_create_session():
        try:
            # All operations
        except Exception as e:
            # Return error response

Level 2: Sub-operation (partial failure handling)
    └─ write_multiple_files():
        for file in files:
            try:
                write_file(file)
            except:
                failed.append(file)  # Continue with others

Level 3: Specific operations (targeted handling)
    └─ _compile_file():
        try:
            subprocess.run(javac, timeout=30)
        except subprocess.TimeoutExpired:
            # Timeout handling
        except FileNotFoundError:
            # javac not found
```

### Error Response Format

```python
# Success
{
    "status": "success",
    "session_id": "...",
    "data": {...}
}

# Partial success
{
    "status": "success",
    "written": 10,
    "failed": 2,
    "failed_files": [
        {"file_path": "A.java", "error": "..."},
        {"file_path": "B.java", "error": "..."}
    ]
}

# Failure
{
    "status": "error",
    "message": "Detailed error message"
}
```

## Extension Points

### Adding a New Tool

1. **Define tool in `_get_tools()`:**
```python
def _get_tools(self):
    return [
        # ...existing tools...
        Tool(
            name="my_new_tool",
            description="Do something",
            inputSchema={...}
        )
    ]
```

2. **Add handler method:**
```python
async def _handle_my_new_tool(self, arguments: Dict) -> list[TextContent]:
    # Implementation
    return await self._format_response({"status": "success", ...})
```

3. **Update routing:**
```python
async def _route_tool_call(self, name, arguments):
    handlers = {
        # ...
        "my_new_tool": self._handle_my_new_tool,
    }
```

### Adding a Custom Recommendation Strategy

```python
from error_recommendation_engine import RecommendationStrategy, ErrorRecommendationEngine

class MyCustomStrategy(RecommendationStrategy):
    def can_handle(self, error: Dict) -> bool:
        return "my pattern" in error.get("message", "").lower()

    def get_recommendations(self, error: Dict) -> List[str]:
        return ["Recommendation 1", "Recommendation 2"]

# Register
engine = ErrorRecommendationEngine()
engine.register_strategy(MyCustomStrategy())
```

### Adding a Custom Transport

```python
from transports import ServerTransport, TransportFactory

class MyCustomTransport(ServerTransport):
    async def run(self, server: JavaErrorCheckerServer):
        server._register_handlers()
        # Custom transport implementation
        pass

# Register
TransportFactory.register("my_custom", MyCustomTransport)

# Use
transport = TransportFactory.create("my_custom")
```

## Performance Optimization

### Bottlenecks & Solutions

| Bottleneck | Impact | Solution |
|---|---|---|
| Full recompilation each check | High | Implement incremental compilation |
| Sequential file writes | Medium | Use write_multiple_files (already optimized) |
| Workspace cleanup | Low | Background cleanup thread |
| In-memory session store | Medium | Use database for large deployments |
| File system I/O | Medium | Use SSD, optimize Path operations |

### Caching Opportunities

```python
# Could cache:
1. Compilation results (with file hash)
2. Recommendation matches (error message → strategy)
3. JDTLS server instance (currently recreated each time)
4. File listings (with invalidation on write)
```

### Scalability Considerations

**Current Limitations:**
- Sessions in-memory only (lost on restart)
- Single process (no horizontal scaling)
- No distributed session state

**Future Improvements:**
- Redis-backed SessionRepository
- Distributed JDTLS cluster
- Load balancer with session affinity
- Async I/O for file operations (currently blocking)
