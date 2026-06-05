"""Pydantic models for GitHub API data.

These models represent the shape of data returned by the GitHub REST API.
They use `populate_by_name` so we can use Pythonic field names
while accepting GitHub's JSON keys.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class License(BaseModel):
    """Repository license information."""

    key: str = ""
    name: str = ""
    spdx_id: str | None = None
    url: str | None = None

    model_config = {"populate_by_name": True}


class RepoInfo(BaseModel):
    """Core repository metadata."""

    full_name: str
    description: str | None = None
    stars: int = Field(default=0, alias="stargazers_count")
    forks: int = Field(default=0, alias="forks_count")
    open_issues: int = Field(default=0, alias="open_issues_count")
    watchers: int = Field(default=0, alias="watchers_count")
    language: str | None = None
    license: License | None = Field(default=None, alias="license")
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime | None = None
    default_branch: str = "main"
    topics: list[str] = Field(default_factory=list)
    html_url: str = ""
    homepage: str | None = None
    size_kb: int = Field(default=0, alias="size")
    archived: bool = False
    fork: bool = False

    model_config = {"populate_by_name": True}

    @field_validator("topics", mode="before")
    @classmethod
    def ensure_topics_list(cls, v: Any) -> list[str]:
        """Handle None or missing topics."""
        if v is None:
            return []
        return v

    @field_validator("license", mode="before")
    @classmethod
    def ensure_license(cls, v: Any) -> License | None:
        """Handle null license (GitHub returns `"license": null` for no license)."""
        if v is None:
            return License(key="none", name="No License")
        if isinstance(v, dict):
            return License(**v)
        return v

    @property
    def age_days(self) -> int:
        """Age of the repository in days."""
        return (datetime.now(tz=self.created_at.tzinfo) - self.created_at).days
