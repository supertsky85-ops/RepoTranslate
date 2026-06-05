"""Request models for API endpoints."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for the analyze endpoint."""

    github_url: str = Field(
        ...,
        description="GitHub repository URL to analyze",
        examples=["https://github.com/psf/requests"],
    )


class TokenRequest(BaseModel):
    """Request body for storing a GitHub token."""

    token: str = Field(
        ...,
        min_length=10,
        description="GitHub Personal Access Token",
    )
