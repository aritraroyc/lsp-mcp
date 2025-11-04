#!/usr/bin/env python3
"""
Complete Example: LangGraph Agentic Workflow Framework

This example demonstrates the complete LangGraph-based agentic workflow
framework with all components:
- Subgraph Registry
- Router Agent
- Abstract Subgraphs
- Main Orchestrator
- A2A Communication (optional)

Usage:
    python examples/complete_workflow_example.py
    python examples/complete_workflow_example.py --with-a2a
"""

import asyncio
import logging
from typing import Set

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph_framework.registry import (
    SubgraphRegistry,
    SubgraphMetadata,
    SubgraphCapability,
    get_global_registry
)
from langgraph_framework.router import (
    RouterAgent,
    RoutingContext,
    RoutingStrategy,
    AdaptiveRouter
)
from langgraph_framework.subgraphs import (
    CodeGenerationSubgraph,
    ErrorCheckingSubgraph,
    RefactoringSubgraph,
    SubgraphState,
    create_subgraph_from_template
)
from langgraph_framework.orchestrator import (
    MainOrchestrator,
    OrchestratorState,
    create_orchestrator
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_registry():
    """Demonstrate the Subgraph Registry System."""
    print("\n" + "="*70)
    print("DEMONSTRATION 1: Subgraph Registry System")
    print("="*70)
    
    # Create a registry
    registry = SubgraphRegistry()
    
    # Register some subgraphs
    print("\n1. Registering subgraphs...")
    
    codegen = CodeGenerationSubgraph(
        name="java_codegen",
        programming_languages={"java"},
        auto_register=False
    )
    codegen.register(registry)
    print(f"   ✓ Registered: {codegen.name}")
    
    error_checker = ErrorCheckingSubgraph(
        name="java_error_checker",
        auto_register=False
    )
    error_checker.register(registry)
    print(f"   ✓ Registered: {error_checker.name}")
    
    refactorer = RefactoringSubgraph(
        name="java_refactorer",
        auto_register=False
    )
    refactorer.register(registry)
    print(f"   ✓ Registered: {refactorer.name}")
    
    # Show registry stats
    print("\n2. Registry Statistics:")
    stats = registry.get_stats()
    print(f"   Total subgraphs: {stats['total_subgraphs']}")
    print(f"   Capabilities: {list(stats['capabilities'].keys())}")
    
    # Find subgraphs by capability
    print("\n3. Finding subgraphs by capability:")
    code_generators = registry.find_by_capability(SubgraphCapability.CODE_GENERATION)
    print(f"   Code generators: {[s.metadata.name for s in code_generators]}")
    
    error_checkers = registry.find_by_capability(SubgraphCapability.ERROR_CHECKING)
    print(f"   Error checkers: {[s.metadata.name for s in error_checkers]}")
    
    # Find best match
    print("\n4. Finding best match for requirements:")
    best = registry.find_best_match(
        required_capabilities={SubgraphCapability.CODE_GENERATION},
        context_tags={"java"}
    )
    print(f"   Best match: {best.metadata.name if best else 'None'}")


async def demonstrate_router():
    """Demonstrate the Router Agent Logic."""
    print("\n" + "="*70)
    print("DEMONSTRATION 2: Router Agent Logic")
    print("="*70)
    
    # Create registry and register subgraphs
    registry = SubgraphRegistry()
    
    # Register multiple code generators with different priorities
    metadata1 = SubgraphMetadata(
        name="basic_codegen",
        description="Basic code generator",
        capabilities={SubgraphCapability.CODE_GENERATION},
        tags={"java"},
        priority=30
    )
    registry.register(metadata1, lambda: "graph1")
    
    metadata2 = SubgraphMetadata(
        name="advanced_codegen",
        description="Advanced code generator with error checking",
        capabilities={SubgraphCapability.CODE_GENERATION, SubgraphCapability.ERROR_CHECKING},
        tags={"java", "python"},
        priority=80
    )
    registry.register(metadata2, lambda: "graph2")
    
    # Create routers
    print("\n1. Creating routers...")
    basic_router = RouterAgent(registry=registry)
    adaptive_router = AdaptiveRouter(registry=registry, learning_rate=0.3)
    print("   ✓ Basic router created")
    print("   ✓ Adaptive router created")
    
    # Test different routing strategies
    print("\n2. Testing routing strategies:")
    
    context = RoutingContext(
        task_type="code_generation",
        required_capabilities={SubgraphCapability.CODE_GENERATION},
        context_tags={"java"}
    )
    
    # Best match
    decision = basic_router.route(context, RoutingStrategy.BEST_MATCH)
    print(f"   BEST_MATCH: {decision.selected_subgraph.metadata.name if decision.selected_subgraph else 'None'}")
    print(f"               Score: {decision.score:.3f}")
    
    # Priority
    decision = basic_router.route(context, RoutingStrategy.PRIORITY)
    print(f"   PRIORITY: {decision.selected_subgraph.metadata.name if decision.selected_subgraph else 'None'}")
    print(f"             Score: {decision.score:.3f}")
    
    # Round robin
    print("\n3. Round-robin routing (5 iterations):")
    for i in range(5):
        decision = basic_router.route(context, RoutingStrategy.ROUND_ROBIN)
        print(f"   Iteration {i+1}: {decision.selected_subgraph.metadata.name if decision.selected_subgraph else 'None'}")
    
    # Adaptive routing with performance feedback
    print("\n4. Adaptive routing with performance feedback:")
    
    # Simulate poor performance for basic_codegen
    for _ in range(3):
        adaptive_router.record_performance("basic_codegen", 0.3)
    print("   ✓ Recorded low performance for basic_codegen")
    
    # Simulate good performance for advanced_codegen
    for _ in range(3):
        adaptive_router.record_performance("advanced_codegen", 0.95)
    print("   ✓ Recorded high performance for advanced_codegen")
    
    # Route and see adaptation
    decision = adaptive_router.route(context)
    print(f"   Adaptive selection: {decision.selected_subgraph.metadata.name if decision.selected_subgraph else 'None'}")
    print(f"   Reason: {decision.reason}")
    
    # Show routing stats
    print("\n5. Routing statistics:")
    stats = basic_router.get_routing_stats()
    print(f"   Total routing decisions: {stats['total_routing_decisions']}")
    print(f"   Success rate: {stats['success_rate']*100:.1f}%")


async def demonstrate_subgraphs():
    """Demonstrate Abstract Subgraph Classes."""
    print("\n" + "="*70)
    print("DEMONSTRATION 3: Abstract Subgraph Classes")
    print("="*70)
    
    print("\n1. Executing Code Generation Subgraph:")
    codegen = CodeGenerationSubgraph(name="demo_codegen", auto_register=False)
    
    input_state = SubgraphState(
        subgraph_name="demo_codegen",
        input_data={
            "requirements": "Create a Calculator class with add and subtract methods",
            "language": "java"
        }
    )
    
    result_dict = await codegen.execute(input_state)
    print(f"   Status: {result_dict['status'].value}")
    print(f"   Generated code preview: {result_dict['output_data'].get('generated_code', '')[:100]}...")
    
    print("\n2. Executing Error Checking Subgraph:")
    error_checker = ErrorCheckingSubgraph(name="demo_error_checker", auto_register=False)
    
    input_state = SubgraphState(
        subgraph_name="demo_error_checker",
        input_data={
            "code": "public class Test { public void method() { } }"
        }
    )
    
    result_dict = await error_checker.execute(input_state)
    print(f"   Status: {result_dict['status'].value}")
    print(f"   Errors found: {result_dict['output_data'].get('error_count', 0)}")
    
    print("\n3. Creating custom subgraph from template:")
    
    def validate_node(state: SubgraphState) -> SubgraphState:
        state.mark_started()
        state.output_data["validated"] = True
        state.mark_completed()
        return state
    
    custom_subgraph = create_subgraph_from_template(
        name="custom_validator",
        capabilities={SubgraphCapability.CODE_REVIEW},
        node_functions={"validate": validate_node},
        edges=[("START", "validate"), ("validate", "END")],
        tags={"custom"},
        auto_register=False
    )
    
    input_state = SubgraphState(subgraph_name="custom_validator")
    result_dict = await custom_subgraph.execute(input_state)
    print(f"   Custom subgraph status: {result_dict['status'].value}")
    print(f"   Output: {result_dict['output_data']}")


async def demonstrate_orchestrator():
    """Demonstrate Main Graph Orchestrator."""
    print("\n" + "="*70)
    print("DEMONSTRATION 4: Main Graph Orchestrator")
    print("="*70)
    
    # Setup registry with subgraphs
    registry = SubgraphRegistry()
    
    codegen = CodeGenerationSubgraph(name="codegen", auto_register=False)
    codegen.register(registry)
    
    error_checker = ErrorCheckingSubgraph(name="error_checker", auto_register=False)
    error_checker.register(registry)
    
    refactorer = RefactoringSubgraph(name="refactorer", auto_register=False)
    refactorer.register(registry)
    
    # Define tasks
    tasks = [
        {
            "type": "generate_calculator",
            "required_capabilities": [SubgraphCapability.CODE_GENERATION.value],
            "tags": ["java"],
            "input": {
                "requirements": "Create a Calculator class",
                "language": "java"
            }
        },
        {
            "type": "check_calculator",
            "required_capabilities": [SubgraphCapability.ERROR_CHECKING.value],
            "input": {
                "code": "public class Calculator { }"
            }
        },
        {
            "type": "refactor_calculator",
            "required_capabilities": [SubgraphCapability.REFACTORING.value],
            "input": {
                "code": "public class Calculator { }"
            }
        }
    ]
    
    print(f"\n1. Creating orchestrator with {len(tasks)} tasks...")
    
    orchestrator, initial_state = create_orchestrator(
        workflow_id="demo_workflow",
        tasks=tasks,
        use_adaptive_routing=True,
        max_retries=2
    )
    
    # Override registry
    orchestrator.router.registry = registry
    orchestrator.registry = registry
    
    print("   ✓ Orchestrator created")
    print(f"   Workflow ID: {initial_state.workflow_id}")
    print(f"   Tasks queued: {len(initial_state.task_queue)}")
    
    print("\n2. Building and executing workflow...")
    graph = orchestrator.build_graph()
    compiled_graph = graph.compile()
    
    result_dict = await compiled_graph.ainvoke(initial_state)
    
    print(f"\n3. Workflow Results:")
    print(f"   Status: {result_dict['status'].value}")
    print(f"   Completed tasks: {len(result_dict['completed_tasks'])}")
    print(f"   Failed tasks: {len(result_dict['failed_tasks'])}")
    print(f"   Errors: {len(result_dict['errors'])}")
    
    print("\n4. Execution Statistics:")
    stats = orchestrator.get_execution_stats()
    print(f"   Workflow ID: {stats['workflow_id']}")
    print(f"   Router stats: {stats['router_stats']['total_routing_decisions']} decisions")
    print(f"   Registry: {stats['registry_stats']['total_subgraphs']} subgraphs")


async def demonstrate_a2a():
    """Demonstrate A2A Service Deployment."""
    print("\n" + "="*70)
    print("DEMONSTRATION 5: Agent-to-Agent (A2A) Service")
    print("="*70)
    
    try:
        from langgraph_framework.a2a import (
            ServiceDiscovery,
            ServiceEndpoint,
            ServiceProtocol,
            create_a2a_service
        )
        
        print("\n1. Creating service discovery registry...")
        discovery = ServiceDiscovery(health_check_interval=60)
        print("   ✓ Service discovery created")
        
        print("\n2. Registering service endpoints...")
        endpoint1 = ServiceEndpoint(
            service_name="codegen_service",
            protocol=ServiceProtocol.HTTP,
            host="localhost",
            port=8081,
            path="/api/v1",
            health_check_url="http://localhost:8081/health"
        )
        discovery.register_service(endpoint1)
        print(f"   ✓ Registered: {endpoint1.service_name} at {endpoint1.get_url()}")
        
        endpoint2 = ServiceEndpoint(
            service_name="error_check_service",
            protocol=ServiceProtocol.HTTP,
            host="localhost",
            port=8082,
            health_check_url="http://localhost:8082/health"
        )
        discovery.register_service(endpoint2)
        print(f"   ✓ Registered: {endpoint2.service_name} at {endpoint2.get_url()}")
        
        print("\n3. Listing registered services:")
        services = discovery.list_services()
        for svc in services:
            print(f"   - {svc.service_name}: {svc.get_url()}")
        
        print("\n4. A2A HTTP Server (not started in demo):")
        print("   To start A2A server, use:")
        print("   >>> server, endpoint = create_a2a_service(host='0.0.0.0', port=8080)")
        print("   >>> await server.start()  # or server.run()")
        
    except ImportError as e:
        print(f"\n⚠ A2A demonstration skipped: {e}")
        print("   Install aiohttp for A2A support: pip install aiohttp")


async def run_all_demonstrations():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("LANGGRAPH AGENTIC WORKFLOW FRAMEWORK")
    print("Complete Demonstration")
    print("="*70)
    
    await demonstrate_registry()
    await demonstrate_router()
    await demonstrate_subgraphs()
    await demonstrate_orchestrator()
    await demonstrate_a2a()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nAll components demonstrated successfully!")
    print("\nNext steps:")
    print("  1. Explore the framework modules in src/langgraph_framework/")
    print("  2. Run tests: pytest src/langgraph_framework/tests/")
    print("  3. Build your own subgraphs using the abstract classes")
    print("  4. Create custom orchestration workflows")
    print("  5. Deploy A2A services for distributed execution")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LangGraph Agentic Workflow Framework Demo"
    )
    parser.add_argument(
        "--demo",
        choices=["all", "registry", "router", "subgraphs", "orchestrator", "a2a"],
        default="all",
        help="Which demonstration to run"
    )
    
    args = parser.parse_args()
    
    if args.demo == "all":
        asyncio.run(run_all_demonstrations())
    elif args.demo == "registry":
        asyncio.run(demonstrate_registry())
    elif args.demo == "router":
        asyncio.run(demonstrate_router())
    elif args.demo == "subgraphs":
        asyncio.run(demonstrate_subgraphs())
    elif args.demo == "orchestrator":
        asyncio.run(demonstrate_orchestrator())
    elif args.demo == "a2a":
        asyncio.run(demonstrate_a2a())


if __name__ == "__main__":
    main()
