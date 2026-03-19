from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db  # noqa: F401 — re-exported for convenience

# Bearer token extractor — used in auth-protected routes
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns current user if token is valid, else None.
    Use this on routes that support both guest + authenticated access.
    """
    if credentials is None:
        return None

    # Circular import avoided — auth_service imported here
    from app.services.auth_service import verify_token, get_user_by_id

    payload = verify_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    return await get_user_by_id(db, user_id)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns current user or raises 401.
    Use this on protected routes.
    """
    user = await get_current_user_optional(credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
