"""
Payment module: complete bank transfer verification workflow.

Handles:
- Bank account data retrieval and formatting
- Payment receipt analysis with GPT-4o Vision
- Fraud detection and deduplication
- Owner approval/rejection flow
- WhatsApp and dashboard notifications
"""

import base64
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CobrosModule:
    """Complete bank transfer verification and payment processing."""

    def __init__(
        self,
        supabase_client: Any,
        openai_client: AsyncOpenAI,
        redis_client: Any = None,
        whatsapp_handler: Any = None,
    ):
        """
        Initialize payment module.

        Args:
            supabase_client: Supabase client instance
            openai_client: OpenAI async client (for gpt-4o vision)
            redis_client: Redis client for pending amount state (24h TTL)
            whatsapp_handler: WhatsApp handler for owner notifications
        """
        self.supabase = supabase_client
        self.openai = openai_client
        self.redis = redis_client
        self.whatsapp = whatsapp_handler
        self.fraud_threshold = float(
            os.environ.get("PAYMENT_FRAUD_SCORE_THRESHOLD", 0.7)
        )
        self._http = httpx.AsyncClient(timeout=30.0)

    async def enviar_datos_bancarios(
        self,
        client_id: str,
        sender_id: str,
        monto_esperado: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Send bank account details for customer payment transfer.

        Reads from datos_bancarios table and stores expected amount in Redis
        for later validation. Returns message to be sent directly in chat.

        Args:
            client_id: Client ID
            sender_id: Sender/customer ID
            monto_esperado: Expected payment amount (stored for 24h validation)

        Returns:
            Dict with mensaje (formatted bank details to show in WhatsApp) and exito flag
        """
        try:
            # 1. Read bank details from datos_bancarios
            response = self.supabase.table("datos_bancarios").select(
                "banco, tipo_cuenta, numero_cuenta, titular, ruc"
            ).eq("cliente_id", client_id).eq("activo", True).limit(1).execute()

            if not response.data:
                return {
                    "exito": False,
                    "mensaje": "No hay datos bancarios configurados para este negocio",
                }

            cuenta = response.data[0]

            # 2. Store pending amount in Redis for 24h (for later validation)
            if self.redis and monto_esperado:
                key = f"cobros:pending:{client_id}:{sender_id}"
                await self.redis.setex(key, 86400, str(monto_esperado))

            # 3. Format message for WhatsApp chat (not email)
            mensaje = (
                f"💳 *Datos para tu transferencia:*\n\n"
                f"🏦 Banco: {cuenta['banco']}\n"
                f"📋 Tipo: {cuenta['tipo_cuenta'].capitalize()}\n"
                f"🔢 Número: {cuenta['numero_cuenta']}\n"
                f"👤 Titular: {cuenta['titular']}\n"
            )
            if cuenta.get("ruc"):
                mensaje += f"🪪 RUC: {cuenta['ruc']}\n"
            if monto_esperado:
                mensaje += f"\n💰 Monto a Transferir: ${monto_esperado:.2f}"
            mensaje += (
                "\n\nUna vez realizada la transferencia, "
                "envíame la foto del comprobante 🙌"
            )

            logger.info(
                f"Bank details sent to {sender_id} in WhatsApp chat",
                extra={"client_id": client_id},
            )

            return {"exito": True, "mensaje": mensaje}

        except Exception as e:
            logger.error(f"Error sending bank details: {e}")
            return {"exito": False, "mensaje": f"Error: {str(e)}"}

    async def _exchange_meta_media_id(
        self,
        media_id: str,
        client_id: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Exchange Meta media object ID for a real downloadable URL.

        WhatsApp sends media object IDs that require authentication to access.
        This method gets the client's access token and exchanges it for a real URL.

        Args:
            media_id: Meta media object ID
            client_id: Client ID (to fetch access token)

        Returns:
            Tuple of (media_url, bearer_token) or (None, None) on error
        """
        try:
            # Get access token from canales_config
            resp = (
                self.supabase.table("canales_config")
                .select("token")
                .eq("cliente_id", client_id)
                .eq("canal", "whatsapp")
                .limit(1)
                .execute()
            )

            token = None
            if resp.data:
                token = resp.data[0].get("token")
            if not token:
                token = os.getenv("META_ACCESS_TOKEN")
            if not token:
                raise ValueError("No WhatsApp access token available")

            # Get media URL from Meta Graph API
            meta_resp = await self._http.get(
                f"https://graph.facebook.com/v21.0/{media_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            meta_resp.raise_for_status()
            media_url = meta_resp.json().get("url")

            if not media_url:
                raise ValueError("Meta API did not return a media URL")

            return media_url, token

        except Exception as e:
            logger.error(f"Failed to exchange Meta media ID {media_id}: {e}")
            return None, None

    async def analyze_receipt_image(
        self,
        client_id: str,
        sender_id: str,
        media_id_or_url: str,
        is_meta_media_id: bool = False,
    ) -> dict[str, Any]:
        """
        Analyze payment receipt image with GPT-4o Vision.

        Extracts transaction details and detects fraud indicators.

        Args:
            client_id: Client ID
            sender_id: Sender ID
            media_id_or_url: Meta media ID or direct URL
            is_meta_media_id: True if media_id_or_url is a Meta media object ID

        Returns:
            Analysis dict with extracted data and fraud score
        """
        try:
            # Exchange Meta media ID for real URL if needed
            if is_meta_media_id:
                real_url, token = await self._exchange_meta_media_id(
                    media_id_or_url, client_id
                )
                if not real_url:
                    return {"error": "No se pudo obtener la imagen", "is_valid": False}
            else:
                real_url = media_id_or_url
                token = None

            # Download image with auth header if needed
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            img_resp = await self._http.get(real_url, headers=headers, timeout=30)
            img_resp.raise_for_status()
            image_data = base64.b64encode(img_resp.content).decode("utf-8")
            mime = img_resp.headers.get("content-type", "image/jpeg")

            # Analyze with GPT-4o Vision (native vision, not deprecated gpt-4-vision-preview)
            vision_response = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{image_data}"},
                            },
                            {
                                "type": "text",
                                "text": """Analiza este comprobante de transferencia bancaria y extrae en JSON:
{
  "monto": 0.0,
  "moneda": "USD",
  "banco_origen": "Banco Pichincha",
  "banco_destino": "Banco Guayaquil",
  "titular_origen": "Nombre Apellido",
  "numero_transaccion": "REF-123456",
  "fecha": "YYYY-MM-DD",
  "es_valido": true,
  "signos_edicion": false,
  "confianza": 0.95,
  "notas": "..."
}
Responde SOLO con el JSON, sin comentarios adicionales.""",
                            },
                        ],
                    }
                ],
                max_tokens=600,
            )

            # Parse JSON response
            content = vision_response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            json_str = content[json_start:json_end]
            analysis = json.loads(json_str)

            # Calculate fraud score
            confianza = analysis.get("confianza", 0.5)
            fraud_score = 1.0 - confianza
            if analysis.get("signos_edicion"):
                fraud_score += 0.2
            if not analysis.get("es_valido"):
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
                f"Receipt analyzed: fraud_score={fraud_score:.2f}",
                extra={"client_id": client_id, "sender_id": sender_id},
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing receipt: {e}")
            return {"error": str(e), "is_valid": False}

    async def registrar_pago(
        self,
        client_id: str,
        sender_id: str,
        conversacion_id: str,
        media_id: str,
        phone_number_id: str,
    ) -> dict[str, Any]:
        """
        Register and verify a payment after receipt analysis.

        Orchestrates the full workflow: image analysis → deduplication → date check →
        amount validation → storage → notifications.

        Args:
            client_id: Client ID
            sender_id: Customer sender ID
            conversacion_id: Conversation ID
            media_id: Meta media ID or image URL
            phone_number_id: Phone number ID for sending notifications

        Returns:
            Result dict with outcome and message for user
        """
        try:
            # 1. Analyze receipt image
            analysis_result = await self.analyze_receipt_image(
                client_id=client_id,
                sender_id=sender_id,
                media_id_or_url=media_id,
                is_meta_media_id=True,
            )

            if "error" in analysis_result:
                return {
                    "success": False,
                    "outcome": "error",
                    "message": analysis_result["error"],
                }

            analysis = analysis_result["analysis"]
            fraud_score = analysis_result["fraud_score"]
            numero_transaccion = analysis.get("numero_transaccion", "")
            monto_recibido = float(analysis.get("monto", 0))

            # 2. Check for duplicate (comprobantes_procesados dedup by numero_transaccion + client_id)
            if numero_transaccion:
                dup = (
                    self.supabase.table("comprobantes_procesados")
                    .select("id")
                    .eq("numero_transaccion", numero_transaccion)
                    .eq("cliente_id", client_id)
                    .limit(1)
                    .execute()
                )
                if dup.data:
                    return {
                        "success": False,
                        "outcome": "duplicate",
                        "message": "Este comprobante ya fue procesado. Si tienes dudas, contacta al negocio.",
                    }

            # 3. Check date is recent (max 24h)
            fecha_str = analysis.get("fecha", "")
            if fecha_str:
                try:
                    fecha_pago = datetime.fromisoformat(fecha_str)
                    if datetime.utcnow() - fecha_pago > timedelta(hours=24):
                        return {
                            "success": False,
                            "outcome": "expired",
                            "message": "El comprobante tiene más de 24 horas. Por favor realiza una nueva transferencia.",
                        }
                except ValueError:
                    pass  # If date can't be parsed, proceed

            # 4. Check amount matches pending (from Redis)
            monto_esperado = None
            amount_matches = True
            if self.redis:
                key = f"cobros:pending:{client_id}:{sender_id}"
                val = await self.redis.get(key)
                if val:
                    monto_esperado = float(val)
                    amount_matches = abs(monto_recibido - monto_esperado) < 0.01

            # 5. Determine outcome based on validations
            if fraud_score >= self.fraud_threshold:
                outcome = "invalid"
            else:
                outcome = "valid"

            # 6. Save to pagos table with correct column names
            pago_id = str(uuid4())
            # ALL valid comprobantes require owner approval before confirming to user
            estado = "pendiente" if outcome == "valid" else "rechazado"

            pago_record = {
                "id": pago_id,
                "cliente_id": client_id,
                "conversacion_id": conversacion_id or None,
                "monto": monto_recibido,
                "moneda": analysis.get("moneda", "USD"),
                "metodo_pago": "transferencia",
                "estado": estado,
                "numero_transaccion": numero_transaccion or None,
                "banco_origen": analysis.get("banco_origen") or None,
                "banco_destino": analysis.get("banco_destino") or None,
                "fraud_score": fraud_score,
                "created_at": datetime.utcnow().isoformat(),
            }

            # 7. Only save valid comprobantes (pending owner approval)
            if outcome == "valid":
                self.supabase.table("pagos").insert(pago_record).execute()

            # 8. Notify owner
            await self._notify_owner(
                client_id, phone_number_id, pago_id, outcome, monto_recibido, sender_id
            )

            # 9. Return message for user
            return {
                "success": True,
                "outcome": outcome,
                "pago_id": pago_id,
                "message": self._user_message_for_outcome(outcome),
            }

        except Exception as e:
            logger.error(f"Error registering payment: {e}")
            return {"success": False, "outcome": "error", "message": str(e)}

    async def _notify_owner(
        self,
        client_id: str,
        phone_number_id: str,
        pago_id: str,
        outcome: str,
        monto: float,
        sender_id: str,
    ) -> None:
        """
        Send owner notification via WhatsApp with approval instructions.

        Only notifies for valid comprobantes (requires approval before confirming to user).
        Invalid/duplicate payments are rejected without notifying owner.

        Args:
            client_id: Client ID
            phone_number_id: WhatsApp phone number ID
            pago_id: Payment ID
            outcome: valid | invalid
            monto: Payment amount
            sender_id: Customer sender ID
        """
        if not self.whatsapp or outcome != "valid":
            return

        try:
            # Get owner phone from clientes table
            resp = (
                self.supabase.table("clientes")
                .select("whatsapp_dueño, nombre_negocio")
                .eq("id", client_id)
                .single()
                .execute()
            )
            if not resp.data:
                return

            owner_phone = resp.data.get("whatsapp_dueño")
            if not owner_phone:
                return

            msg = (
                f"📋 *Nuevo comprobante para revisar*\n\n"
                f"Monto: ${monto:.2f}\n"
                f"De: {sender_id}\n"
                f"ID: {pago_id}\n\n"
                f"Responde:\n"
                f"*aprobar {pago_id}* — Confirmar el pago\n"
                f"*rechazar {pago_id}* — Rechazar el pago"
            )

            # Send via WhatsApp handler
            await self.whatsapp.send_message(
                phone_number_id=phone_number_id,
                recipient_phone=owner_phone,
                text=msg,
                client_id=client_id,
            )

        except Exception as e:
            logger.error(f"Failed to notify owner: {e}")

    async def procesar_respuesta_propietario(
        self,
        client_id: str,
        phone_number_id: str,
        owner_phone: str,
        text: str,
    ) -> bool:
        """
        Process owner approval/rejection of a pending payment.

        Called from WhatsApp handler when owner replies with:
        - "aprobar {pago_id}" → mark as verified, notify customer
        - "rechazar {pago_id}" → mark as rejected, notify customer

        Args:
            client_id: Client ID
            phone_number_id: WhatsApp phone number ID
            owner_phone: Owner's phone number
            text: Message text

        Returns:
            True if was a valid approval command, False otherwise
        """
        # Match pattern: "aprobar/rechazar {uuid}"
        match = re.match(
            r"^(aprobar|rechazar)\s+([a-f0-9\-]{36})$", text.strip().lower()
        )
        if not match:
            return False

        action = match.group(1)  # 'aprobar' or 'rechazar'
        pago_id = match.group(2)

        nuevo_estado = "verificado" if action == "aprobar" else "rechazado"

        try:
            # Update pagos record
            resp = (
                self.supabase.table("pagos")
                .update({
                    "estado": nuevo_estado,
                    "fecha_verificacion": datetime.utcnow().isoformat(),
                })
                .eq("id", pago_id)
                .eq("cliente_id", client_id)
                .select("conversacion_id, monto, numero_transaccion")
                .execute()
            )

            if not resp.data:
                return False

            pago = resp.data[0]

            # If approved: save to comprobantes_procesados for deduplication
            if nuevo_estado == "verificado" and pago.get("numero_transaccion"):
                try:
                    self.supabase.table("comprobantes_procesados").insert({
                        "numero_transaccion": pago["numero_transaccion"],
                        "cliente_id": client_id,
                        "monto": pago["monto"],
                        "fecha_procesado": datetime.utcnow().isoformat(),
                    }).execute()
                except Exception as e:
                    logger.warning(f"Could not save comprobante to dedup table: {e}")

            # Notify customer
            if self.whatsapp and pago.get("conversacion_id"):
                try:
                    conv = (
                        self.supabase.table("conversaciones")
                        .select("usuario_id, sender_id")
                        .eq("id", pago["conversacion_id"])
                        .single()
                        .execute()
                    )
                    if conv.data:
                        customer_phone = conv.data.get("sender_id")
                        if customer_phone:
                            if nuevo_estado == "verificado":
                                user_msg = (
                                    f"✅ *¡Pago confirmado!*\n\n"
                                    f"Tu pago de ${pago['monto']:.2f} ha sido confirmado. ¡Gracias! 🎉"
                                )
                            else:
                                user_msg = (
                                    f"❌ *Pago rechazado*\n\n"
                                    f"No pudimos verificar tu pago. Por favor intenta de nuevo o "
                                    f"contacta directamente al negocio."
                                )
                            await self.whatsapp.send_message(
                                phone_number_id=phone_number_id,
                                recipient_phone=customer_phone,
                                text=user_msg,
                                client_id=client_id,
                            )
                except Exception as e:
                    logger.error(f"Failed to notify customer: {e}")

            return True

        except Exception as e:
            logger.error(f"Error processing owner response: {e}")
            return False

    def _user_message_for_outcome(self, outcome: str) -> str:
        """Return user-friendly message based on payment outcome."""
        messages = {
            "valid": (
                "⏳ *Recibimos tu comprobante, estamos verificando el pago.* "
                "Te confirmamos en breve 🙏"
            ),
            "invalid": "❌ *No pudimos validar tu comprobante.* Por favor intenta de nuevo o contacta al negocio.",
            "duplicate": "⚠️ *Este comprobante ya fue procesado.* Si tienes dudas, contacta al negocio.",
            "expired": "⏰ *El comprobante es muy antiguo.* Realiza una nueva transferencia.",
            "error": "Error al procesar el pago. Por favor intenta nuevamente.",
        }
        return messages.get(outcome, "Hubo un problema procesando tu pago.")
