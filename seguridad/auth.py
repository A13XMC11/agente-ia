"""
Authentication and authorization: JWT tokens, roles, permissions.

Manages:
- User authentication (email + password)
- JWT token generation and validation
- Role-based access control (RBAC)
- Client isolation via JWT claims
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Any
import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from supabase import create_client, Client

from config.modelos import UserLogin, TokenResponse, RoleEnum


logger = structlog.get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthManager:
    """
    Manages authentication, token generation, and authorization.

    JWT claims include:
    - user_id: Unique user identifier
    - client_id: Business customer they belong to
    - role: One of SUPER_ADMIN, ADMIN, OPERADOR
    - email: User email
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        jwt_secret: str | None = None,
        jwt_algorithm: str = "HS256",
        jwt_expiration_hours: int = 24,
    ):
        """
        Initialize auth manager.

        Args:
            supabase_url: Supabase project URL (from env if not provided)
            supabase_key: Supabase public key (from env if not provided)
            jwt_secret: JWT signing secret (from env if not provided)
            jwt_algorithm: JWT algorithm (default: HS256)
            jwt_expiration_hours: Token expiration in hours
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY", "")
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET_KEY", "")
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expiration_hours = jwt_expiration_hours

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        logger.info("auth_manager_initialized")

    def hash_password(self, password: str) -> str:
        """
        Hash a plain password using bcrypt.

        Args:
            password: Plain password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """
        Verify plain password against hash.

        Args:
            plain: Plain password
            hashed: Hashed password from database

        Returns:
            True if password matches
        """
        return pwd_context.verify(plain, hashed)

    async def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> Optional[dict[str, Any]]:
        """
        Authenticate user by email and password.

        Returns user data if successful, None otherwise.

        Args:
            email: User email
            password: Plain password

        Returns:
            User dict with id, email, client_id, role; or None
        """
        try:
            # Query user by email
            response = self.supabase.table("users").select("*").eq(
                "email", email.lower()
            ).execute()

            if not response.data:
                logger.warning("user_not_found", email=email)
                return None

            user = response.data[0]

            # Verify password
            if not self.verify_password(password, user.get("password_hash", "")):
                logger.warning("invalid_password", email=email)
                return None

            logger.info("user_authenticated", user_id=user["id"], email=email)

            return {
                "id": user["id"],
                "email": user["email"],
                "client_id": user.get("client_id"),
                "role": user.get("role", RoleEnum.OPERADOR.value),
                "full_name": user.get("full_name"),
            }

        except Exception as e:
            logger.error(
                "authentication_error",
                email=email,
                error=str(e),
                exc_info=True,
            )
            return None

    def create_access_token(
        self,
        user_id: str,
        client_id: Optional[str],
        role: str,
        email: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User ID
            client_id: Client ID (may be None for SUPER_ADMIN)
            role: User role
            email: User email
            expires_delta: Custom expiration time

        Returns:
            JWT token string
        """
        if not expires_delta:
            expires_delta = timedelta(hours=self.jwt_expiration_hours)

        now = datetime.utcnow()
        expires = now + expires_delta

        claims = {
            "sub": user_id,
            "user_id": user_id,
            "client_id": client_id,
            "role": role,
            "email": email,
            "iat": now,
            "exp": expires,
        }

        token = jwt.encode(
            claims,
            self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )

        logger.info(
            "token_created",
            user_id=user_id,
            role=role,
            expires_at=expires.isoformat(),
        )

        return token

    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify JWT token and return claims.

        Args:
            token: JWT token string

        Returns:
            Token claims dict

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )

            user_id = payload.get("user_id")
            if not user_id:
                raise JWTError("Invalid token: no user_id")

            logger.info("token_verified", user_id=user_id)

            return payload

        except JWTError as e:
            logger.warning("token_verification_failed", error=str(e))
            raise

    async def login(self, credentials: UserLogin) -> TokenResponse:
        """
        Authenticate user and return access token.

        Args:
            credentials: Email and password

        Returns:
            Token response with access_token and expiration

        Raises:
            ValueError: If authentication fails
        """
        user = await self.authenticate_user(credentials.email, credentials.password)

        if not user:
            raise ValueError("Invalid email or password")

        token = self.create_access_token(
            user_id=user["id"],
            client_id=user.get("client_id"),
            role=user["role"],
            email=user["email"],
        )

        return TokenResponse(
            access_token=token,
            expires_in=self.jwt_expiration_hours * 3600,
        )

    def requires_role(self, required_roles: list[RoleEnum]) -> callable:
        """
        Create a dependency for FastAPI route protection.

        Usage:
            @app.get("/admin")
            async def admin_endpoint(user = Depends(auth.requires_role([RoleEnum.ADMIN]))):
                ...

        Args:
            required_roles: List of allowed roles

        Returns:
            FastAPI dependency function
        """

        async def verify_role(token: str) -> dict[str, Any]:
            try:
                claims = await self.verify_token(token)
                user_role = claims.get("role")

                if user_role not in [r.value for r in required_roles]:
                    raise PermissionError(f"Role {user_role} not authorized")

                return claims

            except JWTError as e:
                raise ValueError(f"Invalid token: {str(e)}")

        return verify_role

    def requires_client_isolation(self) -> callable:
        """
        Create a dependency that enforces client isolation.

        Ensures user can only access resources for their client_id.

        Usage:
            @app.get("/api/clients/{client_id}/data")
            async def get_data(
                client_id: str,
                user = Depends(auth.requires_client_isolation())
            ):
                ...

        Returns:
            FastAPI dependency function
        """

        async def verify_client_access(
            token: str,
            requested_client_id: str,
        ) -> dict[str, Any]:
            try:
                claims = await self.verify_token(token)
                user_client_id = claims.get("client_id")
                user_role = claims.get("role")

                # SUPER_ADMIN can access any client
                if user_role == RoleEnum.SUPER_ADMIN.value:
                    return claims

                # Regular users must match client_id
                if user_client_id != requested_client_id:
                    raise PermissionError(
                        f"Client {user_client_id} cannot access {requested_client_id}"
                    )

                return claims

            except JWTError as e:
                raise ValueError(f"Invalid token: {str(e)}")

        return verify_client_access

    async def refresh_token(self, token: str) -> TokenResponse:
        """
        Refresh an access token (extend expiration).

        Args:
            token: Current access token

        Returns:
            New token response

        Raises:
            JWTError: If token is invalid or expired
        """
        claims = await self.verify_token(token)

        new_token = self.create_access_token(
            user_id=claims["user_id"],
            client_id=claims.get("client_id"),
            role=claims["role"],
            email=claims["email"],
        )

        logger.info("token_refreshed", user_id=claims["user_id"])

        return TokenResponse(
            access_token=new_token,
            expires_in=self.jwt_expiration_hours * 3600,
        )

    async def validate_api_key(self, api_key: str) -> Optional[dict[str, Any]]:
        """
        Validate API key for programmatic access.

        Args:
            api_key: API key string

        Returns:
            Client info if valid, None otherwise
        """
        try:
            response = self.supabase.table("api_keys").select("*").eq(
                "key", api_key
            ).eq("active", True).execute()

            if not response.data:
                logger.warning("invalid_api_key")
                return None

            api_key_record = response.data[0]

            # Check if expired
            if api_key_record.get("expires_at"):
                expires = datetime.fromisoformat(api_key_record["expires_at"])
                if expires < datetime.utcnow():
                    logger.warning("expired_api_key")
                    return None

            logger.info("api_key_validated", client_id=api_key_record["client_id"])

            return {
                "client_id": api_key_record["client_id"],
                "user_id": api_key_record["user_id"],
            }

        except Exception as e:
            logger.error("api_key_validation_error", error=str(e), exc_info=True)
            return None
