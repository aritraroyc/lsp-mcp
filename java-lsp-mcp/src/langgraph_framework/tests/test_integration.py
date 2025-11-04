"""
Integration tests for LangGraph Framework
"""

import pytest
import asyncio
from src.langgraph_framework.registry import (
    SubgraphRegistry,
    SubgraphMetadata,
    SubgraphCapability,
    get_global_registry
)
from src.langgraph_framework.router import RouterAgent, RoutingContext
from src.langgraph_framework.subgraphs import (
    CodeGenerationSubgraph,
    ErrorCheckingSubgraph,
    RefactoringSubgraph,
    SubgraphState
)
from src.langgraph_framework.orchestrator import (
    MainOrchestrator,
    OrchestratorState,
    create_orchestrator
)


class TestSubgraphIntegration:
    """Integration tests for subgraph execution."""
    
    @pytest.mark.asyncio
    async def test_code_generation_subgraph_execution(self):
        """Test executing code generation subgraph."""
        subgraph = CodeGenerationSubgraph(
            name="test_codegen",
            auto_register=False
        )
        
        input_state = SubgraphState(
            subgraph_name="test_codegen",
            input_data={
                "requirements": "Create a Hello World class",
                "language": "java"
            }
        )
        
        result_dict = await subgraph.execute(input_state)
        
        # LangGraph returns dicts, not state objects
        assert "output_data" in result_dict
        assert "generated_code" in result_dict["output_data"]
        assert result_dict["status"].value == "completed"
    
    @pytest.mark.asyncio
    async def test_error_checking_subgraph_execution(self):
        """Test executing error checking subgraph."""
        subgraph = ErrorCheckingSubgraph(
            name="test_error_checker",
            auto_register=False
        )
        
        input_state = SubgraphState(
            subgraph_name="test_error_checker",
            input_data={
                "code": "class Test { }"
            }
        )
        
        result_dict = await subgraph.execute(input_state)
        
        assert "output_data" in result_dict
        assert "errors" in result_dict["output_data"]
        assert "error_count" in result_dict["output_data"]
    
    @pytest.mark.asyncio
    async def test_refactoring_subgraph_execution(self):
        """Test executing refactoring subgraph."""
        subgraph = RefactoringSubgraph(
            name="test_refactorer",
            auto_register=False
        )
        
        input_state = SubgraphState(
            subgraph_name="test_refactorer",
            input_data={
                "code": "public class Old { }"
            }
        )
        
        result_dict = await subgraph.execute(input_state)
        
        assert "output_data" in result_dict
        assert "refactored_code" in result_dict["output_data"]
        assert result_dict["status"].value == "completed"


