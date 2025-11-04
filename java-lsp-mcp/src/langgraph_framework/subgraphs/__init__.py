"""
Abstract Subgraph Classes

Provides standardized interfaces and base classes for building subgraphs
with consistent registration, state management, and execution patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from langgraph.graph import StateGraph, START, END

from ..registry import (
    SubgraphMetadata,
    SubgraphCapability,
    SubgraphRegistry,
    get_global_registry
)

logger = logging.getLogger(__name__)

# Type variable for subgraph state
StateT = TypeVar('StateT')


class SubgraphStatus(Enum):
    """Status of subgraph execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SubgraphState:
    """
    Base state for all subgraphs.
    
    Attributes:
        subgraph_name: Name of the subgraph
        input_data: Input data for the subgraph
        output_data: Output data from the subgraph
        status: Current execution status
        error: Error message if failed
        metadata: Additional execution metadata
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
    """
    subgraph_name: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    status: SubgraphStatus = SubgraphStatus.PENDING
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def mark_started(self) -> None:
        """Mark subgraph execution as started."""
        self.status = SubgraphStatus.RUNNING
        self.started_at = datetime.now()
    
    def mark_completed(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark subgraph execution as completed."""
        self.status = SubgraphStatus.COMPLETED
        self.completed_at = datetime.now()
        if output_data:
            self.output_data = output_data
    
    def mark_failed(self, error: str) -> None:
        """Mark subgraph execution as failed."""
        self.status = SubgraphStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def get_execution_time(self) -> Optional[float]:
        """Get execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BaseSubgraph(ABC, Generic[StateT]):
    """
    Abstract base class for all subgraphs.
    
    Provides standardized interface for subgraph registration,
    state management, and execution.
    """
    
    def __init__(self, name: str, auto_register: bool = True):
        """
        Initialize the subgraph.
        
        Args:
            name: Unique name for this subgraph
            auto_register: Whether to auto-register with global registry
        """
        self.name = name
        self._graph: Optional[StateGraph] = None
        self._compiled_graph = None
        
        if auto_register:
            self.register()
        
        logger.info(f"BaseSubgraph '{name}' initialized")
    
    @abstractmethod
    def get_metadata(self) -> SubgraphMetadata:
        """
        Get metadata describing this subgraph's capabilities.
        
        Returns:
            SubgraphMetadata for this subgraph
        """
        pass
    
    @abstractmethod
    def build_graph(self) -> StateGraph:
        """
        Build and return the LangGraph StateGraph for this subgraph.
        
        Returns:
            Constructed StateGraph (not yet compiled)
        """
        pass
    
    def get_compiled_graph(self):
        """
        Get or create compiled graph.
        
        Returns:
            Compiled graph instance
        """
        if self._compiled_graph is None:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
        return self._compiled_graph
    
    def register(self, registry: Optional[SubgraphRegistry] = None) -> None:
        """
        Register this subgraph with a registry.
        
        Args:
            registry: SubgraphRegistry to register with (uses global if None)
        """
        registry = registry or get_global_registry()
        metadata = self.get_metadata()
        
        # Update metadata name to match instance name
        metadata.name = self.name
        
        registry.register(metadata, self.get_compiled_graph)
        logger.info(f"Subgraph '{self.name}' registered")
    
    def deregister(self, registry: Optional[SubgraphRegistry] = None) -> bool:
        """
        Deregister this subgraph from a registry.
        
        Args:
            registry: SubgraphRegistry to deregister from (uses global if None)
            
        Returns:
            True if deregistered successfully
        """
        registry = registry or get_global_registry()
        result = registry.deregister(self.name)
        
        if result:
            logger.info(f"Subgraph '{self.name}' deregistered")
        
        return result
    
    async def execute(self, input_state: StateT) -> StateT:
        """
        Execute the subgraph with given input state.
        
        Args:
            input_state: Input state for the subgraph
            
        Returns:
            Output state from the subgraph
        """
        graph = self.get_compiled_graph()
        
        logger.info(f"Executing subgraph '{self.name}'")
        
        try:
            result = await graph.ainvoke(input_state)
            logger.info(f"Subgraph '{self.name}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"Subgraph '{self.name}' failed: {e}")
            raise
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self.name}')"


class CodeGenerationSubgraph(BaseSubgraph[SubgraphState]):
    """
    Example subgraph for code generation tasks.
    
    This is a boilerplate implementation that can be extended for
    specific code generation needs.
    """
    
    def __init__(self, 
                 name: str = "code_generator",
                 programming_languages: Optional[Set[str]] = None,
                 auto_register: bool = True):
        """
        Initialize code generation subgraph.
        
        Args:
            name: Subgraph name
            programming_languages: Supported programming languages
            auto_register: Whether to auto-register
        """
        self.programming_languages = programming_languages or {"java", "python"}
        super().__init__(name, auto_register)
    
    def get_metadata(self) -> SubgraphMetadata:
        """Get metadata for code generation subgraph."""
        return SubgraphMetadata(
            name=self.name,
            description="Code generation subgraph supporting multiple languages",
            capabilities={SubgraphCapability.CODE_GENERATION},
            tags=self.programming_languages,
            input_schema={
                "type": "object",
                "properties": {
                    "requirements": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["requirements"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "generated_code": {"type": "string"},
                    "file_path": {"type": "string"}
                }
            },
            priority=50
        )
    
    def build_graph(self) -> StateGraph:
        """Build the code generation graph."""
        graph = StateGraph(SubgraphState)
        
        # Add nodes
        graph.add_node("parse_requirements", self._parse_requirements)
        graph.add_node("generate_code", self._generate_code)
        graph.add_node("validate_code", self._validate_code)
        
        # Add edges
        graph.add_edge(START, "parse_requirements")
        graph.add_edge("parse_requirements", "generate_code")
        graph.add_edge("generate_code", "validate_code")
        graph.add_edge("validate_code", END)
        
        return graph
    
    def _parse_requirements(self, state: SubgraphState) -> SubgraphState:
        """Parse code generation requirements."""
        state.mark_started()
        logger.info(f"Parsing requirements for {self.name}")
        
        # Extract and parse requirements
        requirements = state.input_data.get("requirements", "")
        language = state.input_data.get("language", "java")
        
        state.metadata["parsed_requirements"] = requirements
        state.metadata["language"] = language
        
        return state
    
    def _generate_code(self, state: SubgraphState) -> SubgraphState:
        """Generate code based on requirements."""
        logger.info(f"Generating code for {self.name}")
        
        # Placeholder for actual code generation logic
        # In real implementation, this would use an LLM or code generation tool
        requirements = state.metadata.get("parsed_requirements", "")
        language = state.metadata.get("language", "java")
        
        # Simple placeholder code
        if language == "java":
            code = f"public class Generated {{\n    // TODO: {requirements}\n}}"
        else:
            code = f"# TODO: {requirements}\n"
        
        state.output_data["generated_code"] = code
        state.output_data["language"] = language
        
        return state
    
    def _validate_code(self, state: SubgraphState) -> SubgraphState:
        """Validate generated code."""
        logger.info(f"Validating code for {self.name}")
        
        # Placeholder for validation logic
        # In real implementation, this would compile or lint the code
        state.output_data["validation_passed"] = True
        state.mark_completed()
        
        return state


class ErrorCheckingSubgraph(BaseSubgraph[SubgraphState]):
    """
    Example subgraph for error checking tasks.
    
    Boilerplate implementation for error detection and analysis.
    """
    
    def __init__(self, 
                 name: str = "error_checker",
                 auto_register: bool = True):
        """
        Initialize error checking subgraph.
        
        Args:
            name: Subgraph name
            auto_register: Whether to auto-register
        """
        super().__init__(name, auto_register)
    
    def get_metadata(self) -> SubgraphMetadata:
        """Get metadata for error checking subgraph."""
        return SubgraphMetadata(
            name=self.name,
            description="Error checking and analysis subgraph",
            capabilities={SubgraphCapability.ERROR_CHECKING, SubgraphCapability.DEBUGGING},
            tags={"java", "compilation", "static-analysis"},
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "file_path": {"type": "string"}
                },
                "required": ["code"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "errors": {"type": "array"},
                    "error_count": {"type": "integer"}
                }
            },
            priority=70
        )
    
    def build_graph(self) -> StateGraph:
        """Build the error checking graph."""
        graph = StateGraph(SubgraphState)
        
        # Add nodes
        graph.add_node("analyze_code", self._analyze_code)
        graph.add_node("report_errors", self._report_errors)
        
        # Add edges
        graph.add_edge(START, "analyze_code")
        graph.add_edge("analyze_code", "report_errors")
        graph.add_edge("report_errors", END)
        
        return graph
    
    def _analyze_code(self, state: SubgraphState) -> SubgraphState:
        """Analyze code for errors."""
        state.mark_started()
        logger.info(f"Analyzing code for {self.name}")
        
        code = state.input_data.get("code", "")
        
        # Placeholder error detection
        # In real implementation, this would use a compiler or linter
        errors = []
        
        # Simple syntax check (placeholder)
        if "public class" not in code and "class" in code.lower():
            errors.append({
                "line": 1,
                "message": "Missing 'public' keyword",
                "severity": "error"
            })
        
        state.metadata["errors"] = errors
        
        return state
    
    def _report_errors(self, state: SubgraphState) -> SubgraphState:
        """Report detected errors."""
        logger.info(f"Reporting errors for {self.name}")
        
        errors = state.metadata.get("errors", [])
        
        state.output_data["errors"] = errors
        state.output_data["error_count"] = len(errors)
        state.mark_completed()
        
        return state


