import logging
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from supabase_auth.errors import AuthApiError, AuthError

from ..core.supabase import get_supabase_client
from ..schemas.auth import UserResponse

logger = logging.getLogger(__name__)

# HTTPBearer with auto_error=False allows structured 401 response handling
security = HTTPBearer(auto_error=False)


def get_supabase() -> Client:
    """FastAPI dependency to obtain the Supabase client instance.

    Raises:
        HTTPException: 503 Service Unavailable if Supabase environment variables are missing.
    """
    try:
        return get_supabase_client()
    except ValueError as exc:
        logger.error(f"Supabase client initialization failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    supabase: Annotated[Client, Depends(get_supabase)],
) -> UserResponse:
    """Validate Bearer token against Supabase Auth and return authenticated user details.

    Args:
        credentials: The Bearer authorization token header credentials.
        supabase: The Supabase client dependency.

    Returns:
        UserResponse: The verified user profile and Supabase auth.users.id.

    Raises:
        HTTPException: 401 Unauthorized if token is missing, invalid, or expired.
        HTTPException: 503 Service Unavailable if Supabase client is not configured.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = user_response.user
        return UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=user.created_at,
            user_metadata=user.user_metadata or {},
        )
    except AuthApiError as exc:
        logger.warning(f"Supabase Auth API error during token validation: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc.message}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as exc:
        logger.warning(f"Supabase Auth error during token validation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.error(f"Supabase configuration error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error validating token: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during authentication verification: {str(exc)}",
        )
