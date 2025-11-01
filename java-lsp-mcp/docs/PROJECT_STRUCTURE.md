# Project Structure & Navigation Guide

Quick reference guide to understand the refactored Java Error Checker MCP Service codebase.

## Refactored Project Layout

```
java-error-checker-mcp/
│
├── 📁 src/                         # All Python source code
│   │
│   ├── 📁 core/                    # Core business logic modules
│   │   ├── __init__.py
│   │   ├── base_server.py          # Core MCP server logic (transport-agnostic)
│   │   ├── transports.py           # Transport implementations
│   │   ├── session_manager.py      # Session & workspace management
│   │   ├── jdtls_client.py         # Java compilation & error parsing
│   │   ├── error_recommendation_engine.py  # Error fix recommendations
│   │   └── config.py               # Configuration management
│   │
│   ├── 📁 server/                  # Server entry points
│   │   ├── __init__.py
│   │   ├── server.py               # Stdio transport entry point
│   │   └── server_sse.py           # HTTP/SSE transport entry point
│   │
│   ├── 📁 client/                  # Client libraries
│   │   ├── __init__.py
│   │   └── langgraph_integration.py # LangGraph bridge & HTTP client
│   │
│   ├── 📁 tests/                   # Test suites
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_server.py          # Unit tests
│   │   ├── test_end_to_end.py      # Integration tests
│   │   └── test_sse_components.py  # Transport tests
│   │
│   ├── 📁 examples/                # Example implementations
│   │   ├── __init__.py
│   │   ├── example_client.py       # Simple example client
│   │   ├── agentic_workflow_example.py  # Multi-stage workflow
│   │   ├── langgraph_agent_example.py   # LangGraph integration
│   │   └── remote_langgraph_workflow.py # Remote HTTP/SSE workflow
│   │
│   └── __init__.py
│
├── 📁 docs/                        # Documentation (consolidated to 5 files)
│   ├── README.md                   # Main user guide & quick start
│   ├── ARCHITECTURE.md             # System design & patterns
│   ├── DEPLOYMENT.md               # Deployment & examples
│   ├── REFACTORING.md              # Refactoring summary
│   └── PROJECT_STRUCTURE.md        # Navigation guide (this file)
│
├── 📄 Configuration Files
│   ├── requirements.txt             # Python dependencies
│   ├── setup.py                    # Package setup
│   ├── Dockerfile                  # Docker image definition
│   ├── docker-compose.yml          # Docker Compose configuration
│   ├── .env (optional)             # Environment variables
│   └── CLAUDE.md                   # Claude IDE guidance
│
└── 📁 Other
    ├── .gitignore
    ├── LICENSE
    └── README (auto-symlink to docs/README.md)
```

## Module Descriptions

### 🔷 Core Business Logic

#### **base_server.py** (500+ lines)
**Purpose:** Transport-agnostic core MCP server logic

**Key Classes:**
- `ServerTransport` (ABC)
  - Abstract base class for transports
  - Methods: `send_response()`, `run()`

- `JavaErrorCheckerServer`
  - Main server orchestrator
  - ~20 handler methods for 10 tools
  - Uses: `SessionManager`, `JDTLSClient`, `ErrorRecommendationEngine`

**Key Methods:**
- `_register_handlers()` - Register all MCP tools
- `_route_tool_call()` - Command pattern dispatcher
- `_handle_*()` - 10 tool-specific handler methods
- `_format_response()` - MCP response formatting

**When to look here:** Need to understand tool logic or add new tools

---

#### **transports.py** (200+ lines)
**Purpose:** Transport mechanism abstraction & implementations

**Key Classes:**
- `ServerTransport` (ABC) - Base class
- `StdioServerTransport` - Stdio communication
- `JsonResponseTransport` (ABC) - JSON response base
- `SSEServerTransport` - HTTP/SSE communication
- `TransportFactory` - Factory for transport creation

**Key Methods:**
- `StdioServerTransport.run()` - Start stdio server
- `SSEServerTransport.run()` - Start HTTP server
- `TransportFactory.create()` - Create transport instance
- `TransportFactory.register()` - Register custom transport

**When to look here:** Adding new transport, understanding transport layer, creating custom transport

---

#### **session_manager.py** (550+ lines)
**Purpose:** Session lifecycle & workspace management

**Key Classes:**
- `Session` (dataclass) - Session metadata
- `PathResolutionStrategy` (ABC) - Path resolution interface
  - `JavaMainPathStrategy` - Resolve to src/main/java/
  - `JavaTestPathStrategy` - Resolve to src/test/java/
- `SessionRepository` - Repository pattern (CRUD + thread-safe)
- `SessionManager` - Orchestrator with Singleton, Observer, Strategy patterns

