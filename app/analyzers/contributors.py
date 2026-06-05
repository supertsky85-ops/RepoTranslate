"""ContributorAnalyzer — bus factor and core team analysis.

Evaluates project health from contributor data:
    1. Contributor diversity (35%) — more contributors = healthier
    2. Bus factor (35%) — top 3 contributors' percentage
    3. Core team size (30%) — contributors with significant contributions
"""

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput


class ContributorAnalyzer(BaseAnalyzer):
    """Analyzes contributor patterns and project bus factor."""

    @property
    def analyzer_id(self) -> str:
        return "contributors"

    @property
    def display_name(self) -> str:
        return "Contributors"

    @property
    def order(self) -> int:
        return 60

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        contributors = context.contributors_data or []

        if not contributors:
            return AnalyzerOutput(
                analyzer_id=self.analyzer_id,
                display_name=self.display_name,
                severity="warning",
                summary="No contributor data available.",
                score=0,
                recommendations=["Unable to analyze contributors."],
            )

        total_contributions = sum(c.get("contributions", 0) for c in contributors)
        count = len(contributors)

        # ── 1. Diversity (0-35) ───────────────────────────
        if count >= 50:
            diversity_score = 35
        elif count >= 20:
            diversity_score = 28
        elif count >= 10:
            diversity_score = 20
        elif count >= 5:
            diversity_score = 12
        elif count >= 2:
            diversity_score = 6
        else:
            diversity_score = 2

        # ── 2. Bus factor (0-35) ─────────────────────────
        # Lower top-3 concentration = better (more distributed)
        top3_contribs = sum(
            c.get("contributions", 0) for c in contributors[:3]
        )
        if total_contributions > 0:
            top3_ratio = top3_contribs / total_contributions
        else:
            top3_ratio = 1.0

        if top3_ratio <= 0.4:
            bus_score = 35
        elif top3_ratio <= 0.55:
            bus_score = 28
        elif top3_ratio <= 0.7:
            bus_score = 20
        elif top3_ratio <= 0.85:
            bus_score = 10
        else:
            bus_score = 3

        # ── 3. Core team (0-30) ──────────────────────────
        # Contributors with >5% of total = core team
        core_threshold = total_contributions * 0.05 if total_contributions > 0 else 1
        core_team = [
            c for c in contributors
            if c.get("contributions", 0) >= core_threshold
        ]
        core_size = len(core_team)
        if core_size >= 10:
            core_score = 30
        elif core_size >= 5:
            core_score = 24
        elif core_size >= 3:
            core_score = 16
        elif core_size >= 2:
            core_score = 10
        else:
            core_score = 5

        # ── Total ────────────────────────────────────────
        total = round(diversity_score + bus_score + core_score)
        grade = self._grade(total)

        # ── Summary ──────────────────────────────────────
        top_names = [c.get("login", "?") for c in contributors[:3]]
        bus_factor = core_size  # Simplified: core team size ≈ bus factor
        summary = f"{count} 位贡献者"
        if top_names:
            summary += f"，核心: {', '.join(top_names[:3])}"

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity=self._severity(grade),
            summary=summary,
            score=total,
            details={
                "grade": grade,
                "contributor_count": count,
                "total_contributions": total_contributions,
                "top3_names": top_names,
                "top3_ratio": round(top3_ratio, 2),
                "bus_factor": bus_factor,
                "core_team_size": core_size,
                "top_contributors": [
                    {
                        "login": c.get("login"),
                        "contributions": c.get("contributions"),
                        "avatar": c.get("avatar_url"),
                    }
                    for c in contributors[:10]
                ],
            },
            recommendations=self._recommendations(
                grade, core_size, top3_ratio, count
            ),
        )

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 85:
            return "S"
        elif score >= 70:
            return "A"
        elif score >= 50:
            return "B"
        elif score >= 30:
            return "C"
        return "D"

    @staticmethod
    def _severity(grade: str) -> str:
        return {
            "S": "success", "A": "info", "B": "info",
            "C": "warning", "D": "critical",
        }[grade]

    @staticmethod
    def _recommendations(
        grade: str, core_size: int, top3_ratio: float, count: int
    ) -> list[str]:
        recs = []
        if core_size <= 1:
            recs.append(
                "Bus factor is 1 — the project depends on a single person. "
                "Consider bringing in co-maintainers."
            )
        elif core_size <= 2:
            recs.append(
                "Low bus factor. Consider expanding the core maintainer team."
            )
        if top3_ratio > 0.8:
            recs.append(
                "Contributions are highly concentrated. Encourage wider participation."
            )
        if count < 5:
            recs.append(
                "Very few contributors. Add CONTRIBUTING.md to attract new contributors."
            )
        return recs
