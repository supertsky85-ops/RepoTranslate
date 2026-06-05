"""Web page routes — server-rendered HTML with Jinja2 templates.

Starlette 1.2+ API: TemplateResponse(request, name, context)
Context does NOT need "request" key — it's added automatically.
"""

import asyncio
import logging
import os

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.dependencies import get_github_client
from app.services.url_parser import parse_github_url
from app.core.exceptions import (
    RepoNotFoundError,
    GitHubAPIError,
    RateLimitExceededError,
)
from app.models.analysis import AnalysisContext
from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.basic_stats import BasicStatsAnalyzer
from app.analyzers.readme_summary import ReadmeAnalyzer
from app.analyzers.tech_stack import TechStackAnalyzer
from app.analyzers.architecture import ArchitectureAnalyzer
from app.analyzers.code_quality import CodeQualityAnalyzer
from app.analyzers.contributors import ContributorAnalyzer
from app.analyzers.roadmap import RoadmapAnalyzer
from app.services.token_manager import save_token, mask_token, load_token
from app.services.github_client import GitHubClient
from app.services.report_renderer import render_report
from app.services.path_helper import get_base_dir

logger = logging.getLogger(__name__)

web_router = APIRouter()

templates = Jinja2Templates(directory=os.path.join(get_base_dir(), "app/web/templates"))

# ── Analyzer setup ──────────────────────────────────────────

_analyzer_registry = AnalyzerRegistry()
_analyzer_registry.register(BasicStatsAnalyzer())
_analyzer_registry.register(ReadmeAnalyzer())
_analyzer_registry.register(TechStackAnalyzer())
_analyzer_registry.register(ArchitectureAnalyzer())
_analyzer_registry.register(CodeQualityAnalyzer())
_analyzer_registry.register(ContributorAnalyzer())
_analyzer_registry.register(RoadmapAnalyzer())


@web_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page with the URL input form."""
    return templates.TemplateResponse(request, "index.html.j2")


@web_router.post("/analyze", response_class=HTMLResponse)
async def analyze_repo(
    request: Request,
    github_url: str = Form(...),
):
    """Handle the analyze form submission.

    1. Parse and validate the URL
    2. Fetch repo metadata from GitHub API
    3. Run all registered analyzers
    4. Return the repo card + analysis results
    """
    # Step 1: Validate URL
    parsed = parse_github_url(github_url)

    if not parsed.is_valid:
        return templates.TemplateResponse(
            request,
            "partials/error_banner.html.j2",
            {"error": parsed.error or "Invalid GitHub URL."},
            status_code=400,
        )

    # Step 2: Fetch repo data + supplementary data
    client = await get_github_client(request)

    try:
        repo_data = await client.get_repo(parsed.owner, parsed.repo)
    except RepoNotFoundError:
        return templates.TemplateResponse(
            request,
            "partials/error_banner.html.j2",
            {
                "error": f"Repository not found: {parsed.full_name}",
                "detail": "Check the URL and try again. The repository may be private or deleted.",
            },
            status_code=404,
        )
    except RateLimitExceededError:
        return templates.TemplateResponse(
            request,
            "partials/error_banner.html.j2",
            {
                "error": "GitHub API rate limit exceeded.",
                "detail": (
                    "Unauthenticated requests are limited to 60 per hour. "
                    "Add a GitHub token in Settings for 5000 requests/hour."
                ),
            },
            status_code=429,
        )
    except GitHubAPIError as e:
        return templates.TemplateResponse(
            request,
            "partials/error_banner.html.j2",
            {"error": f"GitHub API error: {e}"},
            status_code=502,
        )

    # Fetch essential data in parallel (keep it fast — 3 calls)
    branch = repo_data.get("default_branch", "main")
    readme_data, langs, tree = await asyncio.gather(
        client.get_readme(parsed.owner, parsed.repo),
        client.get_languages(parsed.owner, parsed.repo),
        client.get_repo_tree(parsed.owner, parsed.repo, branch, recursive=True),
        return_exceptions=True,
    )
    if isinstance(readme_data, BaseException):
        readme_data = None
    if isinstance(langs, BaseException):
        langs = {}
    if isinstance(tree, BaseException):
        tree = []

    # Secondary data — fire-and-forget with short timeout, don't block
    commits_data: list = []
    issues_data: list = []
    contribs: list = []
    releases_data: list = []
    try:
        (
            commits_data, issues_data, contribs, releases_data,
        ) = await asyncio.wait_for(
            asyncio.gather(
                client.get_commits(parsed.owner, parsed.repo),
                client.get_issues(parsed.owner, parsed.repo),
                client.get_contributors(parsed.owner, parsed.repo),
                client.get_releases(parsed.owner, parsed.repo),
                return_exceptions=True,
            ),
            timeout=8.0,  # 8 second timeout for secondary data
        )
        if isinstance(commits_data, BaseException):
            commits_data = []
        if isinstance(issues_data, BaseException):
            issues_data = []
        if isinstance(contribs, BaseException):
            contribs = []
        if isinstance(releases_data, BaseException):
            releases_data = []
    except (asyncio.TimeoutError, Exception):
        logger.info(f"Secondary data fetch skipped (timeout) for {parsed.full_name}")

    # Step 3: Run analyzers
    context = AnalysisContext(
        owner=parsed.owner,
        repo=parsed.repo,
        repo_data=repo_data,
        readme_data=readme_data,
        languages_data=langs,
        tree_data=tree,
        commits_data=commits_data,
        issues_data=issues_data,
        contributors_data=contribs,
        releases_data=releases_data,
    )
    analysis_result = await _analyzer_registry.run_all(context)

    # Step 4: Render report (pure Python, no templates)
    auth_status = "authenticated" if request.app.state.settings.is_authenticated else "unauthenticated"
    html = render_report(analysis_result, repo_data, auth_status)
    return HTMLResponse(content=html)


# ── Settings routes ──────────────────────────────────────────

@web_router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page for token management."""
    settings = request.app.state.settings
    token = settings.github_token or load_token()
    client = await get_github_client(request)
    rate_limit = client.rate_limit.summary()

    return templates.TemplateResponse(
        request,
        "settings.html.j2",
        {
            "token_configured": bool(token),
            "token_masked": mask_token(token),
            "rate_limit_summary": rate_limit,
            "analyzer_count": len(_analyzer_registry.get_all()),
        },
    )


@web_router.post("/settings/token", response_class=HTMLResponse)
async def save_token_route(
    request: Request,
    token: str = Form(""),
):
    """Save a GitHub personal access token."""
    if token.strip():
        save_token(token.strip())
        request.app.state.settings.github_token = token.strip()
        await request.app.state.github_client.close()
        request.app.state.github_client = GitHubClient(request.app.state.settings)
        status_html = (
            '<div class="token-ok">Token saved! '
            f'{request.app.state.github_client.rate_limit.summary()}</div>'
        )
    else:
        status_html = '<div class="token-warn">Please enter a valid token.</div>'

    return HTMLResponse(content=status_html)
