"""
Router Agent Logic

Implements intelligent routing of tasks to appropriate subgraphs based on
capabilities, context, and scoring mechanisms.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..registry import (
    SubgraphRegistry,
    SubgraphCapability,
    SubgraphRegistration,
    get_global_registry
)

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Routing strategies for subgraph selection."""
    BEST_MATCH = "best_match"  # Select highest scoring subgraph
    ROUND_ROBIN = "round_robin"  # Distribute load evenly
    LEAST_LOADED = "least_loaded"  # Select subgraph with fewest active executions
    PRIORITY = "priority"  # Select by priority only


@dataclass
class RoutingContext:
    """
    Context information for routing decisions.
    
    Attributes:
        task_type: Type of task to be executed
        required_capabilities: Required subgraph capabilities
        context_tags: Optional tags for context-based scoring
        input_data: Input data for the task
        metadata: Additional routing metadata
        exclude_subgraphs: Subgraphs to exclude from selection
    """
    task_type: str
    required_capabilities: Set[SubgraphCapability]
    context_tags: Optional[Set[str]] = None
    input_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    exclude_subgraphs: Set[str] = field(default_factory=set)


@dataclass
class RoutingDecision:
    """
    Result of a routing decision.
    
    Attributes:
        selected_subgraph: Selected subgraph registration (None if no match)
        score: Match score for the selection
        reason: Human-readable explanation
        alternatives: List of alternative subgraphs considered
        context: Original routing context
    """
    selected_subgraph: Optional[SubgraphRegistration]
    score: float
    reason: str
    alternatives: List[tuple[SubgraphRegistration, float]] = field(default_factory=list)
    context: Optional[RoutingContext] = None


