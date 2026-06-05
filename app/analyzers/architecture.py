"""ArchitectureAnalyzer — infers project architecture from directory structure.

Examines the repo's file tree to identify:
- Architecture pattern (MVC, layered, microservices, monorepo, etc.)
- Framework-specific directory layouts (Django, React, Go standard, etc.)
- Generates a text-based architecture diagram
"""

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput

# ── Pattern definitions ───────────────────────────────────────

# Each pattern: (name, description, score_value, required_dirs, optional_dirs)
ARCH_PATTERNS: list[tuple[str, str, int, list[str], list[str]]] = [
    (
        "Go Standard Layout",
        "Follows the Go project layout convention (cmd/, internal/, pkg/).",
        90,
        ["cmd/", "internal/", "pkg/"],
        ["api/", "web/", "scripts/", "build/", "deployments/"],
    ),
    (
        "Layered Architecture (src-based)",
        "Source organized in src/ with clear layer separation (models, services, controllers).",
        85,
        ["src/"],
        ["tests/", "docs/", "config/"],
    ),
    (
        "MVC (Model-View-Controller)",
        "Classic MVC pattern with separate model, view, and controller directories.",
        80,
        ["models/", "views/"],
        ["controllers/", "templates/", "static/", "routes/"],
    ),
    (
        "Monorepo",
        "Multiple packages/apps in a single repository with shared tooling.",
        75,
        ["packages/"],
        ["apps/", "libs/", "tools/", "lerna.json"],
    ),
    (
        "Microservices",
        "Independent services, each with their own configuration and Docker setup.",
        75,
        ["services/"],
        ["api-gateway/", "docker-compose.yml"],
    ),
    (
        "Frontend-Backend Split",
        "Separate client and server directories with distinct build configurations.",
        80,
        ["client/", "server/"],
        ["shared/", "api/", "docker-compose.yml"],
    ),
    (
        "Component-Based Frontend",
        "UI organized around reusable components with pages/routes separation.",
        70,
        ["components/", "pages/"],
        ["hooks/", "utils/", "styles/", "public/", "assets/"],
    ),
    (
        "Django-style",
        "Django project structure with apps, settings, templates, and static files.",
        85,
        ["manage.py"],
        ["templates/", "static/", "urls/", "settings/", "wsgi.py", "asgi.py"],
    ),
    (
        "Flask/FastAPI-style",
        "Minimal Python web app with routes, models, and config modules.",
        70,
        ["app/"],
        ["routes/", "models/", "config/", "main.py", "requirements.txt"],
    ),
    (
        "React/Next.js-style",
        "React-based project with pages/app router, components, and public assets.",
        75,
        ["public/", "src/"],
        ["pages/", "app/", "components/", "next.config"],
    ),
]

# Framework-specific files/dirs
FRAMEWORK_SIGNATURES: dict[str, str] = {
    "manage.py + settings/": "Django",
    "app/ + routes/ + models/": "FastAPI / Flask",
    "next.config.": "Next.js",
    "nuxt.config.": "Nuxt",
    "svelte.config.": "SvelteKit",
    "astro.config.": "Astro",
    "remix.config.": "Remix",
    "docusaurus.config.": "Docusaurus",
    "gatsby-config.": "Gatsby",
    "angular.json": "Angular",
    "nest-cli.json": "NestJS",
    "CMakeLists.txt + src/": "C/C++ (CMake)",
    "Cargo.toml + src/": "Rust (Cargo)",
    "go.mod + cmd/": "Go service",
    "setup.py + src/": "Python package",
    "pyproject.toml + src/": "Python package",
}


class ArchitectureAnalyzer(BaseAnalyzer):
    """Infers project architecture from directory structure."""

    @property
    def analyzer_id(self) -> str:
        return "architecture"

    @property
    def display_name(self) -> str:
        return "Architecture"

    @property
    def order(self) -> int:
        return 40

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        tree = context.tree_data or []
        dirs = {
            item.get("path", "").rstrip("/")
            for item in tree
            if item.get("type") == "tree"
        }
        files = {
            item.get("path", "")
            for item in tree
            if item.get("type") == "blob"
        }

        # ── Match architecture patterns ──────────────────────
        matches: list[tuple[str, str, int]] = []

        for name, desc, score, required, optional in ARCH_PATTERNS:
            # Required entries can be files or dirs
            req_hits = sum(
                1 for r in required
                if r in dirs or r in files or any(d.startswith(r) for d in dirs)
            )
            if req_hits >= len(required) * 0.6:  # 60% match threshold
                opt_hits = sum(
                    1 for o in optional
                    if o in dirs or o in files or any(d.startswith(o) for d in dirs)
                )
                final_score = min(score + opt_hits * 2, 100)
                matches.append((name, desc, final_score))

        # ── Detect framework signatures ──────────────────────
        frameworks: list[str] = []
        for sig, fw_name in FRAMEWORK_SIGNATURES.items():
            sig_parts = [s.strip() for s in sig.split("+")]
            if all(
                p in dirs or p in files or any(d.startswith(p) for d in dirs)
                for p in sig_parts
            ):
                frameworks.append(fw_name)

        # ── Scoring ─────────────────────────────────────────
        if matches:
            best_name, best_desc, best_score = matches[0]
            for m in matches[1:]:
                if m[2] > best_score:
                    best_name, best_desc, best_score = m
            grade = self._grade(best_score)
            summary = f"架构模式: {best_name} — {best_desc}"
            arch_name = best_name
            arch_desc = best_desc
            score = best_score
        else:
            # No clear pattern detected
            grade = "D"
            score = 15
            arch_name = "Unstructured"
            arch_desc = "No recognizable architecture pattern detected."
            summary = "未检测到明确的架构模式"

        # ── Generate ASCII diagram ───────────────────────────
        diagram = self._generate_diagram(dirs, files, arch_name)

        # ── Top-level structure ──────────────────────────────
        top_dirs = sorted([d for d in dirs if "/" not in d])
        top_files = sorted([
            f for f in files
            if "/" not in f and not f.startswith(".")
        ])[:10]

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity=self._severity(grade),
            summary=summary,
            score=score,
            details={
                "grade": grade,
                "arch_name": arch_name,
                "arch_description": arch_desc,
                "frameworks": frameworks,
                "diagram": diagram,
                "top_dirs": top_dirs[:12],
                "top_files": top_files[:12],
                "dir_count": len(dirs),
                "file_count": len(files),
            },
            recommendations=self._recommendations(score, arch_name, frameworks),
        )

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _generate_diagram(dirs: set[str], files: set[str], arch_name: str) -> str:
        """Generate a simple ASCII tree diagram of top-level structure."""
        top = sorted([d for d in dirs if "/" not in d])[:8]
        lines = []
        for i, d in enumerate(top):
            prefix = "└── " if i == len(top) - 1 else "├── "
            lines.append(f"{prefix}{d}/")

        if not lines:
            # Fall back to top-level files
            top_files = sorted([f for f in files if "/" not in f])[:8]
            for i, f in enumerate(top_files):
                prefix = "└── " if i == len(top_files) - 1 else "├── "
                lines.append(f"{prefix}{f}")

        return f"├── {arch_name}\n" + "\n".join(lines) if lines else ""

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
        score: int, arch_name: str, frameworks: list[str]
    ) -> list[str]:
        recs = []
        if score < 50:
            recs.append(
                "Consider adopting a standard project layout for better discoverability."
            )
        if not frameworks:
            recs.append("No specific framework detected — add framework configuration.")
        if arch_name == "Unstructured":
            recs.append(
                "Consider organizing code into logical directories (src/, tests/, docs/)."
            )
        return recs
