"""Auth endpoints."""
from fastapi import APIRouter, HTTPException, Request, status
import structlog

import app_state as state
from config.modelos import UserLogin, TokenResponse

logger = structlog.get_logger(__name__)

router = APIRouter()

# IP-level limits for the login endpoint:
# 10 attempts per IP per 10 minutes — stops distributed credential stuffing
# while comfortably allowing any legitimate user.
_LOGIN_IP_LIMIT = 10
_LOGIN_IP_WINDOW = 600  # 10 minutes


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, honouring the first entry in X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/auth/login")
async def login(credentials: UserLogin, request: Request):
    """
    User login endpoint.

    Args:
        credentials: UserLogin with email and password

    Returns:
        TokenResponse with JWT access token
    """
    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    # IP-level rate limit: guards against credential stuffing across different
    # email addresses from the same source IP.
    if state.rate_limiter:
        ip = _get_client_ip(request)
        allowed, info = await state.rate_limiter.check_ip_rate_limit(
            ip=ip,
            endpoint="login",
            limit=_LOGIN_IP_LIMIT,
            window_seconds=_LOGIN_IP_WINDOW,
        )
        if not allowed:
            logger.warning(
                "login_ip_rate_limit_exceeded",
                ip=ip,
                current=info.get("current"),
                limit=info.get("limit"),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(_LOGIN_IP_WINDOW)},
            )

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

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=state.auth_manager.jwt_expiration_hours * 3600,
    )