**Key Methods:**
- `create_session()` - Create new session with UUID
- `get_session()` - Retrieve session & update timestamp
- `delete_session()` - Delete session & cleanup
- `write_file()`, `write_multiple_files()` - File operations
- `read_file()`, `list_files()` - File reading
- `refresh_session()` - Extend session timeout
- `get_session_info()` - Session metadata
- `cleanup_old_sessions()` - Remove idle sessions
- `set_path_strategy()` - Swap path resolution
- `register_on_session_created/deleted()` - Observer pattern

**When to look here:** Session management, file operations, adding custom path strategy, thread safety

---

#### **jdtls_client.py** (350+ lines)
**Purpose:** Java compilation & error detection

**Key Classes:**
- `JDTLSClient` - Java compiler interface

**Key Methods:**
- `check_compilation_errors()` - Main entry: compile & report errors
- `_compile_file()` - Async javac invocation
- `_parse_javac_errors()` - Regex-based error parsing
- `_find_jdtls()`, `_find_java_home()` - Java discovery
- `start_server()`, `stop_server()` - JDTLS lifecycle

**When to look here:** Understanding error parsing, Java compilation, adding compilation features

---

#### **error_recommendation_engine.py** (300+ lines)
**Purpose:** Intelligent error fix recommendations

**Key Classes:**
- `RecommendationStrategy` (ABC) - Strategy base class
- 8 Concrete Strategies:
  - `CannotFindSymbolStrategy`
  - `SyntaxErrorStrategy`
  - `MissingSemicolonStrategy`
  - `TypeMismatchStrategy`
  - `MethodSignatureStrategy`
  - `DuplicateDeclarationStrategy`
  - `PackageNotFoundStrategy`
  - `UnreachableCodeStrategy`
- `ErrorRecommendationEngine` - Registry & matcher

**Key Methods:**
- `get_recommendations()` - Get recommendations for error
- `register_strategy()` - Register custom strategy
- Strategy methods: `can_handle()`, `get_recommendations()`

**When to look here:** Adding error patterns, understanding recommendations, custom strategies

---

#### **config.py** (27 lines)
**Purpose:** Centralized configuration

**Configuration Variables:**
- `WORKSPACE_BASE_DIR` - Session workspace directory
- `SESSION_TIMEOUT` - Session expiration timeout
- `JDTLS_PATH`, `JDTLS_MEMORY` - Java language server config
- `JAVA_HOME` - Java installation
- `LOG_FILE`, `LOG_LEVEL` - Logging config

**When to look here:** Understanding or changing configuration

---

### 🔷 Server Entry Points

#### **server.py** (47 lines)
**Purpose:** Stdio transport entry point for Claude Desktop

**Content:**
- Logging configuration
- `main()` entry point
- Creates `JavaErrorCheckerServer` and `StdioServerTransport`
- Invokes `await transport.run(server)`

**When to run:** `python src/server/server.py` for Claude Desktop integration

---

#### **server_sse.py** (235 lines)
**Purpose:** HTTP/SSE transport entry point for remote access

**Key Components:**
- `SSETransport` class (extends JsonResponseTransport)
- HTTP endpoints: `/sse` (POST), `/health` (GET)
- CORS middleware
- Uvicorn server setup
- `main()` entry point with argparse

**When to run:** `python src/server/server_sse.py --host 0.0.0.0 --port 8000` for remote access

---

### 🔷 Tests & Examples

#### **test_server.py** (177 lines)
Unit tests for SessionManager and JDTLSClient

**When to use:** `pytest src/tests/test_server.py -v`

---

#### **test_end_to_end.py** (170+ lines)
Integration tests for complete workflows

**When to use:** `pytest test_end_to_end.py -v`

---

#### **example_client.py** (335 lines)
Simple example demonstrating all tools

**When to use:** `python src/examples/example_client.py` or `python src/examples/example_client.py --interactive`

---

#### **langgraph_agent_example.py** (370+ lines)
LangGraph agent integration example

**Key Class:**
- `JavaErrorCheckerClient` - HTTP client wrapper
- `create_langgraph_tools()` - Factory for LangGraph tools

**When to use:** Reference for LangGraph integration

---

#### **langgraph_integration.py** (387 lines)
LangGraph bridge & HTTP client utilities

**When to use:** Import into LangGraph workflows

---

## Design Patterns Map

| Pattern | File | Class | Purpose |
|---------|------|-------|---------|
| **Strategy** | error_recommendation_engine.py | RecommendationStrategy | Different error patterns |
| **Strategy** | session_manager.py | PathResolutionStrategy | Different path rules |
| **Repository** | session_manager.py | SessionRepository | Data access layer |
| **Singleton** | session_manager.py | SessionManager | Global access point |
| **Factory** | transports.py | TransportFactory | Create transports |
| **Command** | base_server.py | _route_tool_call() | Tool dispatching |
| **Adapter** | transports.py | ServerTransport | Unified interface |
| **Observer** | session_manager.py | register_on_* | Event callbacks |

