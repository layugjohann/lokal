import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from supabase import Client
from supabase_auth.errors import AuthApiError, AuthError

from ...deps import get_current_user, get_supabase, security
from ....schemas.auth import (
    AuthResponseSchema,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    SessionResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with email and password in Supabase Auth.",
)
async def register(
    payload: RegisterRequest,
    supabase: Annotated[Client, Depends(get_supabase)],
):
    """Register a new user using email and password."""
    try:
        auth_response = supabase.auth.sign_up(
            {"email": payload.email, "password": payload.password}
        )
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed. No user record was created.",
            )

        user_data = UserResponse(
            id=str(auth_response.user.id),
            email=auth_response.user.email,
            created_at=auth_response.user.created_at,
            user_metadata=auth_response.user.user_metadata or {},
        )

        session_data = None
        if auth_response.session:
            session_data = SessionResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type=auth_response.session.token_type or "bearer",
                expires_in=auth_response.session.expires_in,
                expires_at=auth_response.session.expires_at,
            )

        message = (
            "Registration successful."
            if session_data
            else "Registration successful. Please check your email to verify your account."
        )

        return AuthResponseSchema(
            user=user_data,
            session=session_data,
            message=message,
        )
    except AuthApiError as exc:
        logger.warning(f"Supabase registration AuthApiError: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    except AuthError as exc:
        logger.warning(f"Supabase registration AuthError: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
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
        logger.error(f"Unexpected registration error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during registration: {str(exc)}",
        )


@router.post(
    "/login",
    response_model=AuthResponseSchema,
    summary="Authenticate user",
    description="Authenticates an existing user using email and password and returns session tokens.",
)
async def login(
    payload: LoginRequest,
    supabase: Annotated[Client, Depends(get_supabase)],
):
    """Authenticate an existing user with email and password."""
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        user_data = UserResponse(
            id=str(auth_response.user.id),
            email=auth_response.user.email,
            created_at=auth_response.user.created_at,
            user_metadata=auth_response.user.user_metadata or {},
        )

        session_data = None
        if auth_response.session:
            session_data = SessionResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type=auth_response.session.token_type or "bearer",
                expires_in=auth_response.session.expires_in,
                expires_at=auth_response.session.expires_at,
            )

        return AuthResponseSchema(
            user=user_data,
            session=session_data,
            message="Authentication successful.",
        )
    except AuthApiError as exc:
        logger.warning(f"Supabase login AuthApiError: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message or "Invalid email or password.",
        )
    except AuthError as exc:
        logger.warning(f"Supabase login AuthError: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
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
        logger.error(f"Unexpected login error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during login: {str(exc)}",
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Sign out user",
    description="Invalidates the user's authenticated session in Supabase Auth.",
)
async def logout(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    supabase: Annotated[Client, Depends(get_supabase)],
):
    """Sign out the current authenticated user and invalidate session."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Token-scoped non-admin revocation using the caller's JWT
        supabase.auth._request(
            "POST",
            "logout",
            jwt=credentials.credentials,
            no_resolve_json=True,
        )
        return MessageResponse(message="Successfully signed out.")
    except AuthApiError as exc:
        logger.warning(f"Supabase logout AuthApiError: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {exc.message}",
        )
    except AuthError as exc:
        logger.warning(f"Supabase logout AuthError: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(exc)}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected logout error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during logout: {str(exc)}",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Returns the profile and Supabase auth.users.id of the currently authenticated user.",
)
async def get_me(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Return the verified user details for the caller's active session."""
    return current_user
