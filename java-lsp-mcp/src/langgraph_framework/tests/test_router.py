"""
Unit tests for Router Agent
"""

import pytest
from src.langgraph_framework.registry import (
    SubgraphRegistry,
    SubgraphMetadata,
    SubgraphCapability
)
from src.langgraph_framework.router import (
    RouterAgent,
    RoutingContext,
    RoutingStrategy,
    AdaptiveRouter
)


class TestRoutingContext:
    """Tests for RoutingContext."""
    
    def test_context_creation(self):
        """Test creating routing context."""
        context = RoutingContext(
            task_type="code_generation",
            required_capabilities={SubgraphCapability.CODE_GENERATION},
            context_tags={"java"}
        )
        
        assert context.task_type == "code_generation"
        assert SubgraphCapability.CODE_GENERATION in context.required_capabilities


class TestRouterAgent:
    """Tests for RouterAgent."""
    
    def setup_method(self):
        """Setup test router and registry."""
        self.registry = SubgraphRegistry()
        self.router = RouterAgent(registry=self.registry)
        
        # Register test subgraphs
        self._register_test_subgraphs()
    
    def _register_test_subgraphs(self):
        """Register test subgraphs."""
        metadata1 = SubgraphMetadata(
            name="basic_codegen",
            description="Basic code generator",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags={"java"},
            priority=30
        )
        
        metadata2 = SubgraphMetadata(
            name="advanced_codegen",
            description="Advanced code generator",
            capabilities={SubgraphCapability.CODE_GENERATION, SubgraphCapability.ERROR_CHECKING},
            tags={"java", "python"},
            priority=70
        )
        
        metadata3 = SubgraphMetadata(
            name="error_checker",
            description="Error checker",
            capabilities={SubgraphCapability.ERROR_CHECKING},
            tags={"java"},
            priority=50
        )
        
        self.registry.register(metadata1, lambda: "g1")
        self.registry.register(metadata2, lambda: "g2")
        self.registry.register(metadata3, lambda: "g3")
    
    def test_route_best_match(self):
        """Test routing with best match strategy."""
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION},
            context_tags={"java"}
        )
        
        decision = self.router.route(context, RoutingStrategy.BEST_MATCH)
        
        assert decision.selected_subgraph is not None
        assert decision.score > 0
        # Should select advanced_codegen due to higher priority
        assert decision.selected_subgraph.metadata.name == "advanced_codegen"
    
    def test_route_no_match(self):
        """Test routing when no subgraph matches."""
        context = RoutingContext(
            task_type="refactoring",
            required_capabilities={SubgraphCapability.REFACTORING}
        )
        
        decision = self.router.route(context, RoutingStrategy.BEST_MATCH)
        
        assert decision.selected_subgraph is None
        assert decision.score == 0.0
    
    def test_route_with_exclusions(self):
        """Test routing with excluded subgraphs."""
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION},
            exclude_subgraphs={"advanced_codegen"}
        )
        
        decision = self.router.route(context, RoutingStrategy.BEST_MATCH)
        
        assert decision.selected_subgraph is not None
        assert decision.selected_subgraph.metadata.name == "basic_codegen"
    
    def test_route_round_robin(self):
        """Test round-robin routing."""
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        # Route multiple times
        names = []
        for _ in range(4):
            decision = self.router.route(context, RoutingStrategy.ROUND_ROBIN)
            names.append(decision.selected_subgraph.metadata.name)
        
        # Should alternate between the two code generators
        assert len(set(names)) == 2
        assert "basic_codegen" in names
        assert "advanced_codegen" in names
    
    def test_route_least_loaded(self):
        """Test least loaded routing."""
        # Simulate load on advanced_codegen
        self.registry.increment_active("advanced_codegen")
        self.registry.increment_active("advanced_codegen")
        
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        decision = self.router.route(context, RoutingStrategy.LEAST_LOADED)
        
        assert decision.selected_subgraph is not None
        # Should select basic_codegen as it has fewer active executions
        assert decision.selected_subgraph.metadata.name == "basic_codegen"
    
    def test_route_priority(self):
        """Test priority-based routing."""
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        decision = self.router.route(context, RoutingStrategy.PRIORITY)
        
        assert decision.selected_subgraph is not None
        # Should select advanced_codegen due to higher priority (70 vs 30)
        assert decision.selected_subgraph.metadata.name == "advanced_codegen"
    
    def test_get_routing_stats(self):
        """Test getting routing statistics."""
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        # Perform some routes
        for _ in range(5):
            self.router.route(context)
        
        stats = self.router.get_routing_stats()
        
        assert stats["total_routing_decisions"] == 5
        assert stats["successful_routes"] == 5
        assert stats["failed_routes"] == 0


class TestAdaptiveRouter:
    """Tests for AdaptiveRouter."""
    
    def setup_method(self):
        """Setup adaptive router."""
        self.registry = SubgraphRegistry()
        self.router = AdaptiveRouter(registry=self.registry, learning_rate=0.5)
        
        # Register test subgraphs
        metadata1 = SubgraphMetadata(
            name="subgraph_a",
            description="Subgraph A",
            capabilities={SubgraphCapability.CODE_GENERATION},
            priority=50
        )
        
        metadata2 = SubgraphMetadata(
            name="subgraph_b",
            description="Subgraph B",
            capabilities={SubgraphCapability.CODE_GENERATION},
            priority=50
        )
        
        self.registry.register(metadata1, lambda: "g1")
        self.registry.register(metadata2, lambda: "g2")
    
    def test_record_performance(self):
        """Test recording performance scores."""
        self.router.record_performance("subgraph_a", 0.9)
        self.router.record_performance("subgraph_a", 0.8)
        
        avg = self.router.get_average_performance("subgraph_a")
        assert abs(avg - 0.85) < 0.001  # Use approximate equality for float
    
    def test_adaptive_routing_with_performance(self):
        """Test that routing adapts based on performance."""
        # Record poor performance for subgraph_a
        for _ in range(5):
            self.router.record_performance("subgraph_a", 0.2)
        
        # Record good performance for subgraph_b
        for _ in range(5):
            self.router.record_performance("subgraph_b", 0.9)
        
        context = RoutingContext(
            task_type="code_gen",
            required_capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        # Route multiple times
        selections = []
        for _ in range(10):
            decision = self.router.route(context)
            selections.append(decision.selected_subgraph.metadata.name)
        
        # Should prefer subgraph_b due to better performance
        assert selections.count("subgraph_b") > selections.count("subgraph_a")
    
    def test_get_average_performance_no_data(self):
        """Test getting average performance with no data."""
        avg = self.router.get_average_performance("nonexistent")
        assert avg == 0.5  # Default value
