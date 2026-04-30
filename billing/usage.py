"""
Usage tracking: Monitor token consumption and enforce limits.

Tracks token usage per client, alerts at thresholds, blocks at limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks and enforces token usage limits."""

    # Monthly limits (tokens)
    DEFAULT_MONTHLY_LIMIT = 1000000  # 1M tokens
    WARNING_THRESHOLD = 0.80  # Alert at 80%
    BLOCK_THRESHOLD = 1.0  # Block at 100%

    # Approximate token prices (USD)
    TOKEN_COST_PER_MILLION = 0.02  # $0.02 per 1M tokens (rough estimate)

    def __init__(self, supabase_client: Any):
        """
        Initialize usage tracker.

        Args:
            supabase_client: Supabase client
        """
        self.supabase = supabase_client

    async def log_token_usage(
        self,
        client_id: str,
        tokens_used: int,
        operation: str = "message",
    ) -> bool:
        """
        Log token usage for a client.

        Args:
            client_id: Client ID
            tokens_used: Number of tokens used
            operation: Type of operation (message, vision, etc)

        Returns:
            True if logged successfully
        """
        try:
            log_entry = {
                "id": str(__import__("uuid").uuid4()),
                "client_id": client_id,
                "tokens_used": tokens_used,
                "operation": operation,
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("token_logs").insert(log_entry).execute()

            logger.info(
                f"Logged {tokens_used} tokens for {client_id}",
                extra={"operation": operation},
            )

            return True

        except Exception as e:
            logger.error(f"Error logging token usage: {e}")
            return False

    async def get_monthly_usage(self, client_id: str) -> dict[str, Any]:
        """
        Get token usage for current month.

        Args:
            client_id: Client ID

        Returns:
            Usage stats dict
        """
        try:
            # Get start of month
            today = datetime.utcnow().date()
            month_start = today.replace(day=1).isoformat()
            month_end = datetime.utcnow().isoformat()

            # Get usage logs
            response = self.supabase.table("token_logs").select(
                "tokens_used"
            ).eq("client_id", client_id).gte(
                "created_at", f"{month_start}T00:00:00"
            ).lte("created_at", month_end).execute()

            logs = response.data or []

            total_tokens = sum(log.get("tokens_used", 0) for log in logs)

            # Get client limit
            client_response = self.supabase.table("clients").select(
                "monthly_token_limit"
            ).eq("id", client_id).single().execute()

            limit = (
                client_response.data.get("monthly_token_limit", self.DEFAULT_MONTHLY_LIMIT)
                if client_response.data
                else self.DEFAULT_MONTHLY_LIMIT
            )

            usage_pct = (total_tokens / limit * 100) if limit > 0 else 0

            cost = (total_tokens / 1000000) * self.TOKEN_COST_PER_MILLION

            return {
                "total_tokens": total_tokens,
                "limit": limit,
                "usage_percent": round(usage_pct, 2),
                "remaining_tokens": max(0, limit - total_tokens),
                "estimated_cost": round(cost, 2),
                "messages_count": len(logs),
            }

        except Exception as e:
            logger.error(f"Error fetching monthly usage: {e}")
            return None

    async def check_usage_limit(self, client_id: str) -> dict[str, Any]:
        """
        Check if client has exceeded usage limits.

        Args:
            client_id: Client ID

        Returns:
            Limit check result
        """
        try:
            usage = await self.get_monthly_usage(client_id)

            if not usage:
                return {"status": "error"}

            result = {
                "status": "ok",
                "usage": usage,
                "warnings": [],
                "blocked": False,
            }

            # Check thresholds
            usage_pct = usage.get("usage_percent", 0)

            if usage_pct >= self.BLOCK_THRESHOLD:
                result["blocked"] = True
                result["warnings"].append("Monthly token limit exceeded")

            elif usage_pct >= (self.WARNING_THRESHOLD * 100):
                result["warnings"].append(f"Using {usage_pct:.0f}% of monthly limit")

            return result

        except Exception as e:
            logger.error(f"Error checking usage limit: {e}")
            return {"status": "error"}

    async def enforce_limit(self, client_id: str) -> bool:
        """
        Enforce usage limit for a client (soft block).

        If client exceeds limit, pause message processing with notification.

        Args:
            client_id: Client ID

        Returns:
            True if limit enforced
        """
        try:
            check = await self.check_usage_limit(client_id)

            if check.get("blocked"):
                # Update client status
                self.supabase.table("clients").update({
                    "status": "usage_limit_exceeded",
                    "usage_limited_date": datetime.utcnow().isoformat(),
                }).eq("id", client_id).execute()

                logger.info(f"Usage limit enforced for {client_id}")

                # Send notification to admin
                await self._notify_admin_usage_exceeded(client_id, check)

                return True

            return False

        except Exception as e:
            logger.error(f"Error enforcing limit: {e}")
            return False

    async def reset_monthly_usage(self, client_id: str) -> bool:
        """
        Reset monthly usage (called when subscription renews).

        Args:
            client_id: Client ID

        Returns:
            True if reset
        """
        try:
            # Delete old logs (keep for archival but mark as archived)
            today = datetime.utcnow().date()
            month_start = today.replace(day=1).isoformat()

            # Archive logs
            self.supabase.table("token_logs").update({
                "archived": True,
            }).eq("client_id", client_id).lt(
                "created_at", f"{month_start}T00:00:00"
            ).execute()

            # Update client if was limited
            self.supabase.table("clients").update({
                "status": "active",
            }).eq("id", client_id).eq(
                "status", "usage_limit_exceeded"
            ).execute()

            logger.info(f"Monthly usage reset for {client_id}")

            return True

        except Exception as e:
            logger.error(f"Error resetting usage: {e}")
            return False

    async def get_usage_by_operation(
        self,
        client_id: str,
    ) -> dict[str, int]:
        """
        Get token usage breakdown by operation type.

        Args:
            client_id: Client ID

        Returns:
            Dict of operation -> tokens
        """
        try:
            response = self.supabase.table("token_logs").select(
                "operation, tokens_used"
            ).eq("client_id", client_id).gte(
                "created_at",
                (datetime.utcnow() - timedelta(days=30)).isoformat(),
            ).execute()

            logs = response.data or []

            breakdown = {}

            for log in logs:
                operation = log.get("operation", "unknown")
                tokens = log.get("tokens_used", 0)

                breakdown[operation] = breakdown.get(operation, 0) + tokens

            return breakdown

        except Exception as e:
            logger.error(f"Error getting usage breakdown: {e}")
            return {}

    async def get_usage_trend(
        self,
        client_id: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get daily usage trend.

        Args:
            client_id: Client ID
            days: Number of days to analyze

        Returns:
            List of daily stats
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            response = self.supabase.table("token_logs").select(
                "created_at, tokens_used"
            ).eq("client_id", client_id).gte(
                "created_at", cutoff_date
            ).order("created_at").execute()

            logs = response.data or []

            # Group by day
            daily = {}

            for log in logs:
                day = log.get("created_at", "")[:10]
                tokens = log.get("tokens_used", 0)

                daily[day] = daily.get(day, 0) + tokens

            # Format as list
            trend = []

            for day in sorted(daily.keys()):
                trend.append({
                    "date": day,
                    "tokens": daily[day],
                    "cost": (daily[day] / 1000000) * self.TOKEN_COST_PER_MILLION,
                })

            return trend

        except Exception as e:
            logger.error(f"Error getting usage trend: {e}")
            return []

    async def _notify_admin_usage_exceeded(
        self,
        client_id: str,
        check: dict[str, Any],
    ) -> bool:
        """
        Notify admin when client exceeds usage limit.

        Args:
            client_id: Client ID
            check: Limit check result

        Returns:
            True if notified
        """
        try:
            usage = check.get("usage", {})

            # Log as alert
            alert = {
                "id": str(__import__("uuid").uuid4()),
                "client_id": client_id,
                "type": "usage_limit_exceeded",
                "severity": "warning",
                "message": f"Client exceeded monthly token limit: {usage.get('total_tokens'):,} / {usage.get('limit'):,}",
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("alerts").insert(alert).execute()

            logger.info(f"Alert created for {client_id}")

            return True

        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
            return False

    async def get_cost_breakdown(
        self,
        client_id: str,
        months: int = 3,
    ) -> dict[str, Any]:
        """
        Get cost breakdown for a client.

        Args:
            client_id: Client ID
            months: Number of months to analyze

        Returns:
            Cost breakdown dict
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=30 * months)).isoformat()

            response = self.supabase.table("token_logs").select(
                "created_at, tokens_used"
            ).eq("client_id", client_id).gte(
                "created_at", cutoff_date
            ).order("created_at").execute()

            logs = response.data or []

            total_tokens = sum(log.get("tokens_used", 0) for log in logs)
            total_cost = (total_tokens / 1000000) * self.TOKEN_COST_PER_MILLION

            # Group by month
            monthly = {}

            for log in logs:
                month = log.get("created_at", "")[:7]  # YYYY-MM
                tokens = log.get("tokens_used", 0)

                if month not in monthly:
                    monthly[month] = {
                        "tokens": 0,
                        "cost": 0,
                    }

                monthly[month]["tokens"] += tokens
                monthly[month]["cost"] = (
                    monthly[month]["tokens"] / 1000000
                ) * self.TOKEN_COST_PER_MILLION

            return {
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 2),
                "average_monthly_cost": round(total_cost / months, 2) if months > 0 else 0,
                "by_month": monthly,
            }

        except Exception as e:
            logger.error(f"Error calculating costs: {e}")
            return None
