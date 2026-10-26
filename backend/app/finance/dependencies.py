"""Finance permission helpers are kept small so the router can be wired to the
project's existing authenticated-user dependency without duplicating policy."""

from fastapi import HTTPException


def require_company_user(user):
    if not getattr(user, "company_id", None) or not getattr(user, "id", None):
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
