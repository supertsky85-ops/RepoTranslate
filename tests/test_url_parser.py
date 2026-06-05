"""Tests for the GitHub URL parser."""

import pytest
from app.services.url_parser import parse_github_url, ParsedRepoUrl


class TestParseGitHubUrl:
    """Tests for parse_github_url()."""

    # ── Valid URLs ─────────────────────────────────────────

    @pytest.mark.parametrize("url, expected_owner, expected_repo", [
        ("https://github.com/psf/requests", "psf", "requests"),
        ("https://github.com/tiangolo/fastapi", "tiangolo", "fastapi"),
        ("https://github.com/microsoft/vscode", "microsoft", "vscode"),
        ("https://github.com/owner/repo.git", "owner", "repo"),
        ("https://github.com/owner/repo/", "owner", "repo"),
        ("http://github.com/owner/repo", "owner", "repo"),
        ("git@github.com:owner/repo.git", "owner", "repo"),
        ("https://github.com/org-name/repo_name", "org-name", "repo_name"),
        ("https://github.com/user123/repo-123", "user123", "repo-123"),
        ("https://github.com/a/b", "a", "b"),
    ])
    def test_valid_urls(self, url, expected_owner, expected_repo):
        """Valid GitHub URLs should parse correctly."""
        result = parse_github_url(url)
        assert result.is_valid is True
        assert result.owner == expected_owner
        assert result.repo == expected_repo
        assert result.source == "github"
        assert result.error is None

    def test_url_with_tree_path(self):
        """URLs with /tree/... should still parse owner/repo."""
        result = parse_github_url(
            "https://github.com/owner/repo/tree/main/src"
        )
        assert result.is_valid is True
        assert result.owner == "owner"
        assert result.repo == "repo"

    def test_url_with_blob_path(self):
        """URLs with /blob/... should still parse owner/repo."""
        result = parse_github_url(
            "https://github.com/owner/repo/blob/main/README.md"
        )
        assert result.is_valid is True
        assert result.owner == "owner"
        assert result.repo == "repo"

    # ── Invalid URLs ───────────────────────────────────────

    @pytest.mark.parametrize("url", [
        "",
        "   ",
        "not-a-url",
        "https://google.com",
        "https://github.com",
        "https://github.com/owner",
        "https://github.com/owner/",
        "https://gitlab.com/owner/repo",
    ])
    def test_invalid_urls(self, url):
        """Clearly invalid URLs should fail validation."""
        result = parse_github_url(url)
        assert result.is_valid is False

    # ── Edge cases ─────────────────────────────────────────

    def test_whitespace_trimmed(self):
        """Leading/trailing whitespace should be trimmed."""
        result = parse_github_url("  https://github.com/a/b  ")
        assert result.is_valid is True
        assert result.owner == "a"
        assert result.repo == "b"

    def test_trailing_slash_removed(self):
        """Trailing slash should not affect parsing."""
        result = parse_github_url("https://github.com/a/b/")
        assert result.is_valid is True
        assert result.owner == "a"
        assert result.repo == "b"
