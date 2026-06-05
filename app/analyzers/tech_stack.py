"""TechStackAnalyzer — detects languages, frameworks, and tooling.

Uses GitHub's /languages API + repository file tree to build a
comprehensive technology inventory.

Detection is purely file-name based (no content parsing needed).
"""

from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput

# ── File → Technology mapping ─────────────────────────────────

LANG_CONFIGS: dict[str, str] = {
    "package.json": "Node.js (npm)",
    "package-lock.json": "Node.js (npm)",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "tsconfig.json": "TypeScript",
    "requirements.txt": "Python (pip)",
    "setup.py": "Python (setuptools)",
    "setup.cfg": "Python (setuptools)",
    "pyproject.toml": "Python (pip/setuptools)",
    "Pipfile": "Pipenv",
    "poetry.lock": "Poetry",
    "go.mod": "Go",
    "go.sum": "Go",
    "Cargo.toml": "Rust",
    "Cargo.lock": "Rust",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
    "build.gradle.kts": "Java (Gradle Kotlin DSL)",
    "settings.gradle": "Java (Gradle)",
    "Gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)",
    "composer.lock": "PHP (Composer)",
    "CMakeLists.txt": "C/C++ (CMake)",
    "Makefile": "Make",
    "meson.build": "Meson",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    ".github/workflows": "GitHub Actions",        # directory
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
    ".travis.yml": "Travis CI",
    ".circleci/config.yml": "CircleCI",
    ".eslintrc.js": "ESLint",
    ".eslintrc.json": "ESLint",
    ".eslintrc.yml": "ESLint",
    ".prettierrc": "Prettier",
    ".prettierrc.json": "Prettier",
    ".prettierrc.js": "Prettier",
    "prettier.config.js": "Prettier",
    "tailwind.config.js": "Tailwind CSS",
    "tailwind.config.ts": "Tailwind CSS",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "webpack.config.js": "Webpack",
    "next.config.js": "Next.js",
    "next.config.ts": "Next.js",
    "next.config.mjs": "Next.js",
    "nuxt.config.js": "Nuxt",
    "nuxt.config.ts": "Nuxt",
    "astro.config.mjs": "Astro",
    "svelte.config.js": "Svelte",
    "remix.config.js": "Remix",
    "docusaurus.config.js": "Docusaurus",
    "mkdocs.yml": "MkDocs",
    ".terraform": "Terraform",                    # directory
    "ansible.cfg": "Ansible",
    "Vagrantfile": "Vagrant",
    ".env.example": "dotenv",
    ".editorconfig": "EditorConfig",
    "renovate.json": "Renovate",
    "jest.config.js": "Jest",
    "jest.config.ts": "Jest",
    "vitest.config.ts": "Vitest",
    "cypress.config.js": "Cypress",
    "playwright.config.ts": "Playwright",
    "tox.ini": "tox (Python)",
    ".pre-commit-config.yaml": "pre-commit",
    # Python ecosystem
    "pyproject.toml": "Python (pip/setuptools)",
    "ruff.toml": "Ruff",
    ".flake8": "Flake8",
    ".pylintrc": "Pylint",
    "mypy.ini": "Mypy",
    "pytest.ini": "Pytest",
    "conftest.py": "Pytest",
    "pyrightconfig.json": "Pyright",
    "coverage.json": "Coverage",
    ".coveragerc": "Coverage",
    "bandit.yaml": "Bandit",
    # Node.js ecosystem
    ".eslintignore": "ESLint",
    ".prettierignore": "Prettier",
    ".stylelintrc": "Stylelint",
    "babel.config.js": "Babel",
    "babel.config.json": "Babel",
    ".babelrc": "Babel",
    "postcss.config.js": "PostCSS",
    "rollup.config.js": "Rollup",
    # Rust ecosystem
    "rustfmt.toml": "rustfmt",
    "clippy.toml": "Clippy",
    # Go ecosystem
    ".golangci.yml": "golangci-lint",
    # Ruby ecosystem
    ".rubocop.yml": "RuboCop",
    "Rakefile": "Rake",
    # Java ecosystem
    ".mvn/wrapper": "Maven Wrapper",
    "gradlew": "Gradle Wrapper",
    ".editorconfig": "EditorConfig",
    "CHANGELOG.md": "Changelog",
    "CONTRIBUTING.md": "Contributing Guide",
    "CODEOWNERS": "CODEOWNERS",
    "SECURITY.md": "Security Policy",
}

