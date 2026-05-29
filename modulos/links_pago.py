"""
Payment links module: initiate payments via Payphone, MercadoPago, PayPal.

Payphone uses a push-payment model — no link is generated.
A sale request is sent to the customer's Payphone app as a push notification.
The customer approves or rejects within 5 minutes.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

PAYPHONE_API_URL = "https://pay.payphonetodoesposible.com/api"


class LinksPagoModule:
    """Payment initiation and tracking."""

    def __init__(self, supabase_client: Any):
        self.supabase = supabase_client
        self.payphone_token = os.environ.get("PAYPHONE_TOKEN")
        self.payphone_enabled = bool(self.payphone_token)

    async def generar_cobro_payphone(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
        descripcion: str,
        phone_number: str,
        country_code: str = "593",
        metadatos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Initiate a Payphone sale request for a customer.

        Sends a push notification to the customer's Payphone app.
        The customer has 5 minutes to approve. Payphone calls our
        webhook (PAYPHONE_RESPONSE_URL) when the customer acts.

        Args:
            client_id: Business client ID
            usuario_id: End-user ID
            monto: Amount in USD
            descripcion: Payment reference shown to payer
            phone_number: Customer's Payphone phone number (e.g. "0984111222")
            country_code: E.164 country code without + (default "593" for Ecuador)
            metadatos: Optional extra info stored in optionalParameter1

        Returns:
            Dict with transaction_id and link_id on success, error on failure
        """
        try:
            if not self.payphone_enabled:
                return {"error": "Payphone no configurado (PAYPHONE_TOKEN faltante)"}

            client_transaction_id = str(uuid4())
            amount_cents = int(monto * 100)

            response_url = os.environ.get(
                "PAYPHONE_RESPONSE_URL",
                "https://api.lanlabsec.com/webhooks/payphone",
            )

            payload: dict[str, Any] = {
                "phoneNumber": phone_number,
                "countryCode": country_code,
                "amount": amount_cents,
                "amountWithoutTax": amount_cents,
                "tax": 0,
                "clientTransactionId": client_transaction_id,
                "currency": "USD",
                "reference": descripcion[:100],
                "responseUrl": response_url,
                "timeZone": -5,
                "clientUserId": usuario_id,
            }
            if metadatos:
                payload["optionalParameter1"] = str(metadatos)[:200]
            if os.environ.get("PAYPHONE_STORE_ID"):
                payload["storeId"] = os.environ["PAYPHONE_STORE_ID"]

            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await http.post(
                    f"{PAYPHONE_API_URL}/Sale",
                    headers={
                        "Authorization": f"Bearer {self.payphone_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(f"Payphone error: {response.status_code} {response.text}")
                return {"error": f"Payphone error: {response.status_code}"}

            data = response.json()

            # Payphone returns { errorCode, errors } on failure
            if "errorCode" in data:
                errors = data.get("errors", [])
                detail = errors[0].get("message") if errors else data.get("message", "Error Payphone")
                logger.error(f"Payphone sale rejected: {detail}")
                return {"error": detail}

            payphone_transaction_id = data.get("transactionId")
            if not payphone_transaction_id:
                return {"error": "Payphone no retornó transactionId"}

            record = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": usuario_id,
                "provider": "payphone",
                "amount": monto,
                "currency": "USD",
                "description": descripcion,
                "payphone_client_transaction_id": client_transaction_id,
                "payphone_transaction_id": str(payphone_transaction_id),
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            }

            self.supabase.table("payment_links").insert(record).execute()

            logger.info(
                f"Payphone sale sent to {phone_number}: txn {payphone_transaction_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "link_id": record["id"],
                "transaction_id": payphone_transaction_id,
                "client_transaction_id": client_transaction_id,
                "provider": "payphone",
                "monto": monto,
                "expira_en": "5 minutos",
                "mensaje": "Se envió una notificación al celular del cliente para que apruebe el pago.",
            }

        except Exception as e:
            logger.error(f"Error creating Payphone sale: {e}")
            return {"error": str(e)}

    async def generar_link_pago_mercadopago(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
        descripcion: str,
        metadatos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate a MercadoPago payment link (placeholder — SDK not yet integrated)."""
        try:
            payment_link = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": usuario_id,
                "provider": "mercadopago",
                "amount": monto,
                "currency": "ARS",
                "description": descripcion,
                "payment_url": f"https://checkout.mercadopago.com/p/{uuid4()}",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            }

            self.supabase.table("payment_links").insert(payment_link).execute()

            logger.info(
                f"MercadoPago payment link created: {payment_link['id']} for user {usuario_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "link_id": payment_link["id"],
                "payment_url": payment_link["payment_url"],
                "provider": "mercadopago",
                "monto": monto,
                "expira_en": "24 horas",
            }

        except Exception as e:
            logger.error(f"Error creating MercadoPago payment link: {e}")
            return {"error": str(e)}

    async def generar_link_pago_paypal(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
        descripcion: str,
        metadatos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate a PayPal payment link (placeholder — SDK not yet integrated)."""
        try:
            payment_link = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": usuario_id,
                "provider": "paypal",
                "amount": monto,
                "currency": "USD",
                "description": descripcion,
                "payment_url": f"https://paypal.me/{client_id}/{monto}",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            }

            self.supabase.table("payment_links").insert(payment_link).execute()

            logger.info(
                f"PayPal payment link created: {payment_link['id']} for user {usuario_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "link_id": payment_link["id"],
                "payment_url": payment_link["payment_url"],
                "provider": "paypal",
                "monto": monto,
                "expira_en": "24 horas",
            }

        except Exception as e:
            logger.error(f"Error creating PayPal payment link: {e}")
            return {"error": str(e)}

    async def generar_link_pago(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
        descripcion: str,
        proveedores: Optional[list[str]] = None,
        phone_number: Optional[str] = None,
        country_code: str = "593",
    ) -> dict[str, Any]:
        """
        Initiate a payment with one or more providers.

        Default provider is payphone. For payphone, phone_number is required.
        Supports: payphone, mercadopago, paypal.
        """
        try:
            if not proveedores:
                proveedores = ["payphone"]

            payment_options: dict[str, Any] = {
                "link_id": str(uuid4()),
                "monto": monto,
                "descripcion": descripcion,
                "opciones": {},
            }

            if "payphone" in proveedores:
                if not phone_number:
                    payment_options["opciones"]["payphone"] = {
                        "error": "Se requiere el número de teléfono Payphone del cliente."
                    }
                else:
                    result = await self.generar_cobro_payphone(
                        client_id, usuario_id, monto, descripcion,
                        phone_number=phone_number, country_code=country_code,
                    )
                    if "error" not in result:
                        payment_options["opciones"]["payphone"] = result

            if "mercadopago" in proveedores:
                result = await self.generar_link_pago_mercadopago(
                    client_id, usuario_id, monto, descripcion
                )
                if "error" not in result:
                    payment_options["opciones"]["mercadopago"] = result

            if "paypal" in proveedores:
                result = await self.generar_link_pago_paypal(
                    client_id, usuario_id, monto, descripcion
                )
                if "error" not in result:
                    payment_options["opciones"]["paypal"] = result

            logger.info(
                f"Payment initiated with {len(payment_options['opciones'])} options",
                extra={"client_id": client_id},
            )

            return {"success": True, "payment_options": payment_options}

        except Exception as e:
            logger.error(f"Error generating payment: {e}")
            return {"error": str(e)}

    async def obtener_estado_pago(self, link_id: str) -> dict[str, Any]:
        """Check payment status by link ID."""
        try:
            response = self.supabase.table("payment_links").select("*").eq(
                "id", link_id
            ).single().execute()

            payment_link = response.data
            return {
                "link_id": link_id,
                "status": payment_link["status"],
                "provider": payment_link["provider"],
                "amount": payment_link["amount"],
                "created_at": payment_link["created_at"],
            }

        except Exception as e:
            logger.error(f"Error fetching payment status: {e}")
            return {"error": str(e)}

    async def get_payment_links_usuario(
        self,
        client_id: str,
        usuario_id: str,
    ) -> list[dict[str, Any]]:
        """Get all payment links for a user."""
        try:
            response = self.supabase.table("payment_links").select("*").eq(
                "cliente_id", client_id
            ).eq("user_id", usuario_id).order(
                "created_at", desc=True
            ).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching payment links: {e}")
            return []
