"""Application-wide constants.

GitHub URL patterns, rate limit info, cache TTLs.
"""

import re

# ── GitHub URL parsing ──────────────────────────────────────────

GITHUB_URL_PATTERNS: list[re.Pattern] = [
    # https://github.com/owner/repo (optionally ending with .git)
    re.compile(
        r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
    ),
    # https://github.com/owner/repo/tree/branch/...
    re.compile(
        r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/tree/"
    ),
    # https://github.com/owner/repo/blob/branch/...
    re.compile(
        r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/"
    ),
    # git@github.com:owner/repo.git
    re.compile(
        r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
    ),
]

# ── GitHub API ──────────────────────────────────────────────────

GITHUB_API_BASE = "https://api.github.com"

# Rate limits
UNAUTHENTICATED_RATE_LIMIT = 60  # requests per hour
AUTHENTICATED_RATE_LIMIT = 5000  # requests per hour

# ── Repository name constraints ─────────────────────────────────

# GitHub repository name regex (1-100 chars, alphanumeric + hyphens + underscores + dots)
REPO_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,100}$")

# GitHub owner name constraints (1-39 chars)
OWNER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$")
