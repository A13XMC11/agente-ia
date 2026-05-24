"""
Billing: Stripe subscription management and webhook handling.

Manages monthly subscriptions, handles payment events, pauses agents on non-payment.
"""

import hmac
import hashlib
import logging
import time
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
        stripe_product_id: Optional[str] = None,
        price_map: Optional[dict[int, str]] = None,
    ):
        self.stripe_secret_key = stripe_secret_key
        self.stripe_webhook_secret = stripe_webhook_secret
        self.supabase = supabase_client
        self.stripe_product_id = stripe_product_id
        # Maps amount_cents → Stripe Price ID, e.g. {14900: "price_xxx"}
        self.price_map: dict[int, str] = price_map or {}
        self.stripe_api_url = "https://api.stripe.com/v1"
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify Stripe webhook signature (v1 scheme).

        Stripe sends: t=<timestamp>,v1=<hash>[,v0=<hash>]
        We validate v1 and enforce a 5-minute tolerance.
        """
        try:
            parts: dict[str, str] = {}
            for item in signature.split(","):
                if "=" in item:
                    key, _, val = item.partition("=")
                    parts.setdefault(key.strip(), val.strip())

            timestamp = parts.get("t")
            provided_hash = parts.get("v1")

            if not timestamp or not provided_hash:
                logger.warning("stripe_webhook_missing_fields")
                return False

            # Replay-attack guard: reject events older than 5 minutes
            if abs(time.time() - int(timestamp)) > 300:
                logger.warning("stripe_webhook_timestamp_too_old")
                return False

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

        Uses a pre-configured Price ID from price_map when available;
        falls back to creating a one-off price.
        """
        try:
            # Create Stripe customer
            customer_response = await self.http_client.post(
                f"{self.stripe_api_url}/customers",
                auth=(self.stripe_secret_key, ""),
                data={
                    "email": customer_email,
                    "metadata[client_id]": client_id,
                },
            )

            if customer_response.status_code != 200:
                logger.error(f"Failed to create customer: {customer_response.text}")
                return None

            customer = customer_response.json()
            customer_id = customer["id"]

            # Resolve price ID: prefer pre-configured; create on-the-fly otherwise
            amount_cents = int(monthly_amount * 100)
            price_id = self.price_map.get(amount_cents)

            if not price_id:
                price_data: dict[str, Any] = {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "recurring[interval]": "month",
                }
                if self.stripe_product_id:
                    price_data["product"] = self.stripe_product_id
                else:
                    price_data["product_data[name]"] = f"Agente IA - {client_id}"

                price_response = await self.http_client.post(
                    f"{self.stripe_api_url}/prices",
                    auth=(self.stripe_secret_key, ""),
                    data=price_data,
                )

                if price_response.status_code != 200:
                    logger.error(f"Failed to create price: {price_response.text}")
                    return None

                price_id = price_response.json()["id"]

            # Create subscription with invoice-based collection
            sub_response = await self.http_client.post(
                f"{self.stripe_api_url}/subscriptions",
                auth=(self.stripe_secret_key, ""),
                data={
                    "customer": customer_id,
                    "items[0][price]": price_id,
                    "metadata[client_id]": client_id,
                    "collection_method": "send_invoice",
                    "days_until_due": "30",
                },
            )

            if sub_response.status_code != 200:
                logger.error(f"Failed to create subscription: {sub_response.text}")
                return None

            subscription = sub_response.json()

            now = datetime.utcnow()
            period_start = subscription.get("current_period_start")
            period_end = subscription.get("current_period_end")

            self.supabase.table("subscription").insert({
                "cliente_id": client_id,
                "stripe_subscription_id": subscription["id"],
                "stripe_customer_id": customer_id,
                "monthly_amount": monthly_amount,
                "status": subscription.get("status", "active"),
                "current_period_start": datetime.fromtimestamp(period_start).isoformat() if period_start else now.isoformat(),
                "current_period_end": datetime.fromtimestamp(period_end).isoformat() if period_end else None,
                "next_billing_date": datetime.fromtimestamp(period_end).isoformat() if period_end else None,
                "created_at": now.isoformat(),
            }).execute()

            # Finalize and send the first invoice
            invoice_id = subscription.get("latest_invoice")
            if invoice_id:
                await self.http_client.post(
                    f"{self.stripe_api_url}/invoices/{invoice_id}/finalize",
                    auth=(self.stripe_secret_key, ""),
                )
                await self.http_client.post(
                    f"{self.stripe_api_url}/invoices/{invoice_id}/send",
                    auth=(self.stripe_secret_key, ""),
                )
                logger.info(f"Invoice {invoice_id} finalized and sent for {client_id}")

            logger.info(f"Subscription created for {client_id}")
            return subscription

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    async def handle_webhook(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle Stripe webhook event."""
        try:
            event_type = event.get("type")

            if event_type == "invoice.payment_succeeded":
                return await self._handle_payment_succeeded(event)

            elif event_type == "invoice.payment_failed":
                return await self._handle_payment_failed(event)

            elif event_type == "customer.subscription.updated":
                return await self._handle_subscription_updated(event)

            elif event_type == "customer.subscription.deleted":
                return await self._handle_subscription_deleted(event)

            else:
                logger.info(f"Ignoring event: {event_type}")
                return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {"error": str(e)}

    async def _handle_payment_succeeded(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle successful payment — reactivate client if paused."""
        try:
            invoice = event.get("data", {}).get("object", {})
            subscription_id = invoice.get("subscription")

            sub_response = self.supabase.table("subscription").select(
                "cliente_id"
            ).eq("stripe_subscription_id", subscription_id).maybeSingle().execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found: {subscription_id}")
                return {"status": "ok"}

            client_id = sub_response.data["cliente_id"]

            self.supabase.table("subscription").update({
                "status": "active",
                "last_payment_date": datetime.utcnow().isoformat(),
                "payment_failed_count": 0,
            }).eq("stripe_subscription_id", subscription_id).execute()

            self.supabase.table("clientes").update({
                "estado": "activo",
            }).eq("id", client_id).eq("estado", "pausado").execute()

            logger.info(f"Payment succeeded for {client_id}")
            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            return {"error": str(e)}

    async def _handle_payment_failed(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle failed payment — pause client after 3 failures."""
        try:
            invoice = event.get("data", {}).get("object", {})
            subscription_id = invoice.get("subscription")

            sub_response = self.supabase.table("subscription").select(
                "id, cliente_id, payment_failed_count"
            ).eq("stripe_subscription_id", subscription_id).maybeSingle().execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found: {subscription_id}")
                return {"status": "ok"}

            sub = sub_response.data
            client_id = sub["cliente_id"]
            new_failed_count = (sub.get("payment_failed_count") or 0) + 1

            self.supabase.table("subscription").update({
                "status": "past_due",
                "payment_failed_count": new_failed_count,
            }).eq("stripe_subscription_id", subscription_id).execute()

            if new_failed_count >= 3:
                self.supabase.table("clientes").update({
                    "estado": "pausado",
                }).eq("id", client_id).execute()
                logger.info(f"Client paused due to failed payment: {client_id}")

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
            return {"error": str(e)}

    async def _handle_subscription_updated(
        self, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle subscription update — sync period dates and status."""
        try:
            subscription = event.get("data", {}).get("object", {})
            subscription_id = subscription.get("id")
            status = subscription.get("status")
            period_start = subscription.get("current_period_start")
            period_end = subscription.get("current_period_end")

            update_data: dict[str, Any] = {}
            if status:
                update_data["status"] = status
            if period_start:
                update_data["current_period_start"] = datetime.fromtimestamp(period_start).isoformat()
            if period_end:
                update_data["current_period_end"] = datetime.fromtimestamp(period_end).isoformat()
                update_data["next_billing_date"] = datetime.fromtimestamp(period_end).isoformat()

            if update_data:
                self.supabase.table("subscription").update(update_data).eq(
                    "stripe_subscription_id", subscription_id
                ).execute()

            logger.info(f"Subscription updated: {subscription_id}")
            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling subscription update: {e}")
            return {"error": str(e)}

    async def _handle_subscription_deleted(
        self, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle subscription cancellation."""
        try:
            subscription = event.get("data", {}).get("object", {})
            subscription_id = subscription.get("id")

            sub_response = self.supabase.table("subscription").select(
                "cliente_id"
            ).eq("stripe_subscription_id", subscription_id).maybeSingle().execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found: {subscription_id}")
                return {"status": "ok"}

            client_id = sub_response.data["cliente_id"]

            self.supabase.table("subscription").update({
                "status": "cancelled",
                "cancelled_date": datetime.utcnow().isoformat(),
            }).eq("cliente_id", client_id).execute()

            self.supabase.table("clientes").update({
                "estado": "pausado",
            }).eq("id", client_id).execute()

            logger.info(f"Client paused due to subscription cancellation: {client_id}")
            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling subscription deletion: {e}")
            return {"error": str(e)}

    async def get_subscription(
        self, client_id: str
    ) -> Optional[dict[str, Any]]:
        """Get the most recent subscription for a client."""
        try:
            response = self.supabase.table("subscription").select(
                "*"
            ).eq("cliente_id", client_id).order(
                "created_at", desc=True
            ).limit(1).execute()

            rows = response.data
            return rows[0] if rows else None

        except Exception as e:
            logger.error(f"Error fetching subscription: {e}")
            return None

    async def cancel_subscription(self, client_id: str) -> bool:
        """Cancel a client's subscription at period end."""
        try:
            sub = await self.get_subscription(client_id)
            if not sub:
                logger.warning(f"No subscription found for {client_id}")
                return False

            subscription_id = sub.get("stripe_subscription_id")

            response = await self.http_client.delete(
                f"{self.stripe_api_url}/subscriptions/{subscription_id}",
                auth=(self.stripe_secret_key, ""),
            )

            if response.status_code == 200:
                self.supabase.table("subscription").update({
                    "status": "cancelled",
                    "cancelled_date": datetime.utcnow().isoformat(),
                }).eq("cliente_id", client_id).execute()
                logger.info(f"Subscription cancelled for {client_id}")
                return True
            else:
                logger.error(f"Failed to cancel subscription: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False

    async def create_customer_portal_session(
        self,
        client_id: str,
        return_url: str,
    ) -> Optional[str]:
        """
        Create a Stripe Billing Portal session URL for a client.

        Requires the Billing Portal to be configured in the Stripe Dashboard.
        Returns the portal URL or None on failure.
        """
        try:
            sub = await self.get_subscription(client_id)
            if not sub:
                logger.warning(f"No subscription for portal session: {client_id}")
                return None

            customer_id = sub.get("stripe_customer_id")
            if not customer_id:
                logger.warning(f"No stripe_customer_id for client: {client_id}")
                return None

            response = await self.http_client.post(
                f"{self.stripe_api_url}/billing_portal/sessions",
                auth=(self.stripe_secret_key, ""),
                data={
                    "customer": customer_id,
                    "return_url": return_url,
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to create portal session: {response.text}")
                return None

            return response.json().get("url")

        except Exception as e:
            logger.error(f"Error creating portal session: {e}")
            return None
