"""Base analyzer abstract class — the plugin contract.

To add a new analyzer:
    1. Create a file in app/analyzers/
    2. Subclass BaseAnalyzer
    3. Implement analyze()
    4. Register it in the AnalyzerRegistry
"""

from abc import ABC, abstractmethod

from app.models.analysis import AnalysisContext, AnalyzerOutput


class BaseAnalyzer(ABC):
    """Abstract base class for all repository analyzers.

    Subclasses must provide:
        - analyzer_id: unique string identifier
        - display_name: human-readable name
        - analyze(): the analysis logic
    """

    @property
    @abstractmethod
    def analyzer_id(self) -> str:
        """Unique identifier for this analyzer (e.g., 'basic_stats')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name (e.g., 'Basic Stats')."""
        ...

    @property
    def order(self) -> int:
        """Execution order (lower = runs first). Default: 100."""
        return 100

    @property
    def enabled(self) -> bool:
        """Whether this analyzer is active. Default: True."""
        return True

    @abstractmethod
    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        """Run analysis on the given context.

        Args:
            context: Pre-fetched repository data. Do NOT call GitHub API here.

        Returns:
            AnalyzerOutput with results, score, and recommendations.
        """
        ...
