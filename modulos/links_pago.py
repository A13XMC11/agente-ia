"""
Payment links module: generate payment links via Stripe, MercadoPago, PayPal.

Handles payment link creation, tracking, and reconciliation.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


class LinksPagoModule:
    """Payment link generation and tracking."""

    def __init__(self, supabase_client: Any):
        """
        Initialize payment links module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.stripe_enabled = stripe.api_key is not None

    async def generar_link_pago_stripe(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
        descripcion: str,
        metadatos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Generate Stripe payment link.

        Args:
            client_id: Client ID
            usuario_id: User ID
            monto: Amount in USD
            descripcion: Payment description
            metadatos: Optional metadata

        Returns:
            Payment link with URL and link_id
        """
        try:
            if not self.stripe_enabled:
                return {"error": "Stripe not configured"}

            # Create Stripe session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": descripcion,
                            },
                            "unit_amount": int(monto * 100),  # Convert to cents
                        },
                        "quantity": 1,
                    }
                ],
                metadata={
                    "client_id": client_id,
                    "user_id": usuario_id,
                    **(metadatos or {}),
                },
                success_url="https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://example.com/cancel",
                mode="payment",
            )

            # Save to database
            payment_link = {
                "id": str(uuid4()),
                "client_id": client_id,
                "user_id": usuario_id,
                "provider": "stripe",
                "amount": monto,
                "currency": "USD",
                "description": descripcion,
                "stripe_session_id": session.id,
                "payment_url": session.url,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat(),
            }

            self.supabase.table("payment_links").insert(payment_link).execute()

            logger.info(
                f"Stripe payment link created: {payment_link['id']} for user {usuario_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "link_id": payment_link["id"],
                "payment_url": session.url,
                "provider": "stripe",
                "monto": monto,
                "expira_en": "24 horas",
            }

        except Exception as e:
            logger.error(f"Error creating Stripe payment link: {e}")
            return {"error": str(e)}

    async def generar_link_pago_mercadopago(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
        descripcion: str,
        metadatos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Generate MercadoPago payment link.

        Args:
            client_id: Client ID
            usuario_id: User ID
            monto: Amount in local currency
            descripcion: Payment description
            metadatos: Optional metadata

        Returns:
            Payment link with URL and link_id
        """
        try:
            # MercadoPago integration would require SDK
            # For now, return placeholder implementation

            payment_link = {
                "id": str(uuid4()),
                "client_id": client_id,
                "user_id": usuario_id,
                "provider": "mercadopago",
                "amount": monto,
                "currency": "ARS",  # Adjust based on locale
                "description": descripcion,
                "payment_url": f"https://checkout.mercadopago.com/p/{uuid4()}",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat(),
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
        """
        Generate PayPal payment link.

        Args:
            client_id: Client ID
            usuario_id: User ID
            monto: Amount in USD
            descripcion: Payment description
            metadatos: Optional metadata

        Returns:
            Payment link with URL and link_id
        """
        try:
            # PayPal integration would require SDK
            # For now, return placeholder implementation

            payment_link = {
                "id": str(uuid4()),
                "client_id": client_id,
                "user_id": usuario_id,
                "provider": "paypal",
                "amount": monto,
                "currency": "USD",
                "description": descripcion,
                "payment_url": f"https://paypal.me/{client_id}/{monto}",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat(),
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
    ) -> dict[str, Any]:
        """
        Generate payment link with multiple provider options.

        Args:
            client_id: Client ID
            usuario_id: User ID
            monto: Amount
            descripcion: Payment description
            proveedores: List of providers (stripe, mercadopago, paypal)

        Returns:
            Payment options dict with links for each provider
        """
        try:
            if not proveedores:
                proveedores = ["stripe"]

            payment_options = {
                "link_id": str(uuid4()),
                "monto": monto,
                "descripcion": descripcion,
                "opciones": {},
            }

            if "stripe" in proveedores:
                stripe_result = await self.generar_link_pago_stripe(
                    client_id, usuario_id, monto, descripcion
                )
                if "error" not in stripe_result:
                    payment_options["opciones"]["stripe"] = stripe_result

            if "mercadopago" in proveedores:
                mp_result = await self.generar_link_pago_mercadopago(
                    client_id, usuario_id, monto, descripcion
                )
                if "error" not in mp_result:
                    payment_options["opciones"]["mercadopago"] = mp_result

            if "paypal" in proveedores:
                paypal_result = await self.generar_link_pago_paypal(
                    client_id, usuario_id, monto, descripcion
                )
                if "error" not in paypal_result:
                    payment_options["opciones"]["paypal"] = paypal_result

            logger.info(
                f"Payment link generated with {len(payment_options['opciones'])} options",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "payment_options": payment_options,
            }

        except Exception as e:
            logger.error(f"Error generating payment link: {e}")
            return {"error": str(e)}

    async def obtener_estado_pago(
        self,
        link_id: str,
    ) -> dict[str, Any]:
        """
        Check payment status by link ID.

        Args:
            link_id: Payment link ID

        Returns:
            Payment status and details
        """
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

    async def reconciliar_pagos(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """
        Reconcile payments with providers (Stripe webhook handler).

        Args:
            client_id: Client ID

        Returns:
            Reconciliation summary
        """
        try:
            # Fetch pending payment links
            response = self.supabase.table("payment_links").select("*").eq(
                "client_id", client_id
            ).eq("status", "pending").execute()

            pending_links = response.data or []

            updated = 0

            for link in pending_links:
                # Check with provider
                if link["provider"] == "stripe":
                    session = stripe.checkout.Session.retrieve(
                        link["stripe_session_id"]
                    )

                    if session.payment_status == "paid":
                        self.supabase.table("payment_links").update(
                            {"status": "paid", "paid_at": datetime.utcnow().isoformat()}
                        ).eq("id", link["id"]).execute()

                        updated += 1

            logger.info(
                f"Reconciliation complete: {updated} payments confirmed",
                extra={"client_id": client_id},
            )

            return {"updated": updated, "total": len(pending_links)}

        except Exception as e:
            logger.error(f"Error reconciling payments: {e}")
            return {"error": str(e)}

    async def get_payment_links_usuario(
        self,
        client_id: str,
        usuario_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get all payment links for a user.

        Args:
            client_id: Client ID
            usuario_id: User ID

        Returns:
            List of payment links
        """
        try:
            response = self.supabase.table("payment_links").select("*").eq(
                "client_id", client_id
            ).eq("user_id", usuario_id).order(
                "created_at", desc=True
            ).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching payment links: {e}")
            return []
