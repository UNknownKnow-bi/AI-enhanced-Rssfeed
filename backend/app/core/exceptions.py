"""
Custom exceptions for the RSS Feed application.
"""

from fastapi import HTTPException, status


class ArticleNotFoundError(HTTPException):
    """Raised when an article is not found."""
    def __init__(self, detail: str = "Article not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedError(HTTPException):
    """Raised when user is not authorized to perform an action."""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationError(HTTPException):
    """Raised when validation fails."""
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
