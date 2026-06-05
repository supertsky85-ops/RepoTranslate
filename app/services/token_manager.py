"""GitHub token management.

Stores token in a local file (data/token.txt) with restricted access.
"""

import os
import logging

logger = logging.getLogger(__name__)

TOKEN_FILE = "data/token.txt"


def load_token() -> str:
    """Load token from file or environment variable.

    Priority: GITHUB_TOKEN env var > data/token.txt
    """
    env_token = os.getenv("GITHUB_TOKEN", "")
    if env_token:
        return env_token

    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                return f.read().strip()
    except OSError as e:
        logger.warning(f"Cannot read token file: {e}")

    return ""


def save_token(token: str) -> bool:
    """Save token to file (and set env var for current session)."""
    token = token.strip()
    if not token:
        return False

    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        # Also set for current session
        os.environ["GITHUB_TOKEN"] = token
        logger.info("GitHub token saved.")
        return True
    except OSError as e:
        logger.error(f"Failed to save token: {e}")
        return False


def mask_token(token: str) -> str:
    """Mask a token for display (show first 4 + last 4 chars)."""
    if not token or len(token) < 8:
        return ""
    return f"{token[:4]}...{token[-4:]}"
