"""
Error Recommendation Engine

This module provides intelligent recommendations for fixing Java compilation errors.
It implements the Strategy pattern to handle different error types.
"""

from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class RecommendationStrategy:
    """Base class for error-specific recommendation strategies.

    This implements the Strategy design pattern, allowing different
    error types to have specialized recommendation logic.
    """

    def can_handle(self, error: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the given error.

        Args:
            error: Error dictionary with 'message' key

        Returns:
            True if this strategy should handle the error
        """
        raise NotImplementedError

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        """Generate recommendations for the error.

        Args:
            error: Error dictionary

        Returns:
            List of recommendation strings
        """
        raise NotImplementedError


class CannotFindSymbolStrategy(RecommendationStrategy):
    """Strategy for 'cannot find symbol' errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "cannot find symbol" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Check that the class, variable, or method name is spelled correctly",
            "Ensure the required import statement is present",
            "Verify that the variable is declared before use"
        ]


class SyntaxErrorStrategy(RecommendationStrategy):
    """Strategy for syntax errors like missing braces."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "class, interface, or enum expected" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Check for missing or extra braces { }",
            "Ensure all methods are inside a class",
            "Verify that all blocks are properly closed"
        ]


class MissingSemicolonStrategy(RecommendationStrategy):
    """Strategy for missing semicolon errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "';' expected" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Add a semicolon at the end of the statement",
            "Check for syntax errors in the line"
        ]


class TypeMismatchStrategy(RecommendationStrategy):
    """Strategy for type mismatch errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return any(x in message for x in ["incompatible types", "type mismatch"])

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Check that the value type matches the variable type",
            "Consider explicit type casting if appropriate",
            "Verify that method return types match expected types"
        ]


class MethodSignatureStrategy(RecommendationStrategy):
    """Strategy for method signature errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "method" in message and "cannot be applied" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Check the number and types of arguments passed to the method",
            "Verify the method signature matches the expected parameters",
            "Ensure arguments are in the correct order"
        ]


class DuplicateDeclarationStrategy(RecommendationStrategy):
    """Strategy for duplicate declaration errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "duplicate" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Remove or rename the duplicate declaration",
            "Check for accidental duplicate imports",
            "Verify variable names are unique in scope"
        ]


class PackageNotFoundStrategy(RecommendationStrategy):
    """Strategy for package/import not found errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "package" in message and "does not exist" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Verify the package name is spelled correctly",
            "Check that the required library is in the classpath",
            "Ensure the dependency is properly configured"
        ]


class UnreachableCodeStrategy(RecommendationStrategy):
    """Strategy for unreachable code errors."""

    def can_handle(self, error: Dict[str, Any]) -> bool:
        message = error.get("message", "").lower()
        return "unreachable statement" in message

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        return [
            "Remove code after return, break, or continue statements",
            "Check for unreachable code blocks",
            "Verify control flow logic"
        ]


class ErrorRecommendationEngine:
    """Main recommendation engine using Strategy pattern.

    This class maintains a registry of recommendation strategies and
    routes errors to the appropriate strategy.
    """

    def __init__(self):
        """Initialize the engine with default strategies."""
        self.strategies: List[RecommendationStrategy] = [
            CannotFindSymbolStrategy(),
            SyntaxErrorStrategy(),
            MissingSemicolonStrategy(),
            TypeMismatchStrategy(),
            MethodSignatureStrategy(),
            DuplicateDeclarationStrategy(),
            PackageNotFoundStrategy(),
            UnreachableCodeStrategy(),
        ]

    def register_strategy(self, strategy: RecommendationStrategy) -> None:
        """Register a custom recommendation strategy.

        Args:
            strategy: RecommendationStrategy instance
        """
        self.strategies.insert(0, strategy)  # Check custom strategies first
        logger.info(f"Registered strategy: {strategy.__class__.__name__}")

    def get_recommendations(self, error: Dict[str, Any]) -> List[str]:
        """Get recommendations for an error.

        Args:
            error: Error dictionary with 'message' key

        Returns:
            List of recommendation strings
        """
        # Find first matching strategy
        for strategy in self.strategies:
            if strategy.can_handle(error):
                try:
                    return strategy.get_recommendations(error)
                except Exception as e:
                    logger.error(f"Error in strategy {strategy.__class__.__name__}: {e}")
                    break

        # Default recommendations
        return self._default_recommendations(error)

    def _default_recommendations(self, error: Dict[str, Any]) -> List[str]:
        """Return default recommendations for unhandled errors."""
        return [
            "Review the error message and consult Java documentation",
            "Check the syntax and naming conventions",
            "Verify all imports and dependencies are correct"
        ]