class TestRegistryRouterIntegration:
    """Integration tests for registry and router."""
    
    def setup_method(self):
        """Setup test environment."""
        self.registry = SubgraphRegistry()
        self.router = RouterAgent(registry=self.registry)
    
    def test_register_and_route(self):
        """Test registering subgraphs and routing to them."""
        # Register subgraphs
        codegen = CodeGenerationSubgraph(name="codegen", auto_register=False)
        codegen.register(self.registry)
        
        error_checker = ErrorCheckingSubgraph(name="error_checker", auto_register=False)
        error_checker.register(self.registry)
        
        # Route to code generation
        context = RoutingContext(
            task_type="generate_code",
            required_capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        decision = self.router.route(context)
        
        assert decision.selected_subgraph is not None
        assert decision.selected_subgraph.metadata.name == "codegen"
        
        # Route to error checking
        context2 = RoutingContext(
            task_type="check_errors",
            required_capabilities={SubgraphCapability.ERROR_CHECKING}
        )
        
        decision2 = self.router.route(context2)
        
        assert decision2.selected_subgraph is not None
        assert decision2.selected_subgraph.metadata.name == "error_checker"


class TestOrchestratorIntegration:
    """Integration tests for orchestrator."""
    
    def setup_method(self):
        """Setup test orchestrator."""
        # Create a fresh registry for each test
        self.registry = SubgraphRegistry()
        
        # Register subgraphs
        codegen = CodeGenerationSubgraph(name="codegen", auto_register=False)
        codegen.register(self.registry)
        
        error_checker = ErrorCheckingSubgraph(name="error_checker", auto_register=False)
        error_checker.register(self.registry)
    
    @pytest.mark.asyncio
    async def test_orchestrator_single_task(self):
        """Test orchestrator with a single task."""
        tasks = [
            {
                "type": "generate_code",
                "required_capabilities": [SubgraphCapability.CODE_GENERATION.value],
                "input": {
                    "requirements": "Create a Calculator class",
                    "language": "java"
                }
            }
        ]
        
        orchestrator, initial_state = create_orchestrator(
            workflow_id="test_workflow",
            tasks=tasks
        )
        
        # Override router to use our test registry
        orchestrator.router.registry = self.registry
        orchestrator.registry = self.registry
        
        graph = orchestrator.build_graph()
        compiled_graph = graph.compile()
        
        result_dict = await compiled_graph.ainvoke(initial_state)
        
        assert result_dict["status"].value in ["completed", "failed"]
        assert len(result_dict["completed_tasks"]) + len(result_dict["failed_tasks"]) == 1
    
    @pytest.mark.asyncio
    async def test_orchestrator_multiple_tasks(self):
        """Test orchestrator with multiple tasks."""
        tasks = [
            {
                "type": "generate_code",
                "required_capabilities": [SubgraphCapability.CODE_GENERATION.value],
                "input": {"requirements": "Create class A"}
            },
            {
                "type": "check_errors",
                "required_capabilities": [SubgraphCapability.ERROR_CHECKING.value],
                "input": {"code": "public class A { }"}
            }
        ]
        
        orchestrator, initial_state = create_orchestrator(
            workflow_id="multi_task_workflow",
            tasks=tasks
        )
        
        # Override router to use our test registry
        orchestrator.router.registry = self.registry
        orchestrator.registry = self.registry
        
        graph = orchestrator.build_graph()
        compiled_graph = graph.compile()
        
        result_dict = await compiled_graph.ainvoke(initial_state)
        
        assert len(result_dict["completed_tasks"]) + len(result_dict["failed_tasks"]) == 2


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test a complete workflow from registration to execution."""
        # 1. Create registry
        registry = SubgraphRegistry()
        
        # 2. Register subgraphs
        codegen = CodeGenerationSubgraph(
            name="codegen",
            programming_languages={"java", "python"},
            auto_register=False
        )
        codegen.register(registry)
        
        error_checker = ErrorCheckingSubgraph(
            name="error_checker",
            auto_register=False
        )
        error_checker.register(registry)
        
        # 3. Create router
        router = RouterAgent(registry=registry)
        
        # 4. Create orchestrator
        tasks = [
            {
                "type": "generate",
                "required_capabilities": [SubgraphCapability.CODE_GENERATION.value],
                "tags": ["java"],
                "input": {
                    "requirements": "Create a simple class",
                    "language": "java"
                }
            },
            {
                "type": "validate",
                "required_capabilities": [SubgraphCapability.ERROR_CHECKING.value],
                "input": {
                    "code": "public class Simple { }"
                }
            }
        ]
        
        orchestrator = MainOrchestrator(
            workflow_id="end_to_end_test",
            router=router
        )
        orchestrator.registry = registry
        
        initial_state = OrchestratorState(
            workflow_id="end_to_end_test",
            task_queue=tasks
        )
        
        # 5. Execute workflow
        graph = orchestrator.build_graph()
        compiled_graph = graph.compile()
        
        result_dict = await compiled_graph.ainvoke(initial_state)
        
        # 6. Verify results
        assert result_dict["workflow_id"] == "end_to_end_test"
        assert result_dict["status"].value in ["completed", "failed"]
        
        # 7. Check stats
        stats = orchestrator.get_execution_stats()
        assert stats["workflow_id"] == "end_to_end_test"
        assert "router_stats" in stats
        assert "registry_stats" in stats
