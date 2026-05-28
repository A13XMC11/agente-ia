"""Auth endpoints."""
from fastapi import APIRouter, HTTPException, status
import structlog

import app_state as state
from config.modelos import UserLogin, TokenResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/auth/login")
async def login(credentials: UserLogin):
    """
    User login endpoint.

    Args:
        credentials: UserLogin with email and password

    Returns:
        TokenResponse with JWT access token
    """
    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    user = await state.auth_manager.authenticate_user(
        email=credentials.email,
        password=credentials.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = state.auth_manager.create_access_token(
        user_id=user["id"],
        client_id=user.get("client_id", ""),
        role=user.get("role", ""),
        email=user.get("email", ""),
    )

    logger.info("user_login_successful", user_id=user["id"])

    return TokenResponse(access_token=token, token_type="bearer")
