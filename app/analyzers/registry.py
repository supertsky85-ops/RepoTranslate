"""Analyzer registry — discovers, registers, and runs analyzers."""

import logging

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput, AnalysisResult

logger = logging.getLogger(__name__)


class AnalyzerRegistry:
    """Central registry for all repository analyzers.

    Usage:
        registry = AnalyzerRegistry()
        registry.register(BasicStatsAnalyzer())
        result = await registry.run_all(context)
    """

    def __init__(self):
        self._analyzers: dict[str, BaseAnalyzer] = {}

    def register(self, analyzer: BaseAnalyzer) -> None:
        """Register an analyzer instance."""
        if not analyzer.enabled:
            logger.debug(f"Skipping disabled analyzer: {analyzer.analyzer_id}")
            return
        self._analyzers[analyzer.analyzer_id] = analyzer
        logger.info(f"Registered analyzer: {analyzer.analyzer_id} ({analyzer.display_name})")

    def get(self, analyzer_id: str) -> BaseAnalyzer | None:
        """Get an analyzer by ID."""
        return self._analyzers.get(analyzer_id)

    def get_all(self) -> list[BaseAnalyzer]:
        """Get all registered analyzers, sorted by execution order."""
        return sorted(self._analyzers.values(), key=lambda a: a.order)

    async def run_all(self, context: AnalysisContext) -> AnalysisResult:
        """Run all registered analyzers on the given context.

        Each analyzer receives the same context and returns an AnalyzerOutput.
        Results are aggregated into an AnalysisResult.
        """
        outputs: list[AnalyzerOutput] = []

        for analyzer in self.get_all():
            try:
                output = await analyzer.analyze(context)
                outputs.append(output)
                logger.info(
                    f"Analyzer '{analyzer.analyzer_id}' completed "
                    f"(score={output.score})"
                )
            except Exception as e:
                logger.error(
                    f"Analyzer '{analyzer.analyzer_id}' failed: {e}",
                    exc_info=True,
                )
                outputs.append(
                    AnalyzerOutput(
                        analyzer_id=analyzer.analyzer_id,
                        display_name=analyzer.display_name,
                        severity="warning",
                        summary=f"Analysis failed: {e}",
                    )
                )

        # Compute overall score
        scores = [o.score for o in outputs if o.score is not None]
        overall = round(sum(scores) / len(scores)) if scores else None

        return AnalysisResult(
            owner=context.owner,
            repo=context.repo,
            outputs=outputs,
            overall_score=overall,
        )
