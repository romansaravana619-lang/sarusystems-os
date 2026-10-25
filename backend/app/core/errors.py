from fastapi import HTTPException, status


class DomainError(Exception):
    """Base exception for business/domain errors."""


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
