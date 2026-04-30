"""
Rate limiting: per-user and per-client message limits.

Uses Redis to track:
- Messages per user per minute
- Messages per client per hour
- Failed login attempts
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Any
import structlog
import redis.asyncio as redis


logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Rate limiter with Redis backend.

    Tracks:
    - User messages per minute
    - Client messages per hour
    - Failed login attempts
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        supabase_client: Optional[Any] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL
            supabase_client: Optional Supabase client for fetching limits from DB
        """
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.supabase = supabase_client

        # Configuration
        self.rate_limit_per_user_per_minute = int(
            os.getenv("RATE_LIMIT_PER_USER_PER_MINUTE", "30")
        )
        self.rate_limit_per_client_per_hour = int(
            os.getenv("RATE_LIMIT_PER_CLIENT_PER_HOUR", "10000")
        )
        self.login_max_attempts = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
        self.login_lockout_minutes = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "30"))
        self.token_limit_warning_pct = 0.80

    async def initialize(self) -> None:
        """Connect to Redis."""
        self.redis = await redis.from_url(self.redis_url)
        logger.info("rate_limiter_initialized", redis_url=self.redis_url)

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("rate_limiter_closed")

    async def check_user_message_limit(
        self,
        user_id: str,
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if user has exceeded message rate limit.

        Limit: N messages per minute

        Args:
            user_id: User ID

        Returns:
            (allowed: bool, info: dict with current count and limit)
        """
        if not self.redis:
            raise RuntimeError("Rate limiter not initialized")

        key = f"ratelimit:user:{user_id}:messages"

        try:
            # Increment counter
            current = await self.redis.incr(key)

            # Set expiration on first increment
            if current == 1:
                await self.redis.expire(key, 60)  # 1 minute

            allowed = current <= self.rate_limit_per_user_per_minute

            if not allowed:
                logger.warning(
                    "user_rate_limit_exceeded",
                    user_id=user_id,
                    current=current,
                    limit=self.rate_limit_per_user_per_minute,
                )

            return allowed, {
                "current": current,
                "limit": self.rate_limit_per_user_per_minute,
                "window_seconds": 60,
            }

        except Exception as e:
            logger.error("rate_limit_check_error", error=str(e), exc_info=True)
            return True, {}  # Default: allow on error

    async def check_client_message_limit(
        self,
        client_id: str,
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if client has exceeded message rate limit.

        Limit: N messages per hour

        Args:
            client_id: Client ID

        Returns:
            (allowed: bool, info: dict with current count and limit)
        """
        if not self.redis:
            raise RuntimeError("Rate limiter not initialized")

        key = f"ratelimit:client:{client_id}:messages"

        try:
            current = await self.redis.incr(key)

            if current == 1:
                await self.redis.expire(key, 3600)  # 1 hour

            allowed = current <= self.rate_limit_per_client_per_hour

            if not allowed:
                logger.warning(
                    "client_rate_limit_exceeded",
                    client_id=client_id,
                    current=current,
                    limit=self.rate_limit_per_client_per_hour,
                )

            return allowed, {
                "current": current,
                "limit": self.rate_limit_per_client_per_hour,
                "window_seconds": 3600,
            }

        except Exception as e:
            logger.error("rate_limit_check_error", error=str(e), exc_info=True)
            return True, {}

    async def record_failed_login(self, email: str) -> tuple[bool, int]:
        """
        Record failed login attempt.

        Locks account after N attempts for M minutes.

        Args:
            email: User email

        Returns:
            (allowed: bool, attempts_remaining: int)
        """
        if not self.redis:
            raise RuntimeError("Rate limiter not initialized")

        key = f"ratelimit:login:{email}"

        try:
            # Check if already locked
            lockout_key = f"ratelimit:login:{email}:lockout"
            locked = await self.redis.exists(lockout_key)

            if locked:
                remaining_ttl = await self.redis.ttl(lockout_key)
                logger.warning(
                    "login_attempt_during_lockout",
                    email=email,
                    lockout_remaining_seconds=remaining_ttl,
                )
                return False, 0

            # Increment fail count
            attempts = await self.redis.incr(key)

            # Set expiration on first attempt
            if attempts == 1:
                await self.redis.expire(key, 3600)  # 1 hour window

            # Lock if max attempts exceeded
            if attempts >= self.login_max_attempts:
                await self.redis.setex(
                    lockout_key,
                    self.login_lockout_minutes * 60,
                    "1",
                )
                logger.warning(
                    "account_locked_too_many_attempts",
                    email=email,
                    attempts=attempts,
                )
                return False, 0

            remaining = self.login_max_attempts - attempts

            logger.info(
                "failed_login_recorded",
                email=email,
                attempts=attempts,
                remaining=remaining,
            )

            return True, remaining

        except Exception as e:
            logger.error("login_rate_limit_error", error=str(e), exc_info=True)
            return True, self.login_max_attempts

    async def reset_login_attempts(self, email: str) -> None:
        """
        Reset failed login counter for email.

        Called after successful login.

        Args:
            email: User email
        """
        if not self.redis:
            return

        try:
            key = f"ratelimit:login:{email}"
            await self.redis.delete(key)

            logger.info("login_attempts_reset", email=email)

        except Exception as e:
            logger.error("reset_login_attempts_error", error=str(e), exc_info=True)

    async def get_client_token_usage(
        self,
        client_id: str,
    ) -> dict[str, int]:
        """
        Get current token usage for client this month.

        Args:
            client_id: Client ID

        Returns:
            Dict with token counts and limit
        """
        if not self.redis:
            return {}

        try:
            key = f"tokens:client:{client_id}:{datetime.now().strftime('%Y-%m')}"
            usage = await self.redis.get(key)
            used = int(usage or 0)

            # Fetch limit from Supabase if available
            limit = 1000000  # Default fallback
            if self.supabase:
                try:
                    response = self.supabase.table("clients").select(
                        "monthly_token_limit"
                    ).eq("id", client_id).single().execute()

                    if response.data:
                        limit = response.data.get("monthly_token_limit", 1000000)
                except Exception as e:
                    logger.warning(
                        "failed_to_fetch_token_limit",
                        client_id=client_id,
                        error=str(e),
                    )

            return {
                "used": used,
                "limit": limit,
            }

        except Exception as e:
            logger.error("token_usage_error", error=str(e), exc_info=True)
            return {}

    async def increment_token_count(
        self,
        client_id: str,
        tokens: int,
    ) -> None:
        """
        Increment token usage for client.

        Called after each agent response.

        Args:
            client_id: Client ID
            tokens: Number of tokens consumed
        """
        if not self.redis:
            return

        try:
            key = f"tokens:client:{client_id}:{datetime.now().strftime('%Y-%m')}"

            # Increment by token count
            await self.redis.incrby(key, tokens)

            # Set expiration (end of month + 1 day)
            tomorrow = datetime.now() + timedelta(days=1)
            month_end = tomorrow.replace(day=1) - timedelta(seconds=1)
            ttl = int((month_end - datetime.now()).total_seconds())

            await self.redis.expire(key, ttl)

            # Check if approaching limit and send alert
            usage = await self.get_client_token_usage(client_id)
            if usage.get("limit", 0) > 0:
                usage_pct = usage.get("used", 0) / usage.get("limit", 1)

                if usage_pct >= self.token_limit_warning_pct:
                    logger.warning(
                        "token_usage_threshold_warning",
                        client_id=client_id,
                        used=usage.get("used"),
                        limit=usage.get("limit"),
                        usage_pct=round(usage_pct * 100, 2),
                    )

                    # Insert alert into Supabase if available
                    if self.supabase:
                        try:
                            self.supabase.table("alerts").insert({
                                "client_id": client_id,
                                "type": "token_usage_threshold",
                                "severity": "warning",
                                "message": f"Token usage at {round(usage_pct * 100, 2)}% of monthly limit",
                                "created_at": datetime.utcnow().isoformat(),
                            }).execute()
                        except Exception as e:
                            logger.error(
                                "failed_to_create_alert",
                                client_id=client_id,
                                error=str(e),
                            )

        except Exception as e:
            logger.error("increment_token_count_error", error=str(e), exc_info=True)
