"""Shared test fixtures for RepoTranslate."""

import pytest
from fastapi.testclient import TestClient

# Ensure the app directory is importable
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from app.main import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_repo_data():
    """Sample GitHub API response for a repository."""
    return {
        "full_name": "test-owner/test-repo",
        "description": "A test repository",
        "stargazers_count": 100,
        "forks_count": 20,
        "open_issues_count": 5,
        "watchers_count": 100,
        "language": "Python",
        "license": {
            "key": "mit",
            "name": "MIT License",
        },
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2024-06-01T00:00:00Z",
        "pushed_at": "2024-06-01T00:00:00Z",
        "default_branch": "main",
        "topics": ["python", "web"],
        "html_url": "https://github.com/test-owner/test-repo",
        "homepage": None,
        "size": 1024,
        "archived": False,
        "fork": False,
    }
