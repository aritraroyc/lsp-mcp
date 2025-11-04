"""
Unit tests for Subgraph Registry System
"""

import pytest
from src.langgraph_framework.registry import (
    SubgraphRegistry,
    SubgraphMetadata,
    SubgraphCapability,
    SubgraphRegistration,
    get_global_registry
)


class TestSubgraphMetadata:
    """Tests for SubgraphMetadata."""
    
    def test_metadata_creation(self):
        """Test creating metadata."""
        metadata = SubgraphMetadata(
            name="test_subgraph",
            description="Test subgraph",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        assert metadata.name == "test_subgraph"
        assert SubgraphCapability.CODE_GENERATION in metadata.capabilities
    
    def test_matches_capability(self):
        """Test capability matching."""
        metadata = SubgraphMetadata(
            name="test",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION, SubgraphCapability.ERROR_CHECKING}
        )
        
        assert metadata.matches_capability(SubgraphCapability.CODE_GENERATION)
        assert not metadata.matches_capability(SubgraphCapability.REFACTORING)
    
    def test_matches_tags(self):
        """Test tag matching."""
        metadata = SubgraphMetadata(
            name="test",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags={"java", "python", "production"}
        )
        
        assert metadata.matches_tags({"java"})
        assert metadata.matches_tags({"java", "python"})
        assert not metadata.matches_tags({"java", "rust"})
    
    def test_score_match_perfect(self):
        """Test scoring with perfect match."""
        metadata = SubgraphMetadata(
            name="test",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags={"java"},
            priority=50
        )
        
        score = metadata.score_match(
            {SubgraphCapability.CODE_GENERATION},
            {"java"}
        )
        
        assert score > 0.5  # Should have good score
    
    def test_score_match_no_capability(self):
        """Test scoring with missing capability."""
        metadata = SubgraphMetadata(
            name="test",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        score = metadata.score_match(
            {SubgraphCapability.REFACTORING}
        )
        
        assert score == 0.0  # Should be zero if capability missing


class TestSubgraphRegistry:
    """Tests for SubgraphRegistry."""
    
    def setup_method(self):
        """Setup test registry."""
        self.registry = SubgraphRegistry()
    
    def test_register_subgraph(self):
        """Test registering a subgraph."""
        metadata = SubgraphMetadata(
            name="test_graph",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        def builder():
            return "graph"
        
        self.registry.register(metadata, builder)
        
        registration = self.registry.get("test_graph")
        assert registration is not None
        assert registration.metadata.name == "test_graph"
    
    def test_register_duplicate_fails(self):
        """Test that duplicate registration fails."""
        metadata = SubgraphMetadata(
            name="duplicate",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        self.registry.register(metadata, lambda: "graph")
        
        with pytest.raises(ValueError):
            self.registry.register(metadata, lambda: "graph2")
    
    def test_deregister_subgraph(self):
        """Test deregistering a subgraph."""
        metadata = SubgraphMetadata(
            name="temp_graph",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        self.registry.register(metadata, lambda: "graph")
        assert self.registry.get("temp_graph") is not None
        
        result = self.registry.deregister("temp_graph")
        assert result is True
        assert self.registry.get("temp_graph") is None
    
    def test_find_by_capability(self):
        """Test finding subgraphs by capability."""
        # Register multiple subgraphs
        metadata1 = SubgraphMetadata(
            name="graph1",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        metadata2 = SubgraphMetadata(
            name="graph2",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION, SubgraphCapability.ERROR_CHECKING}
        )
        
        metadata3 = SubgraphMetadata(
            name="graph3",
            description="Test",
            capabilities={SubgraphCapability.REFACTORING}
        )
        
        self.registry.register(metadata1, lambda: "g1")
        self.registry.register(metadata2, lambda: "g2")
        self.registry.register(metadata3, lambda: "g3")
        
        # Find by code generation
        results = self.registry.find_by_capability(SubgraphCapability.CODE_GENERATION)
        assert len(results) == 2
        names = {r.metadata.name for r in results}
        assert names == {"graph1", "graph2"}
    
    def test_find_by_tags(self):
        """Test finding subgraphs by tags."""
        metadata1 = SubgraphMetadata(
            name="java_graph",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags={"java", "production"}
        )
        
        metadata2 = SubgraphMetadata(
            name="python_graph",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags={"python", "production"}
        )
        
        self.registry.register(metadata1, lambda: "g1")
        self.registry.register(metadata2, lambda: "g2")
        
        # Find production graphs
        results = self.registry.find_by_tags({"production"})
        assert len(results) == 2
        
        # Find java graphs
        results = self.registry.find_by_tags({"java"})
        assert len(results) == 1
        assert results[0].metadata.name == "java_graph"
    
    def test_find_best_match(self):
        """Test finding best matching subgraph."""
        metadata1 = SubgraphMetadata(
            name="basic",
            description="Basic",
            capabilities={SubgraphCapability.CODE_GENERATION},
            priority=30
        )
        
        metadata2 = SubgraphMetadata(
            name="advanced",
            description="Advanced",
            capabilities={SubgraphCapability.CODE_GENERATION, SubgraphCapability.ERROR_CHECKING},
            priority=80
        )
        
        self.registry.register(metadata1, lambda: "g1")
        self.registry.register(metadata2, lambda: "g2")
        
        # Find best match for code generation
        result = self.registry.find_best_match(
            {SubgraphCapability.CODE_GENERATION}
        )
        
        assert result is not None
        # Should prefer higher priority when both match
        assert result.metadata.name == "advanced"
    
    def test_increment_decrement_active(self):
        """Test active execution counter."""
        metadata = SubgraphMetadata(
            name="counter_test",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION},
            max_concurrent=2
        )
        
        self.registry.register(metadata, lambda: "g")
        
        # Increment
        assert self.registry.increment_active("counter_test")
        assert self.registry.increment_active("counter_test")
        
        # Should fail at max
        assert not self.registry.increment_active("counter_test")
        
        # Decrement
        assert self.registry.decrement_active("counter_test")
        
        # Should succeed again
        assert self.registry.increment_active("counter_test")
    
    def test_get_stats(self):
        """Test getting registry statistics."""
        metadata = SubgraphMetadata(
            name="stats_test",
            description="Test",
            capabilities={SubgraphCapability.CODE_GENERATION}
        )
        
        self.registry.register(metadata, lambda: "g")
        
        stats = self.registry.get_stats()
        
        assert stats["total_subgraphs"] == 1
        assert SubgraphCapability.CODE_GENERATION.value in stats["capabilities"]


class TestGlobalRegistry:
    """Test global registry singleton."""
    
    def test_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        reg1 = get_global_registry()
        reg2 = get_global_registry()
        
        assert reg1 is reg2