class RouterAgent:
    """
    Intelligent router for selecting appropriate subgraphs.
    
    Implements various routing strategies and maintains routing history
    for learning and optimization.
    """
    
    def __init__(self, 
                 registry: Optional[SubgraphRegistry] = None,
                 default_strategy: RoutingStrategy = RoutingStrategy.BEST_MATCH):
        """
        Initialize the router agent.
        
        Args:
            registry: SubgraphRegistry to use (uses global if None)
            default_strategy: Default routing strategy
        """
        self.registry = registry or get_global_registry()
        self.default_strategy = default_strategy
        self._routing_history: List[RoutingDecision] = []
        self._round_robin_index = 0
        logger.info(f"RouterAgent initialized with strategy: {default_strategy.value}")
    
    def route(self, 
              context: RoutingContext,
              strategy: Optional[RoutingStrategy] = None) -> RoutingDecision:
        """
        Route a task to an appropriate subgraph.
        
        Args:
            context: Routing context with task requirements
            strategy: Optional routing strategy (uses default if None)
            
        Returns:
            RoutingDecision with selected subgraph
        """
        strategy = strategy or self.default_strategy
        
        logger.info(f"Routing task '{context.task_type}' with strategy '{strategy.value}'")
        logger.debug(f"Required capabilities: {context.required_capabilities}")
        
        decision = self._route_by_strategy(context, strategy)
        decision.context = context
        
        # Record in history
        self._routing_history.append(decision)
        
        if decision.selected_subgraph:
            logger.info(f"Selected subgraph: {decision.selected_subgraph.metadata.name} (score: {decision.score:.3f})")
        else:
            logger.warning(f"No suitable subgraph found for task '{context.task_type}'")
        
        return decision
    
    def _route_by_strategy(self, 
                           context: RoutingContext,
                           strategy: RoutingStrategy) -> RoutingDecision:
        """
        Internal routing based on strategy.
        
        Args:
            context: Routing context
            strategy: Routing strategy to use
            
        Returns:
            RoutingDecision
        """
        if strategy == RoutingStrategy.BEST_MATCH:
            return self._route_best_match(context)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(context)
        elif strategy == RoutingStrategy.LEAST_LOADED:
            return self._route_least_loaded(context)
        elif strategy == RoutingStrategy.PRIORITY:
            return self._route_priority(context)
        else:
            return RoutingDecision(
                selected_subgraph=None,
                score=0.0,
                reason=f"Unknown routing strategy: {strategy}"
            )
    
    def _route_best_match(self, context: RoutingContext) -> RoutingDecision:
        """Route using best match scoring."""
        subgraph = self.registry.find_best_match(
            required_capabilities=context.required_capabilities,
            context_tags=context.context_tags,
            exclude_names=context.exclude_subgraphs
        )
        
        if subgraph is None:
            return RoutingDecision(
                selected_subgraph=None,
                score=0.0,
                reason="No subgraph found matching required capabilities"
            )
        
        score = subgraph.metadata.score_match(
            context.required_capabilities,
            context.context_tags
        )
        
        # Get alternatives
        alternatives = self._get_scored_alternatives(context, exclude={subgraph.metadata.name})
        
        return RoutingDecision(
            selected_subgraph=subgraph,
            score=score,
            reason=f"Best match based on capability and context scoring",
            alternatives=alternatives[:5]  # Top 5 alternatives
        )
    
    def _route_round_robin(self, context: RoutingContext) -> RoutingDecision:
        """Route using round-robin distribution."""
        # Get all capable subgraphs
        candidates = self._get_capable_subgraphs(context)
        
        if not candidates:
            return RoutingDecision(
                selected_subgraph=None,
                score=0.0,
                reason="No capable subgraphs available"
            )
        
        # Select using round-robin
        selected = candidates[self._round_robin_index % len(candidates)]
        self._round_robin_index += 1
        
        return RoutingDecision(
            selected_subgraph=selected,
            score=0.5,  # Neutral score for round-robin
            reason=f"Round-robin selection (index: {self._round_robin_index - 1})",
            alternatives=[(c, 0.5) for c in candidates if c != selected]
        )
    
    def _route_least_loaded(self, context: RoutingContext) -> RoutingDecision:
        """Route to least loaded capable subgraph."""
        candidates = self._get_capable_subgraphs(context)
        
        if not candidates:
            return RoutingDecision(
                selected_subgraph=None,
                score=0.0,
                reason="No capable subgraphs available"
            )
        
        # Sort by active executions (ascending)
        candidates_sorted = sorted(
            candidates,
            key=lambda x: (x.active_executions, -x.metadata.priority)
        )
        
        selected = candidates_sorted[0]
        load_score = 1.0 - (selected.active_executions / 
                           max(selected.metadata.max_concurrent, 100))
        
        return RoutingDecision(
            selected_subgraph=selected,
            score=load_score,
            reason=f"Least loaded ({selected.active_executions} active executions)",
            alternatives=[(c, 1.0 - (c.active_executions / max(c.metadata.max_concurrent, 100))) 
                         for c in candidates_sorted[1:6]]
        )
    
    def _route_priority(self, context: RoutingContext) -> RoutingDecision:
        """Route based on priority only."""
        candidates = self._get_capable_subgraphs(context)
        
        if not candidates:
            return RoutingDecision(
                selected_subgraph=None,
                score=0.0,
                reason="No capable subgraphs available"
            )
        
        # Sort by priority (descending)
        candidates_sorted = sorted(
            candidates,
            key=lambda x: x.metadata.priority,
            reverse=True
        )
        
        selected = candidates_sorted[0]
        priority_score = selected.metadata.priority / 100.0
        
        return RoutingDecision(
            selected_subgraph=selected,
            score=priority_score,
            reason=f"Highest priority ({selected.metadata.priority})",
            alternatives=[(c, c.metadata.priority / 100.0) for c in candidates_sorted[1:6]]
        )
    
    def _get_capable_subgraphs(self, context: RoutingContext) -> List[SubgraphRegistration]:
        """
        Get all subgraphs capable of handling the context.
        
        Args:
            context: Routing context
            
        Returns:
            List of capable subgraph registrations
        """
        all_subgraphs = self.registry.list_all()
        
        capable = [
            reg for reg in all_subgraphs
            if (reg.metadata.name not in context.exclude_subgraphs and
                context.required_capabilities.issubset(reg.metadata.capabilities) and
                reg.can_execute())
        ]
        
        return capable
    
    def _get_scored_alternatives(self,
                                  context: RoutingContext,
                                  exclude: Optional[Set[str]] = None) -> List[tuple[SubgraphRegistration, float]]:
        """
        Get scored alternatives for a routing context.
        
        Args:
            context: Routing context
            exclude: Optional set of subgraph names to exclude
            
        Returns:
            List of (subgraph, score) tuples sorted by score descending
        """
        exclude = exclude or set()
        exclude = exclude.union(context.exclude_subgraphs)
        
        candidates = [
            reg for reg in self.registry.list_all()
            if (reg.metadata.name not in exclude and
                reg.can_execute())
        ]
        
        scored = [
            (reg, reg.metadata.score_match(context.required_capabilities, context.context_tags))
            for reg in candidates
        ]
        
        # Filter out zero scores and sort
        valid_scored = [(reg, score) for reg, score in scored if score > 0]
        valid_scored.sort(key=lambda x: x[1], reverse=True)
        
        return valid_scored
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.
        
        Returns:
            Dictionary with routing statistics
        """
        total_routes = len(self._routing_history)
        successful_routes = sum(1 for d in self._routing_history if d.selected_subgraph is not None)
        
        # Count routes per subgraph
        subgraph_counts: Dict[str, int] = {}
        for decision in self._routing_history:
            if decision.selected_subgraph:
                name = decision.selected_subgraph.metadata.name
                subgraph_counts[name] = subgraph_counts.get(name, 0) + 1
        
        # Average scores
        scores = [d.score for d in self._routing_history if d.selected_subgraph]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "total_routing_decisions": total_routes,
            "successful_routes": successful_routes,
            "failed_routes": total_routes - successful_routes,
            "success_rate": successful_routes / total_routes if total_routes > 0 else 0.0,
            "average_score": avg_score,
            "routes_per_subgraph": subgraph_counts,
            "current_round_robin_index": self._round_robin_index
        }
    
    def clear_history(self) -> None:
        """Clear routing history."""
        self._routing_history.clear()
        logger.info("Routing history cleared")


class AdaptiveRouter(RouterAgent):
    """
    Advanced router that adapts strategy based on context and performance.
    
    Learns from routing history to improve future decisions.
    """
    
    def __init__(self, 
                 registry: Optional[SubgraphRegistry] = None,
                 learning_rate: float = 0.1):
        """
        Initialize adaptive router.
        
        Args:
            registry: SubgraphRegistry to use
            learning_rate: Rate at which to adapt routing decisions (0.0-1.0)
        """
        super().__init__(registry, RoutingStrategy.BEST_MATCH)
        self.learning_rate = max(0.0, min(1.0, learning_rate))
        self._performance_scores: Dict[str, List[float]] = {}
        logger.info(f"AdaptiveRouter initialized with learning_rate: {learning_rate}")
    
    def record_performance(self, subgraph_name: str, performance_score: float) -> None:
        """
        Record performance score for a subgraph execution.
        
        Args:
            subgraph_name: Name of the subgraph
            performance_score: Performance score (0.0-1.0, higher is better)
        """
        if subgraph_name not in self._performance_scores:
            self._performance_scores[subgraph_name] = []
        
        self._performance_scores[subgraph_name].append(performance_score)
        
        # Keep last 100 scores
        if len(self._performance_scores[subgraph_name]) > 100:
            self._performance_scores[subgraph_name] = self._performance_scores[subgraph_name][-100:]
        
        logger.debug(f"Recorded performance {performance_score:.3f} for {subgraph_name}")
    
    def get_average_performance(self, subgraph_name: str) -> float:
        """
        Get average performance score for a subgraph.
        
        Args:
            subgraph_name: Name of the subgraph
            
        Returns:
            Average performance score or 0.5 if no data
        """
        scores = self._performance_scores.get(subgraph_name, [])
        return sum(scores) / len(scores) if scores else 0.5
    
    def route(self, 
              context: RoutingContext,
              strategy: Optional[RoutingStrategy] = None) -> RoutingDecision:
        """
        Route with performance-based adaptation.
        
        Args:
            context: Routing context
            strategy: Optional routing strategy
            
        Returns:
            RoutingDecision with performance-adjusted scoring
        """
        strategy = strategy or self.default_strategy
        
        # For adaptive routing, use best_match with performance adjustment
        if strategy == RoutingStrategy.BEST_MATCH:
            # Get all capable subgraphs and score them with performance
            candidates = self._get_capable_subgraphs(context)
            
            if not candidates:
                return RoutingDecision(
                    selected_subgraph=None,
                    score=0.0,
                    reason="No capable subgraphs available"
                )
            
            # Score each with base score + performance adjustment
            scored = []
            for reg in candidates:
                base_score = reg.metadata.score_match(
                    context.required_capabilities,
                    context.context_tags
                )
                if base_score > 0:
                    performance = self.get_average_performance(reg.metadata.name)
                    adjusted_score = (base_score * (1 - self.learning_rate) + 
                                    performance * self.learning_rate)
                    scored.append((reg, adjusted_score, base_score, performance))
            
            if not scored:
                return RoutingDecision(
                    selected_subgraph=None,
                    score=0.0,
                    reason="No matching subgraphs"
                )
            
            # Sort by adjusted score, then priority
            scored.sort(key=lambda x: (x[1], x[0].metadata.priority), reverse=True)
            
            selected, final_score, base_score, performance = scored[0]
            
            decision = RoutingDecision(
                selected_subgraph=selected,
                score=final_score,
                reason=f"Adaptive best match (base: {base_score:.3f}, perf: {performance:.3f})",
                alternatives=[(r, s) for r, s, _, _ in scored[1:6]]
            )
            
            # Record in history
            self._routing_history.append(decision)
            
            return decision
        else:
            # For other strategies, use base routing
            return super().route(context, strategy)
