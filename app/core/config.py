"""Application configuration via pydantic-settings.

Reads from .env file, environment variables, and data/token.txt.
"""

from pydantic_settings import BaseSettings
from app.services.token_manager import load_token


class Settings(BaseSettings):
    """Central configuration for the RepoTranslate application."""

    # GitHub
    github_token: str = ""

    # Cache
    cache_ttl_hours: int = 1
    cache_dir: str = "data"
    db_path: str = "data/cache.db"

    # Server
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # Rate limiting
    rate_limit_buffer: int = 10
    request_timeout: float = 30.0
    max_retries: int = 3

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fall back to token file if no env token
        if not self.github_token:
            file_token = load_token()
            if file_token:
                self.github_token = file_token

    @property
    def is_authenticated(self) -> bool:
        """Check if a GitHub token is configured."""
        return bool(self.github_token and self.github_token.strip())

    @property
    def cache_ttl_seconds(self) -> int:
        """Cache TTL in seconds (derived from hours)."""
        return self.cache_ttl_hours * 3600
