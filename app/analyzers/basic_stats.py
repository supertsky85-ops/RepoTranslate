"""BasicStatsAnalyzer — repository health scoring.

Scores a repo across 5 dimensions using only pre-fetched metadata:
    1. Stars (popularity)          — 25%
    2. Activity (maintenance)      — 25%
    3. Community (engagement)      — 20%
    4. Maturity (age / stability)  — 15%
    5. License (open-source health)— 15%

Returns a 0-100 score with a letter grade (S/A/B/C/D).
"""

from datetime import datetime, timezone

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput


class BasicStatsAnalyzer(BaseAnalyzer):
    """Analyzes basic repository health from metadata alone."""

    @property
    def analyzer_id(self) -> str:
        return "basic_stats"

    @property
    def display_name(self) -> str:
        return "Repository Health"

    @property
    def order(self) -> int:
        return 10  # Run first

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        data = context.repo_data
        now = datetime.now(timezone.utc)

        # ── Dimension 1: Stars (0-25) ──────────────────────
        stars = data.get("stargazers_count", 0) or 0
        star_score = min(stars / 10000, 1.0) * 25

        # ── Dimension 2: Activity (0-25) ───────────────────
        pushed_at_str = data.get("pushed_at") or data.get("updated_at")
        if pushed_at_str:
            pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
            days_since_push = (now - pushed_at).days
            # Full score if pushed within 30 days; declines to 0 at 365 days
            activity_score = max(0, (365 - min(days_since_push, 365)) / 365) * 25
        else:
            activity_score = 0
            days_since_push = None

        # ── Dimension 3: Community engagement (0-20) ───────
        forks = data.get("forks_count", 0) or 0
        open_issues = data.get("open_issues_count", 0) or 0

        # Fork ratio: forks/stars (healthy projects have active forking)
        if stars > 0:
            fork_ratio = min(forks / stars, 0.5)  # Cap at 0.5
            fork_score = (fork_ratio / 0.5) * 10  # 0-10 points
        else:
            fork_score = 0

        # Issue ratio: not too many, not zero (shows project is managed)
        if 0 < open_issues <= 500:
            # "Goldilocks" zone: 5-100 open issues is ideal
            if open_issues <= 100:
                issue_score = 10
            else:
                issue_score = max(0, 10 - (open_issues - 100) / 40)
        elif open_issues == 0 and stars > 0:
            issue_score = 5  # Zero issues could mean good management
        else:
            issue_score = 3  # Too many issues or can't tell

        community_score = fork_score + issue_score

        # ── Dimension 4: Maturity (0-15) ───────────────────
        created_at_str = data.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            age_days = (now - created_at).days
            if age_days > 730:        # >2 years
                maturity_score = 15
            elif age_days > 365:      # 1-2 years
                maturity_score = 12
            elif age_days > 180:      # 6 months - 1 year
                maturity_score = 8
            elif age_days > 90:       # 3-6 months
                maturity_score = 4
            else:                     # < 3 months
                maturity_score = 1
        else:
            maturity_score = 0
            age_days = None

        # ── Dimension 5: License (0-15) ────────────────────
        license_info = data.get("license")
        if license_info and isinstance(license_info, dict):
            license_key = license_info.get("key", "")
            if license_key and license_key != "none":
                license_score = 15
            else:
                license_score = 0
        else:
            license_score = 0

        # ── Total ──────────────────────────────────────────
        total = round(star_score + activity_score + community_score + maturity_score + license_score)
        grade = self._grade(total)

        # ── Build summary ──────────────────────────────────
        summaries = []
        if stars >= 1000:
            summaries.append(f"{stars:,} stars")
        if isinstance(days_since_push, int) and days_since_push is not None:
            if days_since_push <= 7:
                summaries.append("actively maintained")
            elif days_since_push <= 90:
                summaries.append(f"last pushed {days_since_push}d ago")
        if age_days and age_days >= 365:
            summaries.append(f"{age_days // 365}y old")

        summary = ", ".join(summaries) if summaries else f"Score {total}/100"
        if summaries:
            summary += " — " + ", ".join(summaries)

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity=self._severity(grade),
            summary=summary,
            score=total,
            details={
                "grade": grade,
                "dimensions": {
                    "stars": round(star_score, 1),
                    "activity": round(activity_score, 1),
                    "community": round(community_score, 1),
                    "maturity": round(maturity_score, 1),
                    "license": round(license_score, 1),
                },
                "raw": {
                    "stars": stars,
                    "forks": forks,
                    "open_issues": open_issues,
                    "days_since_push": days_since_push,
                    "age_days": age_days,
                    "has_license": license_score > 0,
                },
            },
            recommendations=self._recommendations(total, license_score, days_since_push),
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
        return {"S": "success", "A": "info", "B": "info", "C": "warning", "D": "critical"}[grade]

    @staticmethod
    def _recommendations(score: int, has_license: bool, days_since_push: int | None) -> list[str]:
        recs = []
        if not has_license:
            recs.append("Consider adding an open-source license to clarify usage rights.")
        if days_since_push is not None and days_since_push > 180:
            recs.append("Repository appears inactive — consider a maintainer note.")
        if score < 30:
            recs.append("This project may be an experiment or abandoned — review before depending on it.")
        return recs
