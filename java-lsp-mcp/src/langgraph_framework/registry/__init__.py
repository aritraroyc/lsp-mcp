"""
Subgraph Registry System

Provides dynamic registration and discovery of subgraphs with capability-based matching.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum
import threading
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SubgraphCapability(Enum):
    """Standard subgraph capabilities."""
    CODE_GENERATION = "code_generation"
    ERROR_CHECKING = "error_checking"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"


@dataclass
class SubgraphMetadata:
    """
    Metadata describing a subgraph's capabilities and requirements.
    
    Attributes:
        name: Unique identifier for the subgraph
        description: Human-readable description
        capabilities: Set of capabilities this subgraph provides
        input_schema: Expected input data structure
        output_schema: Expected output data structure
        tags: Additional categorization tags
        version: Subgraph version
        priority: Priority level (higher = preferred)
        max_concurrent: Maximum concurrent executions (0 = unlimited)
        timeout_seconds: Maximum execution time
        endpoint: Optional remote endpoint for A2A communication
    """
    name: str
    description: str
    capabilities: Set[SubgraphCapability]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    version: str = "1.0.0"
    priority: int = 0
    max_concurrent: int = 0
    timeout_seconds: int = 300
    endpoint: Optional[str] = None
    
    def matches_capability(self, capability: SubgraphCapability) -> bool:
        """Check if this subgraph supports a given capability."""
        return capability in self.capabilities
    
    def matches_tags(self, tags: Set[str]) -> bool:
        """Check if this subgraph matches all given tags."""
        return tags.issubset(self.tags)
    
    def score_match(self, required_capabilities: Set[SubgraphCapability], 
                    context_tags: Optional[Set[str]] = None) -> float:
        """
        Calculate match score for this subgraph against requirements.
        
        Args:
            required_capabilities: Required capabilities
            context_tags: Optional context tags for weighting
            
        Returns:
            Score from 0.0 to 1.0, where 1.0 is perfect match
        """
        if not required_capabilities:
            return 0.0
            
        # Check if all required capabilities are met
        if not required_capabilities.issubset(self.capabilities):
            return 0.0
        
        # Base score: 0.5 for meeting requirements
        base_score = 0.5
        
        # Bonus for tag matches
        tag_score = 0.0
        if context_tags:
            matching_tags = self.tags.intersection(context_tags)
            tag_score = len(matching_tags) / max(len(context_tags), 1) * 0.2
        
        # Priority bonus (normalized to 0-0.3)
        priority_score = min(self.priority / 100, 0.3)
        
        # Combined score
        total_score = min(base_score + tag_score + priority_score, 1.0)
        
        return total_score


@dataclass
class SubgraphRegistration:
    """
    Complete registration entry for a subgraph.
    
    Attributes:
        metadata: Subgraph metadata
        graph_builder: Callable that returns the compiled graph
        registered_at: Timestamp of registration
        active_executions: Current number of active executions
    """
    metadata: SubgraphMetadata
    graph_builder: Callable
    registered_at: datetime = field(default_factory=datetime.now)
    active_executions: int = 0
    
    def can_execute(self) -> bool:
        """Check if subgraph can accept new execution."""
        if self.metadata.max_concurrent == 0:
            return True
        return self.active_executions < self.metadata.max_concurrent


class SubgraphRegistry:
    """
    Thread-safe registry for managing subgraph registrations.
    
    Supports dynamic registration/deregistration and capability-based discovery.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._lock = threading.RLock()
        self._subgraphs: Dict[str, SubgraphRegistration] = {}
        self._capability_index: Dict[SubgraphCapability, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        logger.info("SubgraphRegistry initialized")
    
    def register(self, metadata: SubgraphMetadata, graph_builder: Callable) -> None:
        """
        Register a new subgraph.
        
        Args:
            metadata: Subgraph metadata
            graph_builder: Callable that returns the compiled graph
            
        Raises:
            ValueError: If subgraph name already registered
        """
        with self._lock:
            if metadata.name in self._subgraphs:
                raise ValueError(f"Subgraph '{metadata.name}' already registered")
            
            registration = SubgraphRegistration(
                metadata=metadata,
                graph_builder=graph_builder
            )
            
            self._subgraphs[metadata.name] = registration
            
            # Update capability index
            for capability in metadata.capabilities:
                if capability not in self._capability_index:
                    self._capability_index[capability] = set()
                self._capability_index[capability].add(metadata.name)
            
            # Update tag index
            for tag in metadata.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(metadata.name)
            
            logger.info(f"Registered subgraph '{metadata.name}' with capabilities: {metadata.capabilities}")
    
    def deregister(self, name: str) -> bool:
        """
        Deregister a subgraph.
        
        Args:
            name: Subgraph name to deregister
            
        Returns:
            True if deregistered, False if not found
        """
        with self._lock:
            if name not in self._subgraphs:
                return False
            
            registration = self._subgraphs[name]
            
            # Remove from capability index
            for capability in registration.metadata.capabilities:
                if capability in self._capability_index:
                    self._capability_index[capability].discard(name)
                    if not self._capability_index[capability]:
                        del self._capability_index[capability]
            
            # Remove from tag index
            for tag in registration.metadata.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(name)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]
            
            del self._subgraphs[name]
            
            logger.info(f"Deregistered subgraph '{name}'")
            return True
    
    def get(self, name: str) -> Optional[SubgraphRegistration]:
        """
        Get a specific subgraph registration.
        
        Args:
            name: Subgraph name
            
        Returns:
            SubgraphRegistration if found, None otherwise
        """
        with self._lock:
            return self._subgraphs.get(name)
    
    def find_by_capability(self, capability: SubgraphCapability) -> List[SubgraphRegistration]:
        """
        Find all subgraphs supporting a capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of matching subgraph registrations
        """
        with self._lock:
            names = self._capability_index.get(capability, set())
            return [self._subgraphs[name] for name in names if name in self._subgraphs]
    
    def find_by_tags(self, tags: Set[str]) -> List[SubgraphRegistration]:
        """
        Find all subgraphs matching given tags.
        
        Args:
            tags: Required tags
            
        Returns:
            List of matching subgraph registrations
        """
        with self._lock:
            if not tags:
                return []
            
            # Find intersection of subgraphs matching all tags
            matching_names = None
            for tag in tags:
                tag_names = self._tag_index.get(tag, set())
                if matching_names is None:
                    matching_names = tag_names.copy()
                else:
                    matching_names = matching_names.intersection(tag_names)
            
            if matching_names is None:
                return []
            
            return [self._subgraphs[name] for name in matching_names if name in self._subgraphs]
    
    def find_best_match(self, 
                        required_capabilities: Set[SubgraphCapability],
                        context_tags: Optional[Set[str]] = None,
                        exclude_names: Optional[Set[str]] = None) -> Optional[SubgraphRegistration]:
        """
        Find the best matching subgraph for given requirements.
        
        Args:
            required_capabilities: Required capabilities
            context_tags: Optional context tags for scoring
            exclude_names: Optional set of subgraph names to exclude
            
        Returns:
            Best matching SubgraphRegistration or None if no match
        """
        with self._lock:
            exclude_names = exclude_names or set()
            
            # Find candidates that can execute and aren't excluded
            candidates = [
                reg for name, reg in self._subgraphs.items()
                if name not in exclude_names and reg.can_execute()
            ]
            
            if not candidates:
                return None
            
            # Score each candidate
            scored_candidates = [
                (reg, reg.metadata.score_match(required_capabilities, context_tags))
                for reg in candidates
            ]
            
            # Filter out zero-score matches
            valid_candidates = [(reg, score) for reg, score in scored_candidates if score > 0]
            
            if not valid_candidates:
                return None
            
            # Sort by score (descending), then by priority (descending) for tie-breaking
            valid_candidates.sort(key=lambda x: (x[1], x[0].metadata.priority), reverse=True)
            
            return valid_candidates[0][0]
    
    def list_all(self) -> List[SubgraphRegistration]:
        """
        Get all registered subgraphs.
        
        Returns:
            List of all subgraph registrations
        """
        with self._lock:
            return list(self._subgraphs.values())
    
    def increment_active(self, name: str) -> bool:
        """
        Increment active execution counter.
        
        Args:
            name: Subgraph name
            
        Returns:
            True if incremented, False if not found or limit reached
        """
        with self._lock:
            if name not in self._subgraphs:
                return False
            
            registration = self._subgraphs[name]
            if not registration.can_execute():
                return False
            
            registration.active_executions += 1
            return True
    
    def decrement_active(self, name: str) -> bool:
        """
        Decrement active execution counter.
        
        Args:
            name: Subgraph name
            
        Returns:
            True if decremented, False if not found
        """
        with self._lock:
            if name not in self._subgraphs:
                return False
            
            registration = self._subgraphs[name]
            if registration.active_executions > 0:
                registration.active_executions -= 1
            
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            return {
                "total_subgraphs": len(self._subgraphs),
                "capabilities": {
                    cap.value: len(names) 
                    for cap, names in self._capability_index.items()
                },
                "total_active_executions": sum(
                    reg.active_executions for reg in self._subgraphs.values()
                ),
                "subgraphs": [
                    {
                        "name": reg.metadata.name,
                        "capabilities": [cap.value for cap in reg.metadata.capabilities],
                        "active_executions": reg.active_executions,
                        "can_execute": reg.can_execute()
                    }
                    for reg in self._subgraphs.values()
                ]
            }


# Global registry instance
_global_registry: Optional[SubgraphRegistry] = None
_registry_lock = threading.Lock()


def get_global_registry() -> SubgraphRegistry:
    """
    Get or create the global subgraph registry instance.
    
    Returns:
        Global SubgraphRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = SubgraphRegistry()
    
    return _global_registry
