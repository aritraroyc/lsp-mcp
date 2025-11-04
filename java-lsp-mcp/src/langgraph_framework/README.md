# LangGraph Agentic Workflow Framework

A comprehensive framework for building sophisticated agentic workflows using LangGraph with dynamic subgraph management, intelligent routing, and orchestration capabilities.

## Features

### 🔧 Subgraph Registry System
- **Dynamic Registration**: Register and deregister subgraphs at runtime
- **Capability-Based Discovery**: Find subgraphs by capabilities and tags
- **Metadata Management**: Rich metadata describing subgraph functionality
- **Concurrency Control**: Built-in support for limiting concurrent executions
- **Thread-Safe**: Full thread-safety for concurrent access

### 🎯 Router Agent Logic
- **Multiple Routing Strategies**: 
  - Best Match (capability + context scoring)
  - Round Robin (load distribution)
  - Least Loaded (capacity-based)
  - Priority-Based (priority ordering)
- **Adaptive Routing**: Learn from performance and improve decisions
- **Context-Aware**: Consider tags and metadata in routing
- **Exclusion Support**: Exclude failed subgraphs for retry scenarios

### 📦 Abstract Subgraph Classes
- **Standardized Interfaces**: Consistent API for all subgraphs
- **Built-in State Management**: Automatic state tracking and lifecycle
- **Template System**: Create subgraphs from templates quickly
- **Example Implementations**:
  - CodeGenerationSubgraph
  - ErrorCheckingSubgraph
  - RefactoringSubgraph

### 🎼 Main Graph Orchestrator
- **Multi-Task Workflows**: Execute multiple tasks in sequence
- **Error Detection**: Automatic error detection and handling
- **Adaptive Re-routing**: Retry failed tasks with alternative subgraphs
- **State Management**: Track workflow state and execution history
- **Performance Tracking**: Built-in statistics and monitoring

### 🌐 Agent-to-Agent (A2A) Service
- **HTTP/REST API**: Expose subgraphs via HTTP endpoints
- **Service Discovery**: Dynamic service registration and lookup
- **Health Checking**: Automatic health monitoring
- **Remote Execution**: Execute subgraphs on remote services
- **Protocol Support**: HTTP, gRPC (extensible), WebSocket

## Installation

```bash
# Core framework
pip install langgraph langchain-core

# For A2A services (optional)
pip install aiohttp

# For testing
pip install pytest pytest-asyncio
```

## Quick Start

### 1. Register Subgraphs

```python
from langgraph_framework.registry import get_global_registry
from langgraph_framework.subgraphs import CodeGenerationSubgraph

# Create and register a subgraph
codegen = CodeGenerationSubgraph(
    name="java_codegen",
    programming_languages={"java"}
)

# Already auto-registered with global registry
registry = get_global_registry()
```

### 2. Route Tasks to Subgraphs

```python
from langgraph_framework.router import RouterAgent, RoutingContext
from langgraph_framework.registry import SubgraphCapability

router = RouterAgent()

context = RoutingContext(
    task_type="code_generation",
    required_capabilities={SubgraphCapability.CODE_GENERATION},
    context_tags={"java"}
)

decision = router.route(context)
print(f"Selected: {decision.selected_subgraph.metadata.name}")
```

### 3. Execute Subgraphs

```python
from langgraph_framework.subgraphs import SubgraphState

# Prepare input
input_state = SubgraphState(
    subgraph_name="java_codegen",
    input_data={
        "requirements": "Create a Calculator class",
        "language": "java"
    }
)

# Execute
result = await codegen.execute(input_state)
print(f"Status: {result.status.value}")
print(f"Output: {result.output_data}")
```

### 4. Orchestrate Workflows

```python
from langgraph_framework.orchestrator import create_orchestrator
from langgraph_framework.registry import SubgraphCapability

# Define tasks
tasks = [
    {
        "type": "generate_code",
        "required_capabilities": [SubgraphCapability.CODE_GENERATION.value],
        "input": {"requirements": "Create Calculator class"}
    },
    {
        "type": "check_errors",
        "required_capabilities": [SubgraphCapability.ERROR_CHECKING.value],
        "input": {"code": "..."}
    }
]

# Create and run orchestrator
orchestrator, initial_state = create_orchestrator(
    workflow_id="my_workflow",
    tasks=tasks
)

graph = orchestrator.build_graph()
compiled = graph.compile()
result = await compiled.ainvoke(initial_state)

print(f"Completed: {len(result.completed_tasks)}")
print(f"Failed: {len(result.failed_tasks)}")
```

### 5. Deploy A2A Services

