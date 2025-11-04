"""
Main Graph Orchestrator

Provides parent graph orchestration logic for managing state and subgraph
interactions with error detection and adaptive re-routing.
"""

from typing import Any, Dict, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from langgraph.graph import StateGraph, START, END

from ..registry import SubgraphCapability, get_global_registry
from ..router import RouterAgent, RoutingContext, RoutingStrategy, AdaptiveRouter
from ..subgraphs import SubgraphState, SubgraphStatus

logger = logging.getLogger(__name__)


class OrchestratorStatus(Enum):
    """Status of orchestrator execution."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class OrchestratorState:
    """
    State for the main orchestrator graph.
    
    Attributes:
        workflow_id: Unique identifier for this workflow
        current_task: Current task being executed
        task_queue: Queue of tasks to execute
        completed_tasks: List of completed tasks
        failed_tasks: List of failed tasks
        status: Current orchestrator status
        errors: List of errors encountered
        retry_count: Number of retries attempted
        max_retries: Maximum retry attempts
        context: Global workflow context
        subgraph_results: Results from subgraph executions
    """
    workflow_id: str = ""
    current_task: Optional[Dict[str, Any]] = None
    task_queue: List[Dict[str, Any]] = field(default_factory=list)
    completed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    failed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    status: OrchestratorStatus = OrchestratorStatus.IDLE
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    context: Dict[str, Any] = field(default_factory=dict)
    subgraph_results: Dict[str, Any] = field(default_factory=dict)


class MainOrchestrator:
    """
    Main graph orchestrator for managing workflow execution.
    
    Coordinates multiple subgraphs, handles errors, and provides
    adaptive re-routing capabilities.
    """
    
    def __init__(self,
                 workflow_id: str,
                 router: Optional[RouterAgent] = None,
                 use_adaptive_routing: bool = True,
                 max_retries: int = 3):
        """
        Initialize the orchestrator.
        
        Args:
            workflow_id: Unique identifier for this workflow
            router: Optional router agent (creates adaptive router if None)
            use_adaptive_routing: Whether to use adaptive routing
            max_retries: Maximum retry attempts for failed tasks
        """
        self.workflow_id = workflow_id
        self.max_retries = max_retries
        
        # Initialize router
        if router:
            self.router = router
        elif use_adaptive_routing:
            self.router = AdaptiveRouter()
        else:
            self.router = RouterAgent()
        
        self.registry = get_global_registry()
        self._execution_history: List[Dict[str, Any]] = []
        
        logger.info(f"MainOrchestrator initialized for workflow '{workflow_id}'")
    
    def build_graph(self) -> StateGraph:
        """
        Build the main orchestrator graph.
        
        Returns:
            StateGraph for orchestration
        """
        graph = StateGraph(OrchestratorState)
        
        # Add nodes
        graph.add_node("initialize", self._initialize)
        graph.add_node("get_next_task", self._get_next_task)
        graph.add_node("route_task", self._route_task)
        graph.add_node("execute_subgraph", self._execute_subgraph)
        graph.add_node("validate_result", self._validate_result)
        graph.add_node("handle_error", self._handle_error)
        graph.add_node("finalize", self._finalize)
        
        # Add edges
        graph.add_edge(START, "initialize")
        graph.add_edge("initialize", "get_next_task")
        
        # Conditional edge from get_next_task
        graph.add_conditional_edges(
            "get_next_task",
            self._should_continue_or_finalize,
            {
                "route": "route_task",
                "finalize": "finalize"
            }
        )
        
        graph.add_edge("route_task", "execute_subgraph")
        
        # Conditional edge from execute_subgraph
        graph.add_conditional_edges(
            "execute_subgraph",
            self._check_execution_result,
            {
                "validate": "validate_result",
                "error": "handle_error"
            }
        )
        
        # Conditional edge from validate_result
        graph.add_conditional_edges(
            "validate_result",
            self._check_validation,
            {
                "next": "get_next_task",
                "error": "handle_error"
            }
        )
        
        # Conditional edge from handle_error
        graph.add_conditional_edges(
            "handle_error",
            self._should_retry_or_fail,
            {
                "retry": "route_task",
                "next": "get_next_task",
                "fail": "finalize"
            }
        )
        
        graph.add_edge("finalize", END)
        
        return graph
    
    def _initialize(self, state: OrchestratorState) -> OrchestratorState:
        """Initialize workflow execution."""
        logger.info(f"Initializing workflow '{self.workflow_id}'")
        
        state.workflow_id = self.workflow_id
        state.status = OrchestratorStatus.RUNNING
        state.max_retries = self.max_retries
        
        return state
    
    def _get_next_task(self, state: OrchestratorState) -> OrchestratorState:
        """Get next task from queue."""
        if state.task_queue:
            state.current_task = state.task_queue.pop(0)
            state.retry_count = 0
            logger.info(f"Processing task: {state.current_task.get('type', 'unknown')}")
        else:
            state.current_task = None
            logger.info("No more tasks in queue")
        
        return state
    
    def _route_task(self, state: OrchestratorState) -> OrchestratorState:
        """Route task to appropriate subgraph."""
        if not state.current_task:
            logger.warning("No current task to route")
            return state
        
        task = state.current_task
        
        # Extract routing requirements
        required_capabilities = set(
            SubgraphCapability(cap) 
            for cap in task.get("required_capabilities", [])
        )
        
        context_tags = set(task.get("tags", []))
        
        # Create routing context
        routing_context = RoutingContext(
            task_type=task.get("type", "unknown"),
            required_capabilities=required_capabilities,
            context_tags=context_tags,
            input_data=task.get("input", {}),
            exclude_subgraphs=set(task.get("exclude_subgraphs", []))
        )
        
        # Route to subgraph
        decision = self.router.route(routing_context)
        
        if decision.selected_subgraph:
            state.context["selected_subgraph"] = decision.selected_subgraph.metadata.name
            state.context["routing_score"] = decision.score
            logger.info(f"Routed to subgraph '{decision.selected_subgraph.metadata.name}' (score: {decision.score:.3f})")
        else:
            state.context["selected_subgraph"] = None
            state.errors.append({
                "task": task.get("type"),
                "error": "No suitable subgraph found",
                "reason": decision.reason
            })
            logger.error(f"Failed to route task: {decision.reason}")
        
        return state
    
    async def _execute_subgraph(self, state: OrchestratorState) -> OrchestratorState:
        """Execute the selected subgraph."""
        subgraph_name = state.context.get("selected_subgraph")
        
        if not subgraph_name:
            state.status = OrchestratorStatus.FAILED
            return state
        
        # Get subgraph registration
        registration = self.registry.get(subgraph_name)
        if not registration:
            state.errors.append({
                "subgraph": subgraph_name,
                "error": "Subgraph not found in registry"
            })
            state.status = OrchestratorStatus.FAILED
            return state
        
        # Increment active counter
        self.registry.increment_active(subgraph_name)
        
        try:
            # Prepare subgraph input state
            subgraph_state = SubgraphState(
                subgraph_name=subgraph_name,
                input_data=state.current_task.get("input", {})
            )
            
            # Execute subgraph
            logger.info(f"Executing subgraph '{subgraph_name}'")
            start_time = datetime.now()
            
            graph = registration.graph_builder()
            result_dict = await graph.ainvoke(subgraph_state)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Store result (result is a dict from LangGraph)
            state.subgraph_results[subgraph_name] = {
                "output": result_dict.get("output_data", {}),
                "status": result_dict["status"].value if "status" in result_dict else "unknown",
                "execution_time": execution_time,
                "error": result_dict.get("error")
            }
            
            state.context["last_execution_time"] = execution_time
            
            # Record performance if using adaptive router
            if isinstance(self.router, AdaptiveRouter):
                performance_score = 1.0 if result_dict.get("status") == SubgraphStatus.COMPLETED else 0.0
                self.router.record_performance(subgraph_name, performance_score)
            
            logger.info(f"Subgraph '{subgraph_name}' completed in {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Subgraph '{subgraph_name}' failed: {e}")
            state.subgraph_results[subgraph_name] = {
                "output": {},
                "status": "failed",
                "error": str(e)
            }
            state.errors.append({
                "subgraph": subgraph_name,
                "error": str(e)
            })
            state.status = OrchestratorStatus.FAILED
            
        finally:
            # Decrement active counter
            self.registry.decrement_active(subgraph_name)
        
        return state
    
    def _validate_result(self, state: OrchestratorState) -> OrchestratorState:
        """Validate subgraph execution result."""
        subgraph_name = state.context.get("selected_subgraph")
        result = state.subgraph_results.get(subgraph_name, {})
        
        if result.get("status") == "completed":
            # Mark task as completed
            state.completed_tasks.append({
                "task": state.current_task,
                "result": result,
                "subgraph": subgraph_name
            })
            logger.info("Task validation successful")
            state.context["validation_passed"] = True
        else:
            # Validation failed
            state.context["validation_passed"] = False
            logger.warning("Task validation failed")
        
        return state
    
    def _handle_error(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors with adaptive re-routing."""
        logger.info(f"Handling error (retry {state.retry_count + 1}/{state.max_retries})")
        
        state.retry_count += 1
        
        if state.retry_count <= state.max_retries:
            # Try alternate routing
            failed_subgraph = state.context.get("selected_subgraph")
            if failed_subgraph:
                # Exclude failed subgraph from next routing attempt
                if "exclude_subgraphs" not in state.current_task:
                    state.current_task["exclude_subgraphs"] = []
                state.current_task["exclude_subgraphs"].append(failed_subgraph)
                
                logger.info(f"Attempting re-route, excluding '{failed_subgraph}'")
                state.status = OrchestratorStatus.RETRY
        else:
            # Max retries exceeded
            state.failed_tasks.append({
                "task": state.current_task,
                "errors": state.errors,
                "attempts": state.retry_count
            })
            logger.error(f"Task failed after {state.retry_count} attempts")
            state.status = OrchestratorStatus.FAILED
        
        return state
    
    def _finalize(self, state: OrchestratorState) -> OrchestratorState:
        """Finalize workflow execution."""
        logger.info(f"Finalizing workflow '{self.workflow_id}'")
        
        # Determine final status
        if state.failed_tasks and not state.completed_tasks:
            state.status = OrchestratorStatus.FAILED
        elif state.failed_tasks:
            state.status = OrchestratorStatus.COMPLETED  # Partial completion
        else:
            state.status = OrchestratorStatus.COMPLETED
        
        # Record execution history
        self._execution_history.append({
            "workflow_id": state.workflow_id,
            "status": state.status.value,
            "completed_tasks": len(state.completed_tasks),
            "failed_tasks": len(state.failed_tasks),
            "errors": state.errors
        })
        
        logger.info(f"Workflow completed: {len(state.completed_tasks)} succeeded, {len(state.failed_tasks)} failed")
        
        return state
    
    # Conditional edge functions
    
    def _should_continue_or_finalize(self, state: OrchestratorState) -> str:
        """Determine whether to continue processing or finalize."""
        if state.current_task:
            return "route"
        return "finalize"
    
    def _check_execution_result(self, state: OrchestratorState) -> str:
        """Check if subgraph execution was successful."""
        if state.status == OrchestratorStatus.FAILED:
            return "error"
        return "validate"
    
    def _check_validation(self, state: OrchestratorState) -> str:
        """Check validation result."""
        if state.context.get("validation_passed", False):
            return "next"
        return "error"
    
    def _should_retry_or_fail(self, state: OrchestratorState) -> str:
        """Determine whether to retry, continue, or fail."""
        if state.status == OrchestratorStatus.RETRY:
            return "retry"
        elif state.retry_count > state.max_retries:
            # Move to next task if available
            if state.task_queue:
                return "next"
            return "fail"
        return "next"
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            "workflow_id": self.workflow_id,
            "total_executions": len(self._execution_history),
            "router_stats": self.router.get_routing_stats(),
            "registry_stats": self.registry.get_stats(),
            "execution_history": self._execution_history[-10:]  # Last 10 executions
        }


def create_orchestrator(workflow_id: str,
                       tasks: List[Dict[str, Any]],
                       use_adaptive_routing: bool = True,
                       max_retries: int = 3) -> Tuple[MainOrchestrator, OrchestratorState]:
    """
    Factory function to create an orchestrator with initial state.
    
    Args:
        workflow_id: Unique workflow identifier
        tasks: List of tasks to execute
        use_adaptive_routing: Whether to use adaptive routing
        max_retries: Maximum retry attempts
        
    Returns:
        Tuple of (MainOrchestrator, initial OrchestratorState)
    """
    orchestrator = MainOrchestrator(
        workflow_id=workflow_id,
        use_adaptive_routing=use_adaptive_routing,
        max_retries=max_retries
    )
    
    initial_state = OrchestratorState(
        workflow_id=workflow_id,
        task_queue=tasks,
        max_retries=max_retries
    )
    
    return orchestrator, initial_state