# Categories for grouping
CATEGORIES: dict[str, list[str]] = {
    "Language / Runtime": [],
    "Package Manager": [],
    "Framework": [],
    "Build / Bundler": [],
    "Testing": [],
    "Lint / Format": [],
    "Container / Infra": [],
    "CI / CD": [],
}

# Category assignment for each detected tech
TECH_CATEGORY: dict[str, str] = {
    "Node.js (npm)": "Language / Runtime",
    "TypeScript": "Language / Runtime",
    "Python (pip)": "Language / Runtime",
    "Python (setuptools)": "Language / Runtime",
    "Python (pip/setuptools)": "Language / Runtime",
    "Go": "Language / Runtime",
    "Rust": "Language / Runtime",
    "Java (Maven)": "Language / Runtime",
    "Java (Gradle)": "Language / Runtime",
    "Java (Gradle Kotlin DSL)": "Language / Runtime",
    "Ruby (Bundler)": "Language / Runtime",
    "PHP (Composer)": "Language / Runtime",
    "C/C++ (CMake)": "Language / Runtime",
    "Yarn": "Package Manager",
    "pnpm": "Package Manager",
    "Pipenv": "Package Manager",
    "Poetry": "Package Manager",
    "Next.js": "Framework",
    "Nuxt": "Framework",
    "Astro": "Framework",
    "Svelte": "Framework",
    "Remix": "Framework",
    "Vite": "Build / Bundler",
    "Webpack": "Build / Bundler",
    "Make": "Build / Bundler",
    "Meson": "Build / Bundler",
    "Jest": "Testing",
    "Vitest": "Testing",
    "Cypress": "Testing",
    "Playwright": "Testing",
    "tox (Python)": "Testing",
    "ESLint": "Lint / Format",
    "Prettier": "Lint / Format",
    "pre-commit": "Lint / Format",
    "EditorConfig": "Lint / Format",
    "Docker": "Container / Infra",
    "Docker Compose": "Container / Infra",
    "Terraform": "Container / Infra",
    "Ansible": "Container / Infra",
    "Vagrant": "Container / Infra",
    "Renovate": "Container / Infra",
    "dotenv": "Container / Infra",
    "GitHub Actions": "CI / CD",
    "GitLab CI": "CI / CD",
    "Jenkins": "CI / CD",
    "Travis CI": "CI / CD",
    "CircleCI": "CI / CD",
    "Docusaurus": "Framework",
    "MkDocs": "Framework",
    "Tailwind CSS": "Framework",
    "Ruff": "Lint / Format",
    "Flake8": "Lint / Format",
    "Pylint": "Lint / Format",
    "Mypy": "Lint / Format",
    "Pytest": "Testing",
    "Pyright": "Lint / Format",
    "Coverage": "Testing",
    "Bandit": "Lint / Format",
    "Stylelint": "Lint / Format",
    "Babel": "Build / Bundler",
    "PostCSS": "Build / Bundler",
    "Rollup": "Build / Bundler",
    "rustfmt": "Lint / Format",
    "Clippy": "Lint / Format",
    "golangci-lint": "Lint / Format",
    "RuboCop": "Lint / Format",
    "Rake": "Build / Bundler",
    "Maven Wrapper": "Build / Bundler",
    "Gradle Wrapper": "Build / Bundler",
    "Changelog": "Language / Runtime",
    "Contributing Guide": "Language / Runtime",
    "CODEOWNERS": "Language / Runtime",
    "Security Policy": "Language / Runtime",
    "Bun": "Package Manager",
}