```python
from langgraph_framework.a2a import create_a2a_service

# Create HTTP service
server, endpoint = create_a2a_service(
    host="0.0.0.0",
    port=8080,
    service_name="my_service"
)

# Run server (blocking)
server.run()

# Or start asynchronously
await server.start()
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Framework                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Registry   │───→│    Router    │───→│ Orchestrator │  │
│  │   System     │    │    Agent     │    │    Graph     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │         │
│         ↓                    ↓                    ↓         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Subgraph Implementations                  │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │  │
│  │  │CodeGen  │  │ErrorChk │  │Refactor │  ...        │  │
│  │  └─────────┘  └─────────┘  └─────────┘             │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                    │                    │         │
│         └────────────────────┴────────────────────┘         │
│                              ↓                               │
│                    ┌──────────────────┐                     │
│                    │  A2A Services    │                     │
│                    │  (HTTP/gRPC)     │                     │
│                    └──────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Subgraph Registry
- `SubgraphRegistry`: Main registry class
- `SubgraphMetadata`: Capability and configuration metadata
- `SubgraphCapability`: Enum of standard capabilities
- `get_global_registry()`: Access global registry instance

### Router
- `RouterAgent`: Basic routing with multiple strategies
- `AdaptiveRouter`: Learning-based adaptive routing
- `RoutingContext`: Context for routing decisions
- `RoutingStrategy`: Enum of routing strategies

### Subgraphs
- `BaseSubgraph`: Abstract base class for all subgraphs
- `SubgraphState`: Standard state structure
- `CodeGenerationSubgraph`: Example code generation implementation
- `ErrorCheckingSubgraph`: Example error checking implementation
- `RefactoringSubgraph`: Example refactoring implementation
- `create_subgraph_from_template()`: Factory for custom subgraphs

### Orchestrator
- `MainOrchestrator`: Main workflow orchestration
- `OrchestratorState`: Workflow state management
- `create_orchestrator()`: Factory for orchestrators

### A2A Services
- `A2AHttpServer`: HTTP server for subgraph execution
- `A2AHttpClient`: Client for remote subgraph execution
- `ServiceDiscovery`: Service registry and health checking
- `ServiceEndpoint`: Service endpoint metadata

## Testing

```bash
# Run all tests
pytest src/langgraph_framework/tests/

# Run specific test suites
pytest src/langgraph_framework/tests/test_registry.py
pytest src/langgraph_framework/tests/test_router.py
pytest src/langgraph_framework/tests/test_integration.py

# Run with coverage
pytest src/langgraph_framework/tests/ --cov=src/langgraph_framework --cov-report=html
```

## Examples

See `src/examples/complete_workflow_example.py` for a comprehensive demonstration of all features:

```bash
# Run all demonstrations
python src/examples/complete_workflow_example.py

# Run specific demonstrations
python src/examples/complete_workflow_example.py --demo registry
python src/examples/complete_workflow_example.py --demo router
python src/examples/complete_workflow_example.py --demo subgraphs
python src/examples/complete_workflow_example.py --demo orchestrator
python src/examples/complete_workflow_example.py --demo a2a
```

## Advanced Usage

### Creating Custom Subgraphs

```python
from langgraph_framework.subgraphs import BaseSubgraph, SubgraphState
from langgraph_framework.registry import SubgraphMetadata, SubgraphCapability
from langgraph.graph import StateGraph, START, END

class MyCustomSubgraph(BaseSubgraph[SubgraphState]):
    
    def get_metadata(self) -> SubgraphMetadata:
        return SubgraphMetadata(
            name=self.name,
            description="My custom subgraph",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags={"custom"},
            priority=60
        )
    
    def build_graph(self) -> StateGraph:
        graph = StateGraph(SubgraphState)
        
        graph.add_node("process", self._process)
        graph.add_edge(START, "process")
        graph.add_edge("process", END)
        
        return graph
    
    def _process(self, state: SubgraphState) -> SubgraphState:
        # Your processing logic
        state.mark_started()
        # ... do work ...
        state.mark_completed({"result": "success"})
        return state
```

### Adaptive Routing with Performance

```python
from langgraph_framework.router import AdaptiveRouter

router = AdaptiveRouter(learning_rate=0.3)

# Execute and record performance
result = await subgraph.execute(input_state)

# Calculate performance score (0.0 to 1.0)
performance = calculate_performance(result)
router.record_performance(subgraph.name, performance)

# Future routes will consider this performance
```

### Error Handling and Retry

```python
orchestrator = MainOrchestrator(
    workflow_id="robust_workflow",
    max_retries=3  # Retry up to 3 times
)

# The orchestrator automatically:
# 1. Detects failures
# 2. Excludes failed subgraphs
# 3. Routes to alternatives
# 4. Tracks retry attempts
```

### Remote A2A Execution

```python
from langgraph_framework.a2a import A2AHttpClient

client = A2AHttpClient()

# Execute on remote service
result = await client.execute_remote_subgraph(
    service_url="http://remote-host:8080",
    subgraph_name="code_generator",
    input_data={"requirements": "Create class"}
)

print(result["result"]["output_data"])
```

## Performance Considerations

- **Concurrency**: Set `max_concurrent` in metadata to limit parallel executions
- **Timeouts**: Configure `timeout_seconds` per subgraph
- **Caching**: Results are not cached by default; implement as needed
- **Registry Size**: Registry scales well to hundreds of subgraphs
- **Health Checks**: Configure appropriate intervals for A2A services

## Best Practices

1. **Capability Design**: Define specific, focused capabilities
2. **Priority Assignment**: Use priority to guide selection when multiple matches exist
3. **Tag Usage**: Use tags for context-based routing (language, environment, etc.)
4. **Error Handling**: Implement proper error handling in subgraph nodes
5. **State Management**: Use SubgraphState for consistent state tracking
6. **Testing**: Write tests for custom subgraphs using provided test utilities
7. **Monitoring**: Track orchestrator and router statistics for insights

## Contributing

Contributions are welcome! Please ensure:
- Tests pass: `pytest src/langgraph_framework/tests/`
- Code follows existing patterns
- Documentation is updated

## License

MIT License - See LICENSE file for details
