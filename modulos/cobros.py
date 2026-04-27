"""
Payment module: receipt verification with GPT-4o Vision and payment tracking.

Handles payment receipt verification, fraud detection, and payment registration.
"""

import base64
import json
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CobrosModule:
    """Payment and receipt verification operations."""

    def __init__(self, supabase_client: Any, openai_client: AsyncOpenAI):
        """
        Initialize payment module.

        Args:
            supabase_client: Supabase client instance
            openai_client: OpenAI async client for Vision API
        """
        self.supabase = supabase_client
        self.openai = openai_client
        self.fraud_threshold = float(
            os.environ.get("PAYMENT_FRAUD_SCORE_THRESHOLD", 0.7)
        )

    async def enviar_datos_bancarios(
        self,
        client_id: str,
        user_id: str,
        numero_cuenta: str,
        nombre_banco: str,
        tipo_cuenta: str = "checking",
        monto_esperado: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Send bank account details for customer payment.

        Args:
            client_id: Client ID
            user_id: Customer user ID
            numero_cuenta: Bank account number
            nombre_banco: Bank name
            tipo_cuenta: Account type (checking/savings)
            monto_esperado: Expected payment amount

        Returns:
            Message with account details and payment instructions
        """
        try:
            payment_request = {
                "id": str(uuid4()),
                "client_id": client_id,
                "user_id": user_id,
                "account_number": numero_cuenta,
                "bank_name": nombre_banco,
                "account_type": tipo_cuenta,
                "expected_amount": monto_esperado,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat(),  # Valid for 24 hours
            }

            self.supabase.table("payment_requests").insert(payment_request).execute()

            # Format account details message
            message = f"""
📋 **Datos Bancarios para Transferencia**

Banco: {nombre_banco}
Tipo de Cuenta: {tipo_cuenta.capitalize()}
Número de Cuenta: {numero_cuenta}
"""
            if monto_esperado:
                message += f"Monto a Transferir: ${monto_esperado:.2f}\n"

            message += """
⏰ Esta información es válida por 24 horas.
Después de realizar la transferencia, envía una foto del comprobante.
            """

            logger.info(
                f"Bank details sent to user {user_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "message": message,
                "payment_request_id": payment_request["id"],
            }

        except Exception as e:
            logger.error(f"Error sending bank details: {e}")
            return {"error": str(e)}

    async def analyze_receipt_image(
        self,
        client_id: str,
        user_id: str,
        image_url: str,
    ) -> dict[str, Any]:
        """
        Analyze payment receipt image with GPT-4o Vision.

        Extracts: amount, date, account number, transfer reference.
        Detects fraud indicators.

        Args:
            client_id: Client ID
            user_id: User ID
            image_url: Receipt image URL

        Returns:
            Analysis with extracted data and fraud score
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = base64.b64encode(response.content).decode("utf-8")

            # Analyze with Vision
            vision_response = await self.openai.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                            },
                            {
                                "type": "text",
                                "text": """Analiza esta imagen de comprobante de transferencia bancaria y extrae:
1. Monto: cantidad y moneda
2. Fecha de la transferencia
3. Número de cuenta destino (últimos 4 dígitos)
4. Referencia o código de transacción
5. Nombre del banco (si es visible)
6. Indicadores de fraude: ¿parece auténtico? ¿hay signos de edición?

Responde en JSON:
{
    "monto": 0.0,
    "moneda": "USD",
    "fecha": "YYYY-MM-DD",
    "cuenta_destino": "****1234",
    "referencia": "REF-123456",
    "banco": "Banco",
    "parece_autentico": true,
    "signos_edicion": false,
    "confianza": 0.95,
    "notas": "..."
}""",
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )

            # Parse response
            content = vision_response.choices[0].message.content
            # Extract JSON from response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            json_str = content[json_start:json_end]
            analysis = json.loads(json_str)

            # Calculate fraud score
            fraud_score = 1.0 - analysis.get("confianza", 0.5)
            if analysis.get("signos_edicion"):
                fraud_score += 0.2
            if not analysis.get("parece_autentico"):
                fraud_score = 0.95

            fraud_score = min(fraud_score, 1.0)

            result = {
                "analysis": analysis,
                "fraud_score": fraud_score,
                "is_valid": fraud_score < self.fraud_threshold,
                "verification_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Receipt analyzed for user {user_id}: fraud_score={fraud_score:.2f}",
                extra={"client_id": client_id},
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing receipt: {e}")
            return {"error": str(e), "is_valid": False}

    async def registrar_pago(
        self,
        client_id: str,
        user_id: str,
        monto: float,
        referencia: str,
        metodo: str = "transfer",
        imagen_comprobante: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Register a payment after verification.

        Args:
            client_id: Client ID
            user_id: User ID
            monto: Payment amount
            referencia: Transaction reference
            metodo: Payment method (transfer, card, etc)
            imagen_comprobante: Receipt image URL for verification

        Returns:
            Payment confirmation with receipt ID
        """
        try:
            # Verify receipt if provided
            is_valid = True
            fraud_score = 0.0

            if imagen_comprobante:
                receipt_analysis = await self.analyze_receipt_image(
                    client_id, user_id, imagen_comprobante
                )

                if "error" not in receipt_analysis:
                    is_valid = receipt_analysis.get("is_valid", False)
                    fraud_score = receipt_analysis.get("fraud_score", 0.0)

            if not is_valid and imagen_comprobante:
                logger.warning(
                    f"Payment verification failed for user {user_id}: fraud_score={fraud_score}",
                    extra={"client_id": client_id},
                )
                return {
                    "success": False,
                    "error": "El comprobante no pasó la verificación de autenticidad.",
                    "fraud_score": fraud_score,
                }

            # Register payment
            payment = {
                "id": str(uuid4()),
                "client_id": client_id,
                "user_id": user_id,
                "amount": monto,
                "currency": "USD",
                "reference": referencia,
                "method": metodo,
                "status": "verified" if is_valid else "pending_review",
                "fraud_score": fraud_score,
                "receipt_url": imagen_comprobante,
                "verified_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("payments").insert(payment).execute()

            # Update user balance if valid
            if is_valid:
                # Fetch user's account
                user_response = self.supabase.table("users").select(
                    "account_balance"
                ).eq("id", user_id).eq("client_id", client_id).single().execute()

                current_balance = user_response.data.get("account_balance", 0)
                new_balance = current_balance + monto

                self.supabase.table("users").update(
                    {"account_balance": new_balance}
                ).eq("id", user_id).execute()

            logger.info(
                f"Payment registered: {payment['id']} for user {user_id}, amount=${monto}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "payment_id": payment["id"],
                "amount": monto,
                "status": payment["status"],
                "message": "Pago registrado exitosamente ✅"
                if is_valid
                else "Pago pendiente de revisión",
            }

        except Exception as e:
            logger.error(f"Error registering payment: {e}")
            return {"error": str(e)}

    async def get_payment_history(
        self,
        client_id: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get payment history for a user.

        Args:
            client_id: Client ID
            user_id: User ID
            limit: Max records to return

        Returns:
            List of payments ordered by date (newest first)
        """
        try:
            response = self.supabase.table("payments").select("*").eq(
                "client_id", client_id
            ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching payment history: {e}")
            return []

    async def get_payment_status(
        self,
        client_id: str,
        referencia: str,
    ) -> dict[str, Any]:
        """
        Check payment status by reference.

        Args:
            client_id: Client ID
            referencia: Payment reference

        Returns:
            Payment status and details
        """
        try:
            response = self.supabase.table("payments").select("*").eq(
                "client_id", client_id
            ).eq("reference", referencia).single().execute()

            payment = response.data

            return {
                "payment_id": payment["id"],
                "status": payment["status"],
                "amount": payment["amount"],
                "verified_at": payment["verified_at"],
                "fraud_score": payment.get("fraud_score", 0),
            }

        except Exception as e:
            logger.error(f"Error fetching payment status: {e}")
            return {"error": str(e)}
