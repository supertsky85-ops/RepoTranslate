"""Pydantic models for the analysis pipeline."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalyzerOutput(BaseModel):
    """Output from a single analyzer."""

    analyzer_id: str
    display_name: str
    severity: str = "info"  # info | warning | critical | success
    summary: str = ""
    score: int | None = None  # 0-100, if applicable
    details: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


class AnalysisContext(BaseModel):
    """Data context passed to every analyzer.

    Contains pre-fetched data — analyzers should NOT call GitHub API directly.
    """

    owner: str
    repo: str
    repo_data: dict[str, Any] = Field(default_factory=dict)
    readme_data: dict[str, Any] | None = None
    languages_data: dict[str, int] = Field(default_factory=dict)
    tree_data: list[dict[str, Any]] = Field(default_factory=list)
    commits_data: list[dict[str, Any]] = Field(default_factory=list)
    issues_data: list[dict[str, Any]] = Field(default_factory=list)
    contributors_data: list[dict[str, Any]] = Field(default_factory=list)
    releases_data: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class AnalysisResult(BaseModel):
    """Aggregated result from all analyzers."""

    owner: str
    repo: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    outputs: list[AnalyzerOutput] = Field(default_factory=list)
    overall_score: int | None = None

    @property
    def best_output(self) -> AnalyzerOutput | None:
        """The highest-scoring analyzer output, if any."""
        scored = [o for o in self.outputs if o.score is not None]
        if not scored:
            return self.outputs[0] if self.outputs else None
        return max(scored, key=lambda o: o.score or 0)
