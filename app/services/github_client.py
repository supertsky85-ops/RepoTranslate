"""Async GitHub API client built on httpx.

Handles:
- Authentication (token or unauthenticated)
- Rate limit tracking (X-RateLimit-Remaining / X-RateLimit-Reset headers)
- Conditional requests (ETag / If-None-Match for 304 caching)
- Error translation (HTTP errors → custom exceptions)
"""

import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.core.constants import GITHUB_API_BASE
from app.core.exceptions import (
    GitHubAPIError,
    RateLimitExceededError,
    RepoNotFoundError,
)

logger = logging.getLogger(__name__)


class RateLimitTracker:
    """Tracks GitHub API rate limit state from response headers."""

    def __init__(self):
        self.remaining: int | None = None
        self.limit: int | None = None
        self.reset_at: int | None = None  # Unix timestamp

    def update(self, headers: httpx.Headers) -> None:
        """Update tracker from response headers."""
        remaining = headers.get("X-RateLimit-Remaining")
        limit = headers.get("X-RateLimit-Limit")
        reset_at = headers.get("X-RateLimit-Reset")

        if remaining is not None:
            self.remaining = int(remaining)
        if limit is not None:
            self.limit = int(limit)
        if reset_at is not None:
            self.reset_at = int(reset_at)

    @property
    def is_exhausted(self) -> bool:
        """Check if rate limit has been reached."""
        return self.remaining is not None and self.remaining <= 0

    @property
    def is_low(self) -> bool:
        """Check if rate limit is close to exhausted."""
        return self.remaining is not None and self.remaining < 10

    def summary(self) -> str:
        """Human-readable rate limit status."""
        if self.remaining is None:
            return "Unknown"
        return f"{self.remaining}/{self.limit or '?'} remaining"


class GitHubClient:
    """Async GitHub REST API client.

    Usage:
        settings = Settings()
        client = GitHubClient(settings)
        repo = await client.get_repo("psf", "requests")
        await client.close()
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.rate_limit = RateLimitTracker()

        headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoTranslate/0.1.0",
        }

        if settings.is_authenticated:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers=headers,
            timeout=httpx.Timeout(settings.request_timeout),
        )

    # ── Public API methods ──────────────────────────────────────

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository metadata.

        GET /repos/{owner}/{repo}

        Returns raw dict — caller transforms to Pydantic models.
        """
        return await self._get(f"/repos/{owner}/{repo}")

    async def get_readme(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch the repository's README file.

        GET /repos/{owner}/{repo}/readme
        """
        return await self._get(f"/repos/{owner}/{repo}/readme")

    async def get_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Fetch language breakdown (bytes per language).

        GET /repos/{owner}/{repo}/languages
        """
        return await self._get(f"/repos/{owner}/{repo}/languages")

    async def get_repo_tree(
        self, owner: str, repo: str, branch: str = "main", recursive: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch the repository's git tree (top-level by default).

        GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1

        Returns list of {path, type, size, url} dicts.
        """
        params = ""
        if recursive:
            params = "?recursive=1"
        result = await self._get(
            f"/repos/{owner}/{repo}/git/trees/{branch}{params}"
        )
        return result.get("tree", [])

    async def get_commits(
        self, owner: str, repo: str, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch recent commits.

        GET /repos/{owner}/{repo}/commits?per_page=100
        """
        return await self._get(
            f"/repos/{owner}/{repo}/commits?per_page={per_page}"
        )

    async def get_releases(
        self, owner: str, repo: str, per_page: int = 20
    ) -> list[dict[str, Any]]:
        """Fetch recent releases.

        GET /repos/{owner}/{repo}/releases?per_page=20
        """
        return await self._get(
            f"/repos/{owner}/{repo}/releases?per_page={per_page}"
        )

    async def get_contributors(
        self, owner: str, repo: str, per_page: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch top contributors.

        GET /repos/{owner}/{repo}/contributors?per_page=30
        """
        return await self._get(
            f"/repos/{owner}/{repo}/contributors?per_page={per_page}"
        )

    async def get_issues(
        self, owner: str, repo: str, state: str = "all", per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch recent issues (excludes pull requests).

        GET /repos/{owner}/{repo}/issues?state=all&per_page=100
        """
        return await self._get(
            f"/repos/{owner}/{repo}/issues?state={state}&per_page={per_page}&filter=all"
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ── Internal HTTP helpers ───────────────────────────────────

    async def _get(self, path: str) -> Any:
        """Make a GET request with error handling and rate limit tracking."""
        try:
            response = await self._client.get(path)
        except httpx.TimeoutException:
            raise GitHubAPIError(
                status_code=0,
                message=f"Request timed out: {path}",
            )
        except httpx.RequestError as e:
            raise GitHubAPIError(
                status_code=0,
                message=f"Request failed: {e}",
            )

        # Update rate limit tracking from response headers
        self.rate_limit.update(response.headers)

        # Handle error responses
        if response.status_code == 404:
            # Extract owner/repo from path for better error message
            parts = path.strip("/").split("/")
            if len(parts) >= 2:
                raise RepoNotFoundError(owner=parts[0], repo=parts[1])
            raise GitHubAPIError(status_code=404, message=f"Not found: {path}")

        if response.status_code == 403 and self.rate_limit.remaining == 0:
            raise RateLimitExceededError(
                reset_at=str(self.rate_limit.reset_at or ""),
            )

        if response.status_code >= 400:
            raise GitHubAPIError(
                status_code=response.status_code,
                message=response.json().get("message", response.text),
            )

        return response.json()

    async def _get_raw(self, path: str) -> str:
        """Make a GET request and return raw text (for README content, etc.)."""
        response = await self._client.get(path)
        response.raise_for_status()
        return response.text
