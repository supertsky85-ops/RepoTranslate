"""RepoTranslate — GitHub Repository Analysis Tool.

FastAPI application factory and entry point.

Usage:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings
from app.services.github_client import GitHubClient
from app.services.path_helper import get_base_dir

# ── Logging ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Application lifecycle ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    settings: Settings = app.state.settings
    logger.info(f"Starting RepoTranslate v0.1.0")

    # Ensure data directory exists
    os.makedirs(settings.cache_dir, exist_ok=True)

    # Initialize GitHub client (reused across requests)
    app.state.github_client = GitHubClient(settings)
    auth_status = "authenticated" if settings.is_authenticated else "unauthenticated"
    logger.info(
        f"GitHub client initialized ({auth_status}, "
        f"rate limit: {5000 if settings.is_authenticated else 60}/hr)"
    )

    yield

    # Shutdown
    logger.info("Shutting down...")
    await app.state.github_client.close()
    logger.info("GitHub client closed.")


# ── App factory ────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="RepoTranslate",
        description="Analyze GitHub repositories — tech stack, architecture, quality, and more.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store settings for dependency injection
    app.state.settings = settings

    # Mount static files (CSS, JS)
    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(get_base_dir(), "app/web/static")),
        name="static",
    )

    # Register routers
    from app.api.router import api_router
    from app.web.router import web_router

    app.include_router(web_router)           # Page routes: /, /analyze
    app.include_router(api_router, prefix="/api")  # API routes: /api/health, /api/repo/...

    return app


# ── Module-level app instance (for uvicorn) ────────────────────

app = create_app()