## Navigation by Task

### ✅ "I want to understand how the system works"
1. Start: `README_CONSOLIDATED.md` - High-level overview
2. Then: `ARCHITECTURE_DETAILED.md` - System design
3. Finally: Review `base_server.py` - Core logic

### ✅ "I want to add a new tool"
1. Open: `base_server.py`
2. Add to `_get_tools()` - Tool definition
3. Add `_handle_*()` method - Handler logic
4. Update `_route_tool_call()` - Add handler routing

### ✅ "I want to add error recommendation"
1. Open: `error_recommendation_engine.py`
2. Create class extending `RecommendationStrategy`
3. Implement `can_handle()` and `get_recommendations()`
4. Test with `ErrorRecommendationEngine.register_strategy()`

### ✅ "I want to deploy to cloud"
1. Read: `DEPLOYMENT_AND_EXAMPLES.md`
2. Choose: Docker / Kubernetes / Cloud Run
3. Follow: Specific deployment section
4. Run: `docker-compose up` or cloud CLI commands

### ✅ "I want to integrate with LangGraph"
1. Read: `DEPLOYMENT_AND_EXAMPLES.md` - LangGraph section
2. Reference: `langgraph_agent_example.py` - Example workflow
3. Import: `from langgraph_integration import JavaErrorCheckerClient`

### ✅ "I want to understand refactoring"
1. Read: `REFACTORING_SUMMARY.md` - Complete refactoring details
2. Compare: Before/after code in summary
3. Review: Design patterns applied

### ✅ "I want to add custom transport"
1. Read: `ARCHITECTURE_DETAILED.md` - Extension Points
2. Create: Class extending `ServerTransport`
3. Register: `TransportFactory.register("name", MyTransport)`
4. Use: `transport = TransportFactory.create("name")`

### ✅ "I want to contribute"
1. Read: `REFACTORING_SUMMARY.md` - Code quality improvements
2. Review: Design patterns being used
3. Follow: Established patterns when adding code
4. Test: Add unit tests for new features

## File Dependencies Graph

```
server.py → base_server.py → session_manager.py
         → transports.py  → base_server.py
                          → session_manager.py

server_sse.py → base_server.py
             → transports.py
             → session_manager.py

base_server.py → session_manager.py
              → jdtls_client.py
              → error_recommendation_engine.py

jdtls_client.py → config.py

langgraph_integration.py → (no internal imports, external HTTP client)

Examples use:
  - langgraph_integration.py
  - base_server.py
  - session_manager.py
```

## Quick Reference

### Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `JavaErrorCheckerServer` | base_server.py | Main MCP server |
| `SessionManager` | session_manager.py | Session management |
| `SessionRepository` | session_manager.py | Data access |
| `JDTLSClient` | jdtls_client.py | Java compilation |
| `ErrorRecommendationEngine` | error_recommendation_engine.py | Recommendations |
| `TransportFactory` | transports.py | Transport creation |
| `JavaErrorCheckerClient` | langgraph_integration.py | HTTP client |

### Key Methods

| Method | File | Purpose |
|--------|------|---------|
| `_route_tool_call()` | base_server.py | Tool dispatching |
| `write_multiple_files()` | session_manager.py | Batch file write |
| `check_compilation_errors()` | jdtls_client.py | Error checking |
| `get_recommendations()` | error_recommendation_engine.py | Error suggestions |
| `create()` | transports.py | Transport factory |

### Environment Variables

- `JAVA_HOME` - Java installation
- `JDTLS_WORKSPACE_DIR` - Workspace base directory
- `SESSION_TIMEOUT` - Session expiration (seconds)
- `LOG_FILE` - Log file path
- `LOG_LEVEL` - Logging level (DEBUG, INFO, etc.)

## Documentation Files Guide

| File | Audience | Best For |
|------|----------|----------|
| README_CONSOLIDATED.md | Users & Developers | Features, usage, installation |
| ARCHITECTURE_DETAILED.md | Architects & Advanced Developers | System design, patterns, extensions |
| DEPLOYMENT_AND_EXAMPLES.md | DevOps & Integrators | Deployment, examples, cloud setup |
| REFACTORING_SUMMARY.md | Maintainers & Contributors | Understanding changes, patterns applied |
| PROJECT_STRUCTURE.md | Everyone | Navigation & file descriptions |

---

**📌 Start Here:** Read `README_CONSOLIDATED.md`, then `ARCHITECTURE_DETAILED.md`, then dive into code!