class RefactoringSubgraph(BaseSubgraph[SubgraphState]):
    """
    Example subgraph for code refactoring tasks.
    
    Boilerplate implementation for code refactoring.
    """
    
    def __init__(self, 
                 name: str = "refactorer",
                 auto_register: bool = True):
        """Initialize refactoring subgraph."""
        super().__init__(name, auto_register)
    
    def get_metadata(self) -> SubgraphMetadata:
        """Get metadata for refactoring subgraph."""
        return SubgraphMetadata(
            name=self.name,
            description="Code refactoring and optimization subgraph",
            capabilities={SubgraphCapability.REFACTORING, SubgraphCapability.OPTIMIZATION},
            tags={"java", "python", "refactoring"},
            priority=40
        )
    
    def build_graph(self) -> StateGraph:
        """Build the refactoring graph."""
        graph = StateGraph(SubgraphState)
        
        # Add nodes
        graph.add_node("analyze_structure", self._analyze_structure)
        graph.add_node("apply_refactoring", self._apply_refactoring)
        graph.add_node("verify_refactoring", self._verify_refactoring)
        
        # Add edges
        graph.add_edge(START, "analyze_structure")
        graph.add_edge("analyze_structure", "apply_refactoring")
        graph.add_edge("apply_refactoring", "verify_refactoring")
        graph.add_edge("verify_refactoring", END)
        
        return graph
    
    def _analyze_structure(self, state: SubgraphState) -> SubgraphState:
        """Analyze code structure."""
        state.mark_started()
        logger.info(f"Analyzing structure for {self.name}")
        return state
    
    def _apply_refactoring(self, state: SubgraphState) -> SubgraphState:
        """Apply refactoring transformations."""
        logger.info(f"Applying refactoring for {self.name}")
        
        code = state.input_data.get("code", "")
        # Placeholder refactoring
        refactored_code = code  # In real implementation, apply transformations
        
        state.output_data["refactored_code"] = refactored_code
        
        return state
    
    def _verify_refactoring(self, state: SubgraphState) -> SubgraphState:
        """Verify refactoring correctness."""
        logger.info(f"Verifying refactoring for {self.name}")
        
        state.output_data["verification_passed"] = True
        state.mark_completed()
        
        return state


