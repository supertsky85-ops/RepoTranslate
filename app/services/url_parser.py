"""GitHub URL parser and validator.

Supports multiple GitHub URL formats:
- https://github.com/owner/repo
- https://github.com/owner/repo.git
- https://github.com/owner/repo/tree/branch/...
- https://github.com/owner/repo/blob/branch/...
- git@github.com:owner/repo.git
"""

from dataclasses import dataclass, field

from app.core.constants import GITHUB_URL_PATTERNS, OWNER_NAME_PATTERN, REPO_NAME_PATTERN


@dataclass
class ParsedRepoUrl:
    """Result of parsing a GitHub repository URL."""

    owner: str
    repo: str
    source: str  # "github"
    is_valid: bool
    error: str | None = None

    @property
    def full_name(self) -> str:
        """Return 'owner/repo' string."""
        return f"{self.owner}/{self.repo}"


def parse_github_url(url: str) -> ParsedRepoUrl:
    """Parse and validate a GitHub repository URL.

    Args:
        url: A raw URL string (may contain whitespace, trailing slashes, etc.)

    Returns:
        ParsedRepoUrl with owner, repo, and validation status.

    Examples:
        >>> parse_github_url("https://github.com/psf/requests")
        ParsedRepoUrl(owner="psf", repo="requests", source="github", is_valid=True)

        >>> parse_github_url("not-a-url")
        ParsedRepoUrl(owner="", repo="", source="unknown", is_valid=False, error=...)
    """
    if not url or not url.strip():
        return ParsedRepoUrl(
            owner="", repo="", source="unknown", is_valid=False,
            error="URL cannot be empty.",
        )

    url = url.strip().rstrip("/")

    for pattern in GITHUB_URL_PATTERNS:
        match = pattern.match(url)
        if match:
            owner = match.group("owner")
            repo = match.group("repo")

            # Remove .git suffix from repo name if present
            if repo.endswith(".git"):
                repo = repo[:-4]

            # Validate owner name format
            if not owner or not OWNER_NAME_PATTERN.match(owner):
                return ParsedRepoUrl(
                    owner=owner or "",
                    repo=repo or "",
                    source="github",
                    is_valid=False,
                    error=f"Invalid GitHub owner name: '{owner}'.",
                )

            # Validate repo name format
            if not repo or not REPO_NAME_PATTERN.match(repo):
                return ParsedRepoUrl(
                    owner=owner,
                    repo=repo or "",
                    source="github",
                    is_valid=False,
                    error=f"Invalid GitHub repository name: '{repo}'.",
                )

            return ParsedRepoUrl(
                owner=owner,
                repo=repo,
                source="github",
                is_valid=True,
            )

    # No pattern matched
    return ParsedRepoUrl(
        owner="", repo="", source="unknown", is_valid=False,
        error=f"Not a valid GitHub repository URL. Expected format: "
              f"https://github.com/owner/repo",
    )
