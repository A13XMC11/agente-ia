"""
Billing: Stripe subscription management and webhook handling.

Manages monthly subscriptions, handles payment events, pauses agents on non-payment.
"""

import logging
import hmac
import hashlib
from typing import Any, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class StripeBilling:
    """Manages Stripe subscriptions and billing."""

    def __init__(
        self,
        stripe_secret_key: str,
        stripe_webhook_secret: str,
        supabase_client: Any,
    ):
        """
        Initialize Stripe billing.

        Args:
            stripe_secret_key: Stripe secret API key
            stripe_webhook_secret: Stripe webhook signing secret
            supabase_client: Supabase client
        """
        self.stripe_secret_key = stripe_secret_key
        self.stripe_webhook_secret = stripe_webhook_secret
        self.supabase = supabase_client
        self.stripe_api_url = "https://api.stripe.com/v1"
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Stripe webhook signature.

        Args:
            body: Request body bytes
            signature: Stripe-Signature header

        Returns:
            True if signature is valid
        """
        try:
            timestamp = signature.split(",")[0].split("=")[1]
            provided_hash = signature.split(",")[1].split("=")[1]

            signed_content = f"{timestamp}.{body.decode()}"

            expected_hash = hmac.new(
                self.stripe_webhook_secret.encode(),
                signed_content.encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(provided_hash, expected_hash)

        except Exception as e:
            logger.error(f"Error verifying webhook: {e}")
            return False

    async def create_subscription(
        self,
        client_id: str,
        monthly_amount: float,
        customer_email: str,
    ) -> Optional[dict[str, Any]]:
        """
        Create a Stripe subscription for a client.

        Args:
            client_id: Client ID
            monthly_amount: Monthly subscription amount in USD
            customer_email: Customer email

        Returns:
            Subscription object or None
        """
        try:
            # Create Stripe customer
            customer_response = await self.http_client.post(
                f"{self.stripe_api_url}/customers",
                auth=(self.stripe_secret_key, ""),
                data={
                    "email": customer_email,
                    "metadata": {"client_id": client_id},
                },
            )

            if customer_response.status_code != 200:
                logger.error(f"Failed to create customer: {customer_response.text}")
                return None

            customer = customer_response.json()
            customer_id = customer["id"]

            # Create price
            price_response = await self.http_client.post(
                f"{self.stripe_api_url}/prices",
                auth=(self.stripe_secret_key, ""),
                data={
                    "currency": "usd",
                    "unit_amount": int(monthly_amount * 100),
                    "recurring": {"interval": "month"},
                    "product_data": {"name": f"Agente IA - {client_id}"},
                },
            )

            if price_response.status_code != 200:
                logger.error(f"Failed to create price: {price_response.text}")
                return None

            price = price_response.json()
            price_id = price["id"]

            # Create subscription
            sub_response = await self.http_client.post(
                f"{self.stripe_api_url}/subscriptions",
                auth=(self.stripe_secret_key, ""),
                data={
                    "customer": customer_id,
                    "items": [{"price": price_id}],
                    "metadata": {"client_id": client_id},
                },
            )

            if sub_response.status_code != 200:
                logger.error(f"Failed to create subscription: {sub_response.text}")
                return None

            subscription = sub_response.json()

            # Save to Supabase
            self.supabase.table("subscription").insert({
                "client_id": client_id,
                "stripe_subscription_id": subscription["id"],
                "stripe_customer_id": customer_id,
                "monthly_amount": monthly_amount,
                "status": "active",
                "current_period_start": datetime.fromtimestamp(
                    subscription["current_period_start"]
                ).isoformat(),
                "current_period_end": datetime.fromtimestamp(
                    subscription["current_period_end"]
                ).isoformat(),
                "next_billing_date": datetime.fromtimestamp(
                    subscription["current_period_end"]
                ).isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            }).execute()

            logger.info(f"Subscription created for {client_id}")

            return subscription

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    async def handle_webhook(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Stripe webhook event.

        Args:
            event: Stripe event

        Returns:
            Response dict
        """
        try:
            event_type = event.get("type")

            if event_type == "invoice.payment_succeeded":
                return await self._handle_payment_succeeded(event)

            elif event_type == "invoice.payment_failed":
                return await self._handle_payment_failed(event)

            elif event_type == "customer.subscription.deleted":
                return await self._handle_subscription_deleted(event)

            else:
                logger.info(f"Ignoring event: {event_type}")
                return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {"error": str(e)}

    async def _handle_payment_succeeded(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle successful payment."""
        try:
            invoice = event.get("data", {}).get("object", {})
            subscription_id = invoice.get("subscription")
            customer_id = invoice.get("customer")

            # Get client from subscription
            sub_response = self.supabase.table("subscription").select(
                "client_id"
            ).eq("stripe_subscription_id", subscription_id).single().execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found: {subscription_id}")
                return {"status": "ok"}

            client_id = sub_response.data["client_id"]

            # Update subscription status
            self.supabase.table("subscription").update({
                "status": "active",
                "last_payment_date": datetime.utcnow().isoformat(),
            }).eq("client_id", client_id).execute()

            # Reactivate client if paused
            self.supabase.table("clientes").update({
                "status": "active",
            }).eq("id", client_id).eq("status", "paused").execute()

            logger.info(f"Payment succeeded for {client_id}")

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            return {"error": str(e)}

    async def _handle_payment_failed(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle failed payment."""
        try:
            invoice = event.get("data", {}).get("object", {})
            subscription_id = invoice.get("subscription")

            # Get client from subscription
            sub_response = self.supabase.table("subscription").select(
                "client_id"
            ).eq("stripe_subscription_id", subscription_id).single().execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found: {subscription_id}")
                return {"status": "ok"}

            client_id = sub_response.data["client_id"]

            # Update subscription status
            self.supabase.table("subscription").update({
                "status": "past_due",
                "payment_failed_count": (
                    self.supabase.table("subscription").select("payment_failed_count").eq(
                        "client_id", client_id
                    ).single().execute().data.get("payment_failed_count", 0) + 1
                ),
            }).eq("client_id", client_id).execute()

            # Check if we should pause the client
            sub_data = self.supabase.table("subscription").select(
                "payment_failed_count"
            ).eq("client_id", client_id).single().execute().data

            failed_count = sub_data.get("payment_failed_count", 0)

            if failed_count >= 3:
                # Pause client after 3 failed payments (3 days)
                self.supabase.table("clientes").update({
                    "status": "paused",
                    "paused_reason": "payment_failed",
                    "paused_date": datetime.utcnow().isoformat(),
                }).eq("id", client_id).execute()

                logger.info(f"Client paused due to failed payment: {client_id}")

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
            return {"error": str(e)}

    async def _handle_subscription_deleted(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle subscription cancellation."""
        try:
            subscription = event.get("data", {}).get("object", {})
            subscription_id = subscription.get("id")

            # Get client
            sub_response = self.supabase.table("subscription").select(
                "client_id"
            ).eq("stripe_subscription_id", subscription_id).single().execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found: {subscription_id}")
                return {"status": "ok"}

            client_id = sub_response.data["client_id"]

            # Update subscription status
            self.supabase.table("subscription").update({
                "status": "cancelled",
                "cancelled_date": datetime.utcnow().isoformat(),
            }).eq("client_id", client_id).execute()

            # Pause client
            self.supabase.table("clientes").update({
                "status": "paused",
                "paused_reason": "subscription_cancelled",
            }).eq("id", client_id).execute()

            logger.info(f"Client paused due to subscription cancellation: {client_id}")

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling subscription deletion: {e}")
            return {"error": str(e)}

    async def get_subscription(
        self,
        client_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get subscription for a client.

        Args:
            client_id: Client ID

        Returns:
            Subscription data or None
        """
        try:
            response = self.supabase.table("subscription").select(
                "*"
            ).eq("client_id", client_id).single().execute()

            return response.data

        except Exception as e:
            logger.error(f"Error fetching subscription: {e}")
            return None

    async def cancel_subscription(self, client_id: str) -> bool:
        """
        Cancel a client's subscription.

        Args:
            client_id: Client ID

        Returns:
            True if cancelled
        """
        try:
            sub = await self.get_subscription(client_id)

            if not sub:
                logger.warning(f"No subscription found for {client_id}")
                return False

            subscription_id = sub.get("stripe_subscription_id")

            # Cancel via Stripe API
            response = await self.http_client.delete(
                f"{self.stripe_api_url}/subscriptions/{subscription_id}",
                auth=(self.stripe_secret_key, ""),
            )

            if response.status_code == 200:
                logger.info(f"Subscription cancelled for {client_id}")
                return True
            else:
                logger.error(f"Failed to cancel subscription: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False
