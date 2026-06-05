"""Custom exception hierarchy for RepoTranslate."""


class RepoTranslateError(Exception):
    """Base exception for all application errors."""


# ── URL parsing ─────────────────────────────────────────────────

class InvalidURLError(RepoTranslateError):
    """Raised when the provided URL is not a valid GitHub repository URL."""

    def __init__(self, url: str, reason: str = ""):
        self.url = url
        self.reason = reason
        msg = f"Invalid GitHub URL: {url}"
        if reason:
            msg += f" — {reason}"
        super().__init__(msg)


# ── GitHub API ──────────────────────────────────────────────────

class GitHubAPIError(RepoTranslateError):
    """Raised when the GitHub API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"GitHub API error ({status_code}): {message}")


class RateLimitExceededError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_at: str = ""):
        self.reset_at = reset_at
        msg = "GitHub API rate limit exceeded."
        if reset_at:
            msg += f" Resets at: {reset_at}"
        super().__init__(status_code=429, message=msg)


class RepoNotFoundError(GitHubAPIError):
    """Raised when a repository is not found (404)."""

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        super().__init__(
            status_code=404,
            message=f"Repository not found: {owner}/{repo}",
        )
