"""ReadmeAnalyzer — deep README analysis.

Extracts:
    - Project description (first meaningful paragraph)
    - Section structure (all headings)
    - Installation instructions (code blocks near install headings)
    - Usage examples (code blocks near usage headings)
    - Technology requirements (mentioned in README)
    - All external links with labels
    - Badges and images count
"""

import base64
import re
from typing import Any

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput


class ReadmeAnalyzer(BaseAnalyzer):
    """Deep README content analysis."""

    @property
    def analyzer_id(self) -> str:
        return "readme_summary"

    @property
    def display_name(self) -> str:
        return "README Quality"

    @property
    def order(self) -> int:
        return 20

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        readme_data = context.readme_data
        if not readme_data:
            return AnalyzerOutput(
                analyzer_id=self.analyzer_id,
                display_name=self.display_name,
                severity="warning",
                summary="该仓库没有 README 文件",
                score=0,
                recommendations=["建议添加 README.md 来描述项目"],
            )

        content = self._decode(readme_data)
        if not content:
            return AnalyzerOutput(
                analyzer_id=self.analyzer_id,
                display_name=self.display_name,
                severity="warning",
                summary="README 文件为空",
                score=0,
                recommendations=["请在 README 中添加内容"],
            )

        # ── 1. Basic stats ────────────────────────────────
        char_count = len(content)
        # Headings
        headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
        heading_texts = [h.strip() for h in headings]
        # Badges (shields.io, badge svg)
        badge_count = len(re.findall(
            r'!\[.*?\]\([^)]*?(?:shields\.io|badge|\.svg)[^)]*?\)',
            content, re.IGNORECASE,
        ))
        # Images (non-badge)
        total_images = len(re.findall(r'!\[.*?\]\(.*?\)', content))
        image_count = max(0, total_images - badge_count)
        # Links
        all_links = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', content)

        # ── 2. Extract description ────────────────────────
        description = self._extract_description(content)

        # ── 3. Extract installation ───────────────────────
        install_text = self._extract_section_content(
            content, ['install', 'getting started', 'setup', 'quick start', 'quickstart']
        )

        # ── 4. Extract usage examples ─────────────────────
        usage_text = self._extract_section_content(
            content, ['usage', 'example', 'how to use', 'quickstart']
        )

        # ── 5. Extract code blocks ────────────────────────
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
        # Filter to reasonable-sized examples
        examples: list[dict] = []
        for lang, code in code_blocks[:5]:
            code = code.strip()
            if 10 < len(code) < 500 and not code.startswith('$'):  # Skip shell prompts
                examples.append({"lang": lang or "text", "code": code[:300]})

        # ── 6. Extract tech requirements ──────────────────
        tech_mentions = self._extract_tech_requirements(content)

        # ── Build summary ─────────────────────────────────
        parts = []
        if char_count:
            parts.append(f"{char_count} 字")
        if heading_texts:
            parts.append(f"{len(heading_texts)} 个章节")
        if badge_count:
            parts.append(f"{badge_count} 个徽章")
        if all_links:
            parts.append(f"{len(all_links)} 个链接")
        summary = "，".join(parts) if parts else "已分析"

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity="info",
            summary=summary,
            score=None,
            details={
                "stats": {
                    "char_count": char_count,
                    "badge_count": badge_count,
                    "image_count": image_count,
                    "link_count": len(all_links),
                    "heading_count": len(heading_texts),
                },
                "preview": description,
                "sections": heading_texts[:25],
                "install_text": install_text,
                "usage_text": usage_text,
                "examples": examples,
                "tech_requirements": tech_mentions,
                "links": [
                    {"label": l[0][:60], "url": l[1][:120]}
                    for l in all_links[:12]
                ],
                "readme_name": readme_data.get("name", "README.md"),
            },
            recommendations=self._recommendations(
                char_count, badge_count, image_count, heading_texts
            ),
        )

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _decode(data: dict[str, Any]) -> str:
        if not data:
            return ""
        content = data.get("content", "")
        encoding = data.get("encoding", "")
        if encoding == "base64" and content:
            try:
                return base64.b64decode(content).decode("utf-8", errors="replace")
            except Exception:
                return ""
        return content

    @staticmethod
    def _extract_description(text: str) -> str:
        """Extract first meaningful paragraph after title/badges."""
        lines = text.split("\n")
        paragraph: list[str] = []
        started = False

        for line in lines:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("```"):
                if started and paragraph:
                    break
                continue
            if s.startswith("---") or s.startswith("==="):
                if started:
                    break
                continue
            if re.match(r'^\[?!\[', s):
                continue
            if re.match(r'^\[.*?\]\(.*?\)$', s):
                continue
            started = True
            # Strip markdown bold/italic
            clean = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', s)
            paragraph.append(clean)
            if len(" ".join(paragraph)) > 300:
                break

        result = " ".join(paragraph).strip()
        if len(result) > 300:
            result = result[:297] + "..."
        return result

    @staticmethod
    def _extract_section_content(text: str, keywords: list[str]) -> str | None:
        """Extract content under a heading that matches keywords."""
        lines = text.split("\n")
        capture = False
        content_lines: list[str] = []

        for i, line in enumerate(lines):
            s = line.strip().lower()
            # Check if this line is a matching heading
            if re.match(r'^#{1,3}\s+', line.strip()):
                heading = line.strip().lstrip("#").strip().lower()
                if any(kw in heading for kw in keywords):
                    capture = True
                    continue
                elif capture:
                    break  # Next heading, stop

            if capture and line.strip():
                content_lines.append(line.strip())
                if len(content_lines) > 15:
                    break

        if content_lines:
            text = "\n".join(content_lines)
            if len(text) > 500:
                text = text[:497] + "..."
            return text
        return None

    @staticmethod
    def _extract_tech_requirements(text: str) -> list[str]:
        """Detect technology requirements mentioned in README."""
        techs: list[str] = []
        patterns = [
            (r'python\s*([\d.]+)', 'Python'),
            (r'node(?:\.js)?\s*([\d.]+)', 'Node.js'),
            (r'go\s*([\d.]+)', 'Go'),
            (r'java\s*([\d.]+)', 'Java'),
            (r'rust', 'Rust'),
            (r'docker', 'Docker'),
            (r'pip\s+install', 'pip'),
            (r'npm\s+install', 'npm'),
            (r'yarn\s+add', 'Yarn'),
            (r'cargo\s+install', 'Cargo'),
            (r'go\s+get', 'go get'),
            (r'gem\s+install', 'RubyGems'),
            (r'composer\s+require', 'Composer'),
        ]
        for pattern, name in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if name not in techs:
                    techs.append(name)
        return techs

    @staticmethod
    def _recommendations(
        char_count: int, badges: int, images: int, headings: list[str]
    ) -> list[str]:
        recs = []
        if char_count < 200:
            recs.append("README 内容过短，建议补充项目说明和使用方法")
        if badges == 0:
            recs.append("建议添加 CI/CD 或版本徽章（shields.io）增强可信度")
        if images == 0:
            recs.append("建议添加截图或架构图帮助新用户理解项目")
        heading_text = " ".join(headings).lower()
        if "install" not in heading_text and "getting started" not in heading_text:
            recs.append("建议添加「安装」或「快速开始」章节")
        if "usage" not in heading_text and "example" not in heading_text:
            recs.append("建议添加使用示例帮助用户快速上手")
        return recs
