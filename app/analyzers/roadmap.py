"""RoadmapAnalyzer — release history and project trajectory.

Tracks project evolution through release history:
    - Release frequency and version progression
    - Recent milestones
    - Project momentum indicators
"""

from datetime import datetime, timezone

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput


class RoadmapAnalyzer(BaseAnalyzer):
    """Analyzes project release history and evolution trajectory."""

    @property
    def analyzer_id(self) -> str:
        return "roadmap"

    @property
    def display_name(self) -> str:
        return "技术路线"

    @property
    def order(self) -> int:
        return 55

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        releases = context.releases_data or []
        repo = context.repo_data
        now = datetime.now(timezone.utc)

        if not releases:
            return AnalyzerOutput(
                analyzer_id=self.analyzer_id,
                display_name=self.display_name,
                severity="info",
                summary="该项目暂无 Release 记录（可能使用持续发布模式）",
                score=0,
                details={},
                recommendations=[],
            )

        # ── Parse release data ──────────────────────────────
        release_list: list[dict] = []
        for rel in releases[:15]:
            tag = rel.get("tag_name", "")
            name = rel.get("name", tag)
            published = rel.get("published_at", "")
            is_prerelease = rel.get("prerelease", False)
            body = (rel.get("body") or "")[:200]
            release_list.append({
                "tag": tag,
                "name": name,
                "date": published[:10] if published else "",
                "prerelease": is_prerelease,
                "summary": body.strip(),
            })

        # ── Analysis ────────────────────────────────────────
        stable = [r for r in release_list if not r["prerelease"]]
        pre = [r for r in release_list if r["prerelease"]]

        # Release frequency
        if len(stable) >= 2 and stable[0]["date"] and stable[-1]["date"]:
            try:
                first = datetime.fromisoformat(stable[-1]["date"])
                last = datetime.fromisoformat(stable[0]["date"])
                span_days = max((last - first).days, 1)
            except ValueError:
                span_days = 0

        # Momentum assessment
        if len(releases) >= 10:
            momentum = "高频发布，项目非常活跃"
        elif len(releases) >= 5:
            momentum = "稳定发布节奏，项目持续演进中"
        elif len(releases) >= 2:
            momentum = "有版本发布记录，但频次较低"
        else:
            momentum = "发布次数少，可能处于早期阶段"

        # Latest version
        latest = release_list[0]["tag"] if release_list else "?"

        # Build summary
        summary = f"共 {len(releases)} 个版本，最新: {latest}"
        if stable:
            summary += f"（{len(stable)} 个稳定版）"
        summary += f" — {momentum}"

        # Version timeline
        timeline = [r["tag"] for r in release_list[:8]]

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity="info",
            summary=summary,
            score=None,
            details={
                "release_count": len(releases),
                "stable_count": len(stable),
                "prerelease_count": len(pre),
                "latest_version": latest,
                "momentum": momentum,
                "timeline": timeline,
                "releases": release_list[:8],
            },
            recommendations=[],
        )