class TechStackAnalyzer(BaseAnalyzer):
    """Detects technology stack from repo file tree and language data."""

    @property
    def analyzer_id(self) -> str:
        return "tech_stack"

    @property
    def display_name(self) -> str:
        return "Tech Stack"

    @property
    def order(self) -> int:
        return 30

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        # ── Languages from GitHub API ─────────────────────────
        languages = context.languages_data or {}
        # Sort by byte count descending
        lang_list = sorted(languages.items(), key=lambda x: x[1], reverse=True)

        # ── Config files from repo tree ───────────────────────
        tree = context.tree_data or []
        file_names = [item.get("path", "") for item in tree]
        file_set = set(file_names)

        # Detect directory-type entries (GitHub tree returns them as type="tree")
        dir_names = {
            item.get("path", "")
            for item in tree
            if item.get("type") == "tree"
        }

        detected_techs: list[str] = []
        detected_files: list[str] = []

        for fname in file_names:
            # Match exact file name
            if fname in LANG_CONFIGS:
                tech_name = LANG_CONFIGS[fname]
                if tech_name not in detected_techs:
                    detected_techs.append(tech_name)
                detected_files.append(fname)
            # Match base name (for files like .eslintrc.json)
            base = fname.split("/")[-1]
            if base in LANG_CONFIGS and fname not in LANG_CONFIGS:
                tech_name = LANG_CONFIGS[base]
                if tech_name not in detected_techs:
                    detected_techs.append(tech_name)
                detected_files.append(fname)

        # Check for directory-based entries
        for dname in dir_names:
            if dname in LANG_CONFIGS:
                tech_name = LANG_CONFIGS[dname]
                if tech_name not in detected_techs:
                    detected_techs.append(tech_name)

        # Check for .github/workflows as a subdirectory
        if any(d.startswith(".github/workflows") or d == ".github" for d in dir_names):
            if "GitHub Actions" not in detected_techs:
                # Check if there are actual workflow files
                has_workflows = any(
                    f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))
                    for f in file_names
                )
                if has_workflows:
                    detected_techs.append("GitHub Actions")

        # ── Category grouping ────────────────────────────────
        groups: dict[str, list[str]] = {}
        for tech in detected_techs:
            cat = TECH_CATEGORY.get(tech, "Other")
            groups.setdefault(cat, []).append(tech)

        # ── Scoring ──────────────────────────────────────────
        category_count = len(groups)
        tech_count = len(detected_techs)
        lang_count = len([l for l, b in lang_list if b > 0])

        # Score: completeness of tech stack definition
        if tech_count >= 12 and category_count >= 6:
            score = min(85 + (tech_count - 12) * 2 + (category_count - 6) * 3, 100)
        elif tech_count >= 8 and category_count >= 4:
            score = 70 + (tech_count - 8) * 3
        elif tech_count >= 5 and category_count >= 3:
            score = 50 + (tech_count - 5) * 5
        elif tech_count >= 3:
            score = 30 + (tech_count - 3) * 8
        elif tech_count >= 1:
            score = 10 + tech_count * 5
        else:
            score = 5  # No config files found, just languages

        grade = self._grade(score)

        # ── Summary ──────────────────────────────────────────
        lang_names = [l for l, b in lang_list[:3]]
        lang_str = ", ".join(lang_names) if lang_names else "unknown"
        summary = f"语言: {lang_str}"
        if detected_techs:
            summary += f" + {len(detected_techs)} tools detected"

        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            severity=self._severity(grade),
            summary=summary,
            score=score,
            details={
                "grade": grade,
                "languages": [{"name": l, "bytes": b} for l, b in lang_list[:8]],
                "detected": detected_techs,
                "categories": groups,
                "config_files": detected_files,
                "total_languages": lang_count,
                "total_tools": tech_count,
            },
            recommendations=self._recommendations(
                grade, lang_count, tech_count, detected_techs
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
        grade: str, lang_count: int, tech_count: int, detected: list[str]
    ) -> list[str]:
        recs = []
        if lang_count == 0:
            recs.append("No languages detected — the repository may be empty.")
        if tech_count == 0:
            recs.append("No build config or package manager files found.")
        if "Docker" not in detected and "Docker Compose" not in detected:
            if tech_count > 0:
                recs.append("No Docker configuration found. Consider containerizing.")
        if not any(t in detected for t in [
            "GitHub Actions", "GitLab CI", "Jenkins", "Travis CI", "CircleCI",
        ]):
            recs.append("No CI/CD pipeline detected. Consider adding automated testing.")
        if not any(t in detected for t in ["ESLint", "Prettier", "pre-commit"]):
            if "Python" not in str(detected):  # Python uses different tools
                recs.append("No linter or formatter detected.")
        return recs
