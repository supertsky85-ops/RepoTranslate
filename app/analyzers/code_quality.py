"""CodeQualityAnalyzer — commit frequency and issue resolution trends.

Analyzes recent commit activity and issue management:
    1. Commit frequency (30%) — commits/day in last 30 days
    2. Maintenance rhythm (25%) — consistency of commit intervals
    3. Issue resolution (25%) — closed/total ratio
    4. Response speed (20%) — recent issue closure velocity
"""

from datetime import datetime, timezone
import statistics

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput


class CodeQualityAnalyzer(BaseAnalyzer):
    """Analyzes code quality signals from commit and issue data."""

    @property
    def analyzer_id(self) -> str:
        return "code_quality"

    @property
    def display_name(self) -> str:
        return "Code Quality"

    @property
    def order(self) -> int:
        return 50

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        commits = context.commits_data or []
        issues = context.issues_data or []
        now = datetime.now(timezone.utc)

        # ── 1. Commit frequency (0-30) ─────────────────────
        recent_commits = 0
        commit_dates: list[datetime] = []
        for c in commits:
            author = c.get("commit", {}).get("author", {})
            date_str = author.get("date", "")
            if date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                commit_dates.append(dt)
                if (now - dt).days <= 30:
                    recent_commits += 1

        commits_per_day = recent_commits / 30 if recent_commits > 0 else 0
        if commits_per_day >= 2:
            freq_score = 30
        elif commits_per_day >= 1:
            freq_score = 25
        elif commits_per_day >= 0.3:
            freq_score = 18
        elif commits_per_day >= 0.1:
            freq_score = 10
        elif commits_per_day > 0:
            freq_score = 5
        else:
            freq_score = 0

        # ── 2. Maintenance rhythm (0-25) ──────────────────
        if len(commit_dates) >= 3:
            intervals: list[float] = []
            sorted_dates = sorted(commit_dates, reverse=True)[:30]
            for i in range(len(sorted_dates) - 1):
                gap = (sorted_dates[i] - sorted_dates[i + 1]).total_seconds() / 3600
                intervals.append(gap)

            mean_interval = statistics.mean(intervals) if intervals else 0
            if len(intervals) >= 2:
                stdev = statistics.stdev(intervals) if mean_interval > 0 else 999
            else:
                stdev = 999

            # Low stdev relative to mean = regular rhythm
            if mean_interval > 0 and stdev < mean_interval * 1.5:
                rhythm_score = 20 + min(int(5 * (mean_interval / (stdev + 0.001))), 5)
            elif mean_interval > 0 and stdev < mean_interval * 3:
                rhythm_score = 15
            elif mean_interval > 0:
                rhythm_score = 8
            else:
                rhythm_score = 5
        else:
            rhythm_score = 0
            intervals = []
            mean_interval = 0

        # ── 3. Issue resolution (0-25) ────────────────────
        total_issues = len(issues)
        closed_issues = sum(
            1 for i in issues if i.get("state") == "closed"
        )
        if total_issues > 0:
            resolution_rate = closed_issues / total_issues
            resolution_score = round(resolution_rate * 25)
        else:
            resolution_score = 25  # No issues = good sign (or new project)
            resolution_rate = 1.0

        # ── 4. Response speed (0-20) ──────────────────────
        closed_dates: list[datetime] = []
        for i in issues:
            if i.get("state") == "closed":
                closed_str = i.get("closed_at", "")
                if closed_str:
                    closed_dates.append(
                        datetime.fromisoformat(closed_str.replace("Z", "+00:00"))
                    )

        if closed_dates:
            # Average age of recently closed issues (lower = faster response)
            ages = [(now - d).days for d in closed_dates[:20]]
            avg_age = statistics.mean(ages) if ages else 90
            if avg_age <= 7:
                response_score = 20
            elif avg_age <= 30:
                response_score = 15
            elif avg_age <= 90:
                response_score = 10
            elif avg_age <= 180:
                response_score = 5
            else:
                response_score = 2
        else:
            response_score = 0
            avg_age = None

        # ── Total ──────────────────────────────────────────
        total = round(freq_score + rhythm_score + resolution_score + response_score)
        grade = self._grade(total)

        # ── Summary ────────────────────────────────────────
        parts = []
        if commits_per_day >= 0.1:
            parts.append(f"{commits_per_day:.1f} commits/day")
        if resolution_rate > 0:
            parts.append(f"{resolution_rate:.0%} issues resolved")
        if not parts:
            parts.append("insufficient data")
        summary = ", ".join(parts) if parts else "insufficient data"

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity=self._severity(grade),
            summary=summary,
            score=total,
            details={
                "grade": grade,
                "commits_per_day": round(commits_per_day, 2),
                "recent_commits_30d": recent_commits,
                "total_commits_fetched": len(commits),
                "resolution_rate": round(resolution_rate, 2),
                "closed_issues": closed_issues,
                "total_issues": total_issues,
                "mean_commit_interval_hours": round(mean_interval, 1) if mean_interval else None,
                "avg_issue_age_days": round(avg_age, 1) if avg_age else None,
            },
            recommendations=self._recommendations(
                commits_per_day, resolution_rate, grade
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
        commits_per_day: float, resolution_rate: float, grade: str
    ) -> list[str]:
        recs = []
        if commits_per_day == 0:
            recs.append("No recent commits — the project may be abandoned.")
        elif commits_per_day < 0.1:
            recs.append("Low commit frequency. Consider increasing maintenance cadence.")
        if resolution_rate < 0.5:
            recs.append(
                "Low issue resolution rate. Triage and close stale issues."
            )
        if grade in ("D", "C"):
            recs.append("Overall code quality signals are weak — review project health.")
        return recs
