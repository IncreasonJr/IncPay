import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_supabase_client

logger = logging.getLogger(__name__)

# auto_error=False allows us to return a consistent 401 with custom error message
security = HTTPBearer(auto_error=False)


def verify_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    FastAPI dependency to verify an incoming Bearer token against Supabase Auth.
    Ensures that the caller is an authenticated user (admin).
    Raises HTTPException(401, "Not authenticated") if token is missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized when validating auth token.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )

    try:
        # Validate JWT and retrieve user from Supabase Auth
        response = client.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return response.user
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Failed to authenticate token with Supabase: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
