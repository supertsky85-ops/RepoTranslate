"""API router aggregating all API route modules."""

from fastapi import APIRouter, Request

from app.services.url_parser import parse_github_url
from app.core.dependencies import get_github_client, get_settings
from app.core.exceptions import RepoNotFoundError, GitHubAPIError, RateLimitExceededError

api_router = APIRouter()


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@api_router.post("/repo/validate")
async def validate_url(payload: dict[str, str]):
    """Validate a GitHub URL and return the parsed owner/repo.

    Request body: {"url": "https://github.com/owner/repo"}
    """
    url = payload.get("url", "")
    result = parse_github_url(url)
    return {
        "valid": result.is_valid,
        "owner": result.owner,
        "repo": result.repo,
        "source": result.source,
        "error": result.error,
    }


@api_router.get("/repo/{owner}/{repo}")
async def get_repo_info(
    owner: str,
    repo: str,
    request: Request,
):
    """Fetch repository metadata from GitHub API.

    Returns the raw repository data as JSON.
    """
    client = await get_github_client(request)
    try:
        data = await client.get_repo(owner, repo)
        return data
    except RepoNotFoundError:
        return {"error": f"Repository not found: {owner}/{repo}"}
    except GitHubAPIError as e:
        return {"error": str(e)}


@api_router.get("/rate-limit")
async def get_rate_limit(request: Request):
    """Get current GitHub API rate limit status."""
    client = await get_github_client(request)
    return {
        "remaining": client.rate_limit.remaining,
        "limit": client.rate_limit.limit,
        "summary": client.rate_limit.summary(),
    }
