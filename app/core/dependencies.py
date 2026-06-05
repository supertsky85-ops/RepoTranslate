"""FastAPI dependency injection providers.

Every component that needs to be injected is defined here.
"""

from fastapi import Request

from app.core.config import Settings
from app.services.github_client import GitHubClient


def get_settings(request: Request) -> Settings:
    """Get the application settings from app state."""
    return request.app.state.settings


async def get_github_client(request: Request) -> GitHubClient:
    """Get or create a GitHub API client for the current request.

    The client is stored on app state and reused across requests.
    """
    return request.app.state.github_client
