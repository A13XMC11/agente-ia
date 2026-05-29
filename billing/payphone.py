"""
Billing: Payphone subscription management via API Sale.

Payphone (payphonetodoesposible.com) uses a push-payment model:
  1. The merchant POSTs to /api/Sale with the payer's phone number
  2. The payer receives a push notification in their Payphone app
  3. The payer approves/rejects within 5 minutes
  4. Payphone POSTs to responseUrl with ?id=<transactionId>&clientTransactionID=<uuid>
  5. We call POST /button/V2/Confirm to verify and update subscription state

For subscription billing, the super_admin provides the client's Payphone
phone number when creating the subscription.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

PAYPHONE_API_URL = "https://pay.payphonetodoesposible.com/api"

# transactionStatus values from /button/V2/Confirm
PAYPHONE_STATUS_APPROVED = 1
PAYPHONE_STATUS_CANCELLED = 2
PAYPHONE_STATUS_ERROR = 3


class PayphoneBilling:
    """Manages Payphone subscription charges and confirmation."""

    def __init__(
        self,
        payphone_token: str,
        supabase_client: Any,
        response_url: str,
        store_id: Optional[str] = None,
    ):
        self.payphone_token = payphone_token
        self.supabase = supabase_client
        self.response_url = response_url
        self.store_id = store_id
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self.http_client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.payphone_token}",
            "Content-Type": "application/json",
        }

    async def create_sale(
        self,
        client_id: str,
        monthly_amount: float,
        phone_number: str,
        country_code: str = "593",
    ) -> Optional[dict[str, Any]]:
        """
        Initiate a Payphone sale request for the monthly subscription.

        Sends a push notification to the client's Payphone app.
        The client has 5 minutes to approve the payment.

        Args:
            client_id: Internal client UUID
            monthly_amount: Amount in USD (converted to cents internally)
            phone_number: Client's Payphone phone number (e.g. "0984111222")
            country_code: E.164 country code without + (default "593" for Ecuador)

        Returns:
            Dict with transactionId from Payphone, or None on failure.
        """
        try:
            amount_cents = int(monthly_amount * 100)
            client_transaction_id = str(uuid4())

            payload: dict[str, Any] = {
                "phoneNumber": phone_number,
                "countryCode": country_code,
                "amount": amount_cents,
                "amountWithoutTax": amount_cents,
                "tax": 0,
                "clientTransactionId": client_transaction_id,
                "currency": "USD",
                "reference": f"Suscripcion mensual - {client_id[:8]}",
                "responseUrl": self.response_url,
                "timeZone": -5,
            }
            if self.store_id:
                payload["storeId"] = self.store_id

            print(f"[PAYPHONE] Sending sale request to {phone_number} (countryCode={country_code}), amount={amount_cents} cents")
            response = await self.http_client.post(
                f"{PAYPHONE_API_URL}/Sale",
                headers=self._headers(),
                json=payload,
            )

            print(f"[PAYPHONE] Sale response status: {response.status_code}")
            print(f"[PAYPHONE] Sale response body: {response.text}")

            if not (200 <= response.status_code < 300):
                logger.error(f"Payphone sale error: {response.status_code} {response.text}")
                return None

            data = response.json()

            # On error, Payphone returns { message, errorCode, errors }
            if "errorCode" in data:
                errors = data.get("errors", [])
                detail = errors[0].get("message") if errors else data.get("message", "Unknown error")
                logger.error(f"Payphone sale rejected: {detail}")
                print(f"[PAYPHONE] Sale rejected by API: {detail}")
                return None

            payphone_transaction_id = data.get("transactionId")
            if not payphone_transaction_id:
                logger.error(f"Payphone returned no transactionId: {data}")
                print(f"[PAYPHONE] No transactionId in response: {data}")
                return None

            now = datetime.utcnow()

            # Check if a subscription row already exists for this client
            existing = self.supabase.table("subscription").select("id").eq(
                "cliente_id", client_id
            ).order("created_at", desc=True).limit(1).execute()

            sub_data = {
                "payphone_client_transaction_id": client_transaction_id,
                "payphone_transaction_id": str(payphone_transaction_id),
                "monthly_amount": monthly_amount,
                "status": "pending_payment",
            }

            if existing.data:
                self.supabase.table("subscription").update(sub_data).eq(
                    "id", existing.data[0]["id"]
                ).execute()
            else:
                self.supabase.table("subscription").insert({
                    **sub_data,
                    "cliente_id": client_id,
                    "created_at": now.isoformat(),
                }).execute()

            logger.info(f"Payphone sale request sent to {phone_number} for client {client_id}")
            return {
                "transaction_id": payphone_transaction_id,
                "client_transaction_id": client_transaction_id,
                "amount": monthly_amount,
            }

        except Exception as e:
            logger.error(f"Error creating Payphone sale: {e}")
            return None

    async def confirm_payment(
        self,
        payphone_transaction_id: int,
        client_transaction_id: str,
    ) -> dict[str, Any]:
        """
        Confirm a payment with Payphone's API (POST /button/V2/Confirm).

        Called from the webhook handler when Payphone notifies us that
        the payer approved or rejected the transaction.
        """
        try:
            response = await self.http_client.post(
                f"{PAYPHONE_API_URL}/button/V2/Confirm",
                headers=self._headers(),
                json={
                    "id": payphone_transaction_id,
                    "clientTransactionId": client_transaction_id,
                },
            )

            if response.status_code != 200:
                logger.error(f"Payphone confirm error: {response.status_code} {response.text}")
                return {"status": "error", "message": response.text}

            data = response.json()
            transaction_status = data.get("transactionStatus")

            sub_response = self.supabase.table("subscription").select(
                "cliente_id"
            ).eq("payphone_client_transaction_id", client_transaction_id).execute()

            if not sub_response.data:
                logger.warning(f"Subscription not found for clientTransactionId: {client_transaction_id}")
                return {"status": "not_found"}

            client_id = sub_response.data[0]["cliente_id"]

            if transaction_status == PAYPHONE_STATUS_APPROVED:
                now = datetime.utcnow()
                self.supabase.table("subscription").update({
                    "status": "active",
                    "payphone_transaction_id": str(payphone_transaction_id),
                    "last_payment_date": now.isoformat(),
                    "payment_failed_count": 0,
                }).eq("payphone_client_transaction_id", client_transaction_id).execute()

                self.supabase.table("clientes").update({
                    "estado": "activo",
                }).eq("id", client_id).eq("estado", "pausado").execute()

                logger.info(f"Payment approved for client {client_id}")
                return {"status": "approved", "client_id": client_id}

            elif transaction_status == PAYPHONE_STATUS_CANCELLED:
                self.supabase.table("subscription").update({
                    "status": "cancelled",
                    "cancelled_date": datetime.utcnow().isoformat(),
                }).eq("payphone_client_transaction_id", client_transaction_id).execute()

                logger.info(f"Payment cancelled by payer for client {client_id}")
                return {"status": "cancelled", "client_id": client_id}

            else:
                failed_resp = self.supabase.table("subscription").select(
                    "payment_failed_count"
                ).eq("payphone_client_transaction_id", client_transaction_id).execute()

                failed_count = (failed_resp.data[0] if failed_resp.data else {}).get("payment_failed_count", 0) or 0
                new_count = failed_count + 1

                self.supabase.table("subscription").update({
                    "status": "past_due",
                    "payment_failed_count": new_count,
                }).eq("payphone_client_transaction_id", client_transaction_id).execute()

                if new_count >= 3:
                    self.supabase.table("clientes").update({
                        "estado": "pausado",
                    }).eq("id", client_id).execute()
                    logger.info(f"Client paused after {new_count} failures: {client_id}")

                return {"status": "error", "failed_count": new_count, "client_id": client_id}

        except Exception as e:
            logger.error(f"Error confirming Payphone payment: {e}")
            return {"status": "error", "message": str(e)}

    async def handle_callback(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle Payphone's webhook callback.

        Payphone POSTs to responseUrl with:
          id               → Payphone's transactionId
          clientTransactionID → our UUID

        Both GET (query params) and POST (JSON body) are supported.
        We call confirm_payment to verify with the Payphone API.
        """
        try:
            # Payphone sends "id" and "clientTransactionID" (capital ID)
            transaction_id = params.get("id") or params.get("transactionId")
            client_transaction_id = (
                params.get("clientTransactionID")
                or params.get("clientTransactionId")
            )

            if not transaction_id or not client_transaction_id:
                logger.warning(f"Payphone callback missing required params: {list(params.keys())}")
                return {"status": "error", "message": "Missing id or clientTransactionID"}

            return await self.confirm_payment(
                payphone_transaction_id=int(transaction_id),
                client_transaction_id=str(client_transaction_id),
            )

        except Exception as e:
            logger.error(f"Error handling Payphone callback: {e}")
            return {"status": "error", "message": str(e)}

    async def get_subscription(self, client_id: str) -> Optional[dict[str, Any]]:
        """Get the most recent subscription record for a client."""
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
        """Cancel a client's subscription (DB-only — no Payphone API call needed)."""
        try:
            sub = await self.get_subscription(client_id)
            if not sub:
                logger.warning(f"No subscription found for {client_id}")
                return False

            self.supabase.table("subscription").update({
                "status": "cancelled",
                "cancelled_date": datetime.utcnow().isoformat(),
            }).eq("cliente_id", client_id).execute()

            self.supabase.table("clientes").update({
                "estado": "pausado",
            }).eq("id", client_id).execute()

            logger.info(f"Subscription cancelled for {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False
