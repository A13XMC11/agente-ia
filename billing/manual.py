"""
Billing: Manual payment methods — bank transfer and cash.

These methods require admin verification instead of automatic payment processing.
Flow for transferencia:
  1. Admin creates subscription with payment_method='transferencia'
  2. Client sees bank details on their billing page
  3. Client uploads transfer proof → status='proof_submitted'
  4. Admin approves/rejects → status='active' or back to 'pending_payment'
  5. Each month: dates roll forward, new ledger row in subscription_payments

Flow for efectivo:
  1. Admin creates subscription with payment_method='efectivo'
  2. Client sees cash payment instructions
  3. Client pays in person
  4. Admin clicks "Registrar pago / Renovar mes" → status stays 'active', dates roll
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ManualBilling:
    """Manages bank-transfer and cash subscription payments."""

    def __init__(self, supabase_client: Any) -> None:
        self.supabase = supabase_client

    def _get_subscription(self, client_id: str) -> Optional[dict[str, Any]]:
        resp = self.supabase.table("subscription").select("*").eq(
            "cliente_id", client_id
        ).order("created_at", desc=True).limit(1).execute()
        return resp.data[0] if resp.data else None

    def create_subscription(
        self,
        client_id: str,
        monthly_amount: float,
        payment_method: str,
    ) -> Optional[dict[str, Any]]:
        """
        Create (or reopen) a manual subscription and insert the first payment ledger row.

        Returns the created/updated subscription dict, or None on error.
        """
        if payment_method not in ("transferencia", "efectivo"):
            logger.error(f"Invalid payment_method for manual billing: {payment_method}")
            return None

        try:
            now = datetime.utcnow()
            period_end = now + timedelta(days=30)

            sub_data: dict[str, Any] = {
                "monthly_amount": monthly_amount,
                "payment_method": payment_method,
                "status": "pending_payment",
                "current_period_start": now.isoformat(),
                "current_period_end": period_end.isoformat(),
                "next_billing_date": period_end.isoformat(),
                "payment_failed_count": 0,
                "pending_proof_url": None,
                "pending_proof_submitted_at": None,
                "payphone_client_transaction_id": None,
                "payphone_transaction_id": None,
            }

            existing = self._get_subscription(client_id)
            if existing:
                self.supabase.table("subscription").update(sub_data).eq(
                    "id", existing["id"]
                ).execute()
                sub_id = existing["id"]
            else:
                result = self.supabase.table("subscription").insert({
                    **sub_data,
                    "cliente_id": client_id,
                    "created_at": now.isoformat(),
                }).execute()
                sub_id = result.data[0]["id"] if result.data else None

            if sub_id:
                self.supabase.table("subscription_payments").insert({
                    "subscription_id": sub_id,
                    "cliente_id": client_id,
                    "payment_method": payment_method,
                    "amount": monthly_amount,
                    "status": "pending",
                    "period_start": now.isoformat(),
                    "period_end": period_end.isoformat(),
                }).execute()

            logger.info(f"Manual subscription created for {client_id} via {payment_method}")
            return self._get_subscription(client_id)

        except Exception as e:
            logger.error(f"Error creating manual subscription for {client_id}: {e}")
            return None

    def submit_proof(self, client_id: str, proof_url: str) -> bool:
        """
        Record that the client submitted a transfer proof.
        Transitions subscription to 'proof_submitted' and updates the pending payment row.
        """
        try:
            now = datetime.utcnow()

            self.supabase.table("subscription").update({
                "status": "proof_submitted",
                "pending_proof_url": proof_url,
                "pending_proof_submitted_at": now.isoformat(),
            }).eq("cliente_id", client_id).execute()

            sub = self._get_subscription(client_id)
            if sub:
                self.supabase.table("subscription_payments").update({
                    "status": "proof_submitted",
                    "proof_url": proof_url,
                }).eq("subscription_id", sub["id"]).eq(
                    "status", "pending"
                ).execute()

            logger.info(f"Transfer proof submitted for client {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error submitting proof for {client_id}: {e}")
            return False

    def verify_payment(
        self,
        client_id: str,
        approve: bool,
        verified_by: str,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Admin approves or rejects the submitted proof.

        On approval: subscription → 'active', clientes.estado → 'activo' (if paused).
        On rejection: subscription → 'pending_payment', proof fields cleared.
        """
        try:
            sub = self._get_subscription(client_id)
            if not sub:
                logger.warning(f"No subscription found for {client_id}")
                return False

            now = datetime.utcnow()

            if approve:
                self.supabase.table("subscription").update({
                    "status": "active",
                    "last_payment_date": now.isoformat(),
                    "pending_proof_url": None,
                    "pending_proof_submitted_at": None,
                    "payment_failed_count": 0,
                }).eq("cliente_id", client_id).execute()

                # Mirror payphone.py:211-213 — reactivate paused client
                self.supabase.table("clientes").update({
                    "estado": "activo",
                }).eq("id", client_id).eq("estado", "pausado").execute()

                self.supabase.table("subscription_payments").update({
                    "status": "paid",
                    "verified_by": verified_by,
                    "verified_at": now.isoformat(),
                    "notes": notes,
                }).eq("subscription_id", sub["id"]).in_(
                    "status", ["proof_submitted", "pending"]
                ).execute()

                logger.info(f"Manual payment approved for client {client_id} by {verified_by}")
            else:
                self.supabase.table("subscription").update({
                    "status": "pending_payment",
                    "pending_proof_url": None,
                    "pending_proof_submitted_at": None,
                }).eq("cliente_id", client_id).execute()

                self.supabase.table("subscription_payments").update({
                    "status": "rejected",
                    "verified_by": verified_by,
                    "verified_at": now.isoformat(),
                    "notes": notes,
                }).eq("subscription_id", sub["id"]).in_(
                    "status", ["proof_submitted", "pending"]
                ).execute()

                logger.info(f"Manual payment rejected for client {client_id} by {verified_by}")

            return True

        except Exception as e:
            logger.error(f"Error verifying payment for {client_id}: {e}")
            return False

    def renew(self, client_id: str, verified_by: str) -> bool:
        """
        Roll subscription period forward one month and insert a new payment ledger row.

        For efectivo: new row is marked 'paid' immediately.
        For transferencia: new row is 'pending' (client must submit proof again).
        Does NOT insert a new subscription row — updates the existing one.
        """
        try:
            sub = self._get_subscription(client_id)
            if not sub:
                logger.warning(f"No subscription found for {client_id}")
                return False

            now = datetime.utcnow()
            new_period_start = now
            new_period_end = now + timedelta(days=30)
            payment_method = sub.get("payment_method", "transferencia")

            self.supabase.table("subscription").update({
                "status": "active",
                "current_period_start": new_period_start.isoformat(),
                "current_period_end": new_period_end.isoformat(),
                "next_billing_date": new_period_end.isoformat(),
                "last_payment_date": now.isoformat(),
                "pending_proof_url": None,
                "pending_proof_submitted_at": None,
            }).eq("cliente_id", client_id).execute()

            new_payment_status = "paid" if payment_method == "efectivo" else "pending"

            self.supabase.table("subscription_payments").insert({
                "subscription_id": sub["id"],
                "cliente_id": client_id,
                "payment_method": payment_method,
                "amount": sub.get("monthly_amount", 0),
                "status": new_payment_status,
                "period_start": new_period_start.isoformat(),
                "period_end": new_period_end.isoformat(),
                "verified_by": verified_by if payment_method == "efectivo" else None,
                "verified_at": now.isoformat() if payment_method == "efectivo" else None,
            }).execute()

            logger.info(f"Subscription renewed for client {client_id} by {verified_by}")
            return True

        except Exception as e:
            logger.error(f"Error renewing subscription for {client_id}: {e}")
            return False

    def get_due_subscriptions(self) -> list[dict[str, Any]]:
        """
        Return manual subscriptions due or overdue within 3 days.
        Used by the admin 'renovaciones pendientes' list.
        """
        try:
            threshold = (datetime.utcnow() + timedelta(days=3)).isoformat()

            resp = self.supabase.table("subscription").select(
                "*, clientes(nombre_empresa, email)"
            ).in_(
                "payment_method", ["transferencia", "efectivo"]
            ).lte(
                "next_billing_date", threshold
            ).not_.eq(
                "status", "cancelled"
            ).order("next_billing_date").execute()

            return resp.data or []

        except Exception as e:
            logger.error(f"Error fetching due subscriptions: {e}")
            return []

    @staticmethod
    def get_platform_bank_info() -> dict[str, str]:
        """Return LanLabs bank account details from environment variables."""
        return {
            "banco": os.getenv("LANLABS_BANCO", ""),
            "tipo_cuenta": os.getenv("LANLABS_TIPO_CUENTA", ""),
            "numero_cuenta": os.getenv("LANLABS_NUMERO_CUENTA", ""),
            "titular": os.getenv("LANLABS_TITULAR", ""),
            "ruc": os.getenv("LANLABS_RUC", ""),
            "cash_address": os.getenv("LANLABS_CASH_ADDRESS", ""),
        }