def create_subgraph_from_template(
    name: str,
    capabilities: Set[SubgraphCapability],
    node_functions: Dict[str, callable],
    edges: list[tuple[str, str]],
    tags: Optional[Set[str]] = None,
    priority: int = 50,
    auto_register: bool = True
) -> BaseSubgraph:
    """
    Factory function to create a subgraph from a template.
    
    Args:
        name: Subgraph name
        capabilities: Set of capabilities
        node_functions: Dict mapping node names to functions
        edges: List of (from_node, to_node) tuples
        tags: Optional tags
        priority: Priority level
        auto_register: Whether to auto-register
        
    Returns:
        Configured BaseSubgraph instance
    """
    
    class TemplateSubgraph(BaseSubgraph[SubgraphState]):
        """Dynamically created subgraph from template."""
        
        def get_metadata(self) -> SubgraphMetadata:
            return SubgraphMetadata(
                name=name,
                description=f"Template-based subgraph: {name}",
                capabilities=capabilities,
                tags=tags or set(),
                priority=priority
            )
        
        def build_graph(self) -> StateGraph:
            graph = StateGraph(SubgraphState)
            
            # Add all nodes
            for node_name, func in node_functions.items():
                graph.add_node(node_name, func)
            
            # Add all edges
            for from_node, to_node in edges:
                if from_node == "START":
                    graph.add_edge(START, to_node)
                elif to_node == "END":
                    graph.add_edge(from_node, END)
                else:
                    graph.add_edge(from_node, to_node)
            
            return graph
    
    return TemplateSubgraph(name, auto_register)
