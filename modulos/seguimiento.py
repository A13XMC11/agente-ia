"""
Automatic follow-up system: 6 types of follow-ups (cold leads, hot leads, appointment reminders, post-sale, reactivation).

REQUIRED SQL MIGRATION before deployment:
    ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_24h_enviado BOOLEAN DEFAULT FALSE;
    ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_1h_enviado BOOLEAN DEFAULT FALSE;
    ALTER TABLE alertas ADD COLUMN IF NOT EXISTS referencia_id TEXT;
"""

import logging
from datetime import datetime, timedelta, time, timezone
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class SeguimientoModule:
    """Automatic follow-up system for leads and appointments."""

    def __init__(self, supabase_client: Any):
        """Initialize follow-up module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

    async def verificar_seguimientos_pendientes(self, cliente_id: str) -> dict[str, int]:
        """
        Verify and send all pending follow-ups for a client.

        Entry point called every 30 minutes by scheduler.

        Args:
            cliente_id: Client ID

        Returns:
            Summary: {"frios": int, "calientes": int, "cita_24h": int, "cita_1h": int, "post_venta": int, "reactivacion": int}
        """
        try:
            logger.info(f"Verificando seguimientos para cliente {cliente_id}")

            result = {
                "frios": await self._verificar_prospectos_frios(cliente_id),
                "calientes": await self._verificar_leads_calientes(cliente_id),
                "cita_24h": await self._verificar_recordatorio_cita_24h(cliente_id),
                "cita_1h": await self._verificar_recordatorio_cita_1h(cliente_id),
                "post_venta": await self._verificar_post_venta(cliente_id),
                "reactivacion": await self._verificar_reactivacion(cliente_id),
            }

            total = sum(result.values())
            if total > 0:
                logger.info(f"Seguimientos enviados para {cliente_id}: {total} total", extra={
                    "cliente_id": cliente_id,
                    "resumen": result,
                })

            return result

        except Exception as e:
            logger.error(f"Error verificando seguimientos para {cliente_id}: {e}", exc_info=True)
            return {
                "frios": 0, "calientes": 0, "cita_24h": 0, "cita_1h": 0, "post_venta": 0, "reactivacion": 0
            }

    async def _verificar_prospectos_frios(self, cliente_id: str) -> int:
        """
        Cold lead follow-up: score < 5, no response in 24h.

        Message: "Hola {nombre} 👋 Hace un momento hablamos..."
        """
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            hace_24h = now - timedelta(hours=24)

            # Get cold leads (score < 5, not discarded)
            response = self.supabase.table("leads").select(
                "id, nombre, telefono"
            ).eq(
                "cliente_id", cliente_id
            ).lt("score", 5).neq("estado", "descartado").limit(200).execute()

            leads = response.data or []
            logger.debug(f"Found {len(leads)} cold leads for client {cliente_id}")

            for lead in leads:
                lead_id = lead.get("id")
                nombre = lead.get("nombre", "Amigo/a")
                telefono = lead.get("telefono")

                if not telefono:
                    continue

                # Check last message time
                conv_response = self.supabase.table("conversaciones").select(
                    "fecha_ultimo_mensaje"
                ).eq("cliente_id", cliente_id).eq(
                    "usuario_id", telefono
                ).order("fecha_ultimo_mensaje", desc=True).limit(1).execute()

                if not conv_response.data:
                    continue

                conv = conv_response.data[0]
                fecha_str = conv.get("fecha_ultimo_mensaje")
                if not fecha_str:
                    continue

                fecha_ultimo = datetime.fromisoformat(fecha_str)

                # Check if 24h have passed and no duplicate alert
                if fecha_ultimo < hace_24h:
                    if not await self._ya_enviado(cliente_id, "seguimiento_frio", lead_id, ventana_horas=24):
                        mensaje = (
                            f"Hola {nombre} 👋 Hace un momento hablamos sobre nuestros servicios. "
                            f"¿Pudiste revisar la información? Estoy aquí para resolver cualquier duda 😊"
                        )
                        if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                            await self._guardar_alerta_enviada(cliente_id, "seguimiento_frio", lead_id, mensaje)
                            enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_prospectos_frios for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_leads_calientes(self, cliente_id: str) -> int:
        """
        Hot lead follow-up: score >= 7, no response in 2h.

        Message: "Hola {nombre} 🔥 Vi que estabas muy interesado..."
        """
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            hace_2h = now - timedelta(hours=2)

            response = self.supabase.table("leads").select(
                "id, nombre, telefono"
            ).eq(
                "cliente_id", cliente_id
            ).gte("score", 7).limit(200).execute()

            leads = response.data or []
            logger.debug(f"Found {len(leads)} hot leads for client {cliente_id}")

            for lead in leads:
                lead_id = lead.get("id")
                nombre = lead.get("nombre", "Amigo/a")
                telefono = lead.get("telefono")

                if not telefono:
                    continue

                conv_response = self.supabase.table("conversaciones").select(
                    "fecha_ultimo_mensaje"
                ).eq("cliente_id", cliente_id).eq(
                    "usuario_id", telefono
                ).order("fecha_ultimo_mensaje", desc=True).limit(1).execute()

                if not conv_response.data:
                    continue

                conv = conv_response.data[0]
                fecha_str = conv.get("fecha_ultimo_mensaje")
                if not fecha_str:
                    continue

                fecha_ultimo = datetime.fromisoformat(fecha_str)

                if fecha_ultimo < hace_2h:
                    if not await self._ya_enviado(cliente_id, "seguimiento_caliente", lead_id, ventana_horas=24):
                        mensaje = (
                            f"Hola {nombre} 🔥 Vi que estabas muy interesado en nuestros servicios. "
                            f"¿Tienes alguna pregunta que pueda resolver ahora mismo?"
                        )
                        if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                            await self._guardar_alerta_enviada(cliente_id, "seguimiento_caliente", lead_id, mensaje)
                            enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_leads_calientes for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_recordatorio_cita_24h(self, cliente_id: str) -> int:
        """
        Appointment reminder 24h before at 9am.

        Message: "Hola {nombre} 👋 Te recuerdo que mañana tienes..."
        """
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            tomorrow = (now + timedelta(days=1)).date()

            # Get confirmed appointments for tomorrow
            response = self.supabase.table("citas").select(
                "id, nombre_cliente, hora, telefono_cliente, fecha"
            ).eq(
                "cliente_id", cliente_id
            ).eq("estado", "confirmada").eq(
                "recordatorio_24h_enviado", False
            ).limit(200).execute()

            citas = response.data or []

            for cita in citas:
                cita_id = cita.get("id")
                fecha_str = cita.get("fecha")

                if not fecha_str:
                    continue

                fecha_cita = datetime.fromisoformat(fecha_str).date()

                if fecha_cita == tomorrow:
                    nombre = cita.get("nombre_cliente", "Amigo/a")
                    hora = cita.get("hora", "la hora acordada")
                    telefono = cita.get("telefono_cliente")

                    if telefono:
                        mensaje = (
                            f"Hola {nombre} 👋 Te recuerdo que mañana tienes una cita con nosotros a las {hora}. "
                            f"¿Confirmas tu asistencia? 😊"
                        )
                        if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                            self.supabase.table("citas").update(
                                {"recordatorio_24h_enviado": True}
                            ).eq("id", cita_id).execute()
                            enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_recordatorio_cita_24h for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_recordatorio_cita_1h(self, cliente_id: str) -> int:
        """
        Appointment reminder 1h before.

        Message: "Hola {nombre} ⏰ En una hora tienes tu cita..."
        """
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            today = now.date()
            hora_actual = now.time()

            response = self.supabase.table("citas").select(
                "id, nombre_cliente, hora, telefono_cliente, fecha"
            ).eq(
                "cliente_id", cliente_id
            ).eq("estado", "confirmada").eq(
                "recordatorio_1h_enviado", False
            ).limit(200).execute()

            citas = response.data or []

            for cita in citas:
                cita_id = cita.get("id")
                fecha_str = cita.get("fecha")
                hora_str = cita.get("hora")

                if not fecha_str or not hora_str:
                    continue

                fecha_cita = datetime.fromisoformat(fecha_str).date()

                if fecha_cita == today:
                    try:
                        hora_cita = datetime.strptime(hora_str, "%H:%M").time()
                    except ValueError:
                        continue

                    # Check if appointment is within next 1 hour
                    if hora_cita > hora_actual:
                        tiempo_falta = datetime.combine(today, hora_cita) - now
                        if timedelta(minutes=0) <= tiempo_falta <= timedelta(hours=1):
                            nombre = cita.get("nombre_cliente", "Amigo/a")
                            telefono = cita.get("telefono_cliente")

                            if telefono:
                                mensaje = (
                                    f"Hola {nombre} ⏰ En una hora tienes tu cita con nosotros. ¡Te esperamos!"
                                )
                                if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                                    self.supabase.table("citas").update(
                                        {"recordatorio_1h_enviado": True}
                                    ).eq("id", cita_id).execute()
                                    enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_recordatorio_cita_1h for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_post_venta(self, cliente_id: str) -> int:
        """
        Post-sale follow-up: 24h after confirmed payment.

        Message: "Hola {nombre} 😊 ¿Cómo ha sido tu experiencia..."
        """
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            hace_25h = now - timedelta(hours=25)
            hace_23h = now - timedelta(hours=23)

            response = self.supabase.table("pagos").select(
                "id, nombre_cliente, telefono_cliente, created_at"
            ).eq(
                "cliente_id", cliente_id
            ).eq("estado", "confirmado").limit(200).execute()

            pagos = response.data or []

            for pago in pagos:
                pago_id = pago.get("id")
                created_at_str = pago.get("created_at")

                if not created_at_str:
                    continue

                try:
                    created_at = datetime.fromisoformat(created_at_str)
                except ValueError:
                    continue

                # Send follow-up 24h after payment
                if hace_25h <= created_at <= hace_23h:
                    if not await self._ya_enviado(cliente_id, "seguimiento_post_venta", pago_id, ventana_horas=48):
                        # Get customer name/phone from payment metadata
                        nombre = pago.get("nombre_cliente", "Amigo/a")
                        telefono = pago.get("telefono_cliente")

                        if telefono:
                            mensaje = (
                                f"Hola {nombre} 😊 ¿Cómo ha sido tu experiencia con nuestro servicio? "
                                f"Tu opinión es muy importante para nosotros."
                            )
                            if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                                await self._guardar_alerta_enviada(cliente_id, "seguimiento_post_venta", pago_id, mensaje)
                                enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_post_venta for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_reactivacion(self, cliente_id: str) -> int:
        """
        Reactivation follow-up: 7 days without activity (WhatsApp only).

        Message: "Hola {nombre} 👋 Hace tiempo que no sabemos de ti..."
        """
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            hace_7d = now - timedelta(days=7)

            response = self.supabase.table("conversaciones").select(
                "id, usuario_id, canal, usuario_nombre, fecha_ultimo_mensaje"
            ).eq(
                "cliente_id", cliente_id
            ).eq("canal", "whatsapp").lt(
                "fecha_ultimo_mensaje", hace_7d.isoformat()
            ).limit(200).execute()

            conversaciones = response.data or []
            logger.debug(f"Found {len(conversaciones)} inactive WhatsApp conversations for client {cliente_id}")

            for conv in conversaciones:
                conv_id = conv.get("id")
                usuario_id = conv.get("usuario_id")
                nombre = conv.get("usuario_nombre", "Amigo/a")

                if not usuario_id or not isinstance(usuario_id, str):
                    continue

                if not await self._ya_enviado(cliente_id, "reactivacion", conv_id, ventana_horas=168):
                    mensaje = (
                        f"Hola {nombre} 👋 Hace tiempo que no sabemos de ti. "
                        f"¿Hay algo en lo que podamos ayudarte?"
                    )
                    if await self.enviar_seguimiento(cliente_id, usuario_id, mensaje):
                        await self._guardar_alerta_enviada(cliente_id, "reactivacion", conv_id, mensaje)
                        enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_reactivacion for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _ya_enviado(
        self,
        cliente_id: str,
        tipo: str,
        referencia_id: str,
        ventana_horas: int,
    ) -> bool:
        """
        Check if a follow-up of this type was already sent recently.

        Args:
            cliente_id: Client ID
            tipo: Follow-up type (seguimiento_frio, seguimiento_caliente, etc)
            referencia_id: Lead ID or appointment ID
            ventana_horas: Time window in hours to check

        Returns:
            True if already sent within the time window
        """
        try:
            hace_x_horas = (datetime.now(timezone.utc) - timedelta(hours=ventana_horas)).isoformat()

            response = self.supabase.table("alertas").select("id").eq(
                "cliente_id", cliente_id
            ).eq("tipo", tipo).eq(
                "referencia_id", referencia_id
            ).gte("created_at", hace_x_horas).limit(1).execute()

            return bool(response.data)

        except Exception as e:
            logger.error(f"Error checking if already sent: {e}")
            return False

    async def _guardar_alerta_enviada(
        self,
        cliente_id: str,
        tipo: str,
        referencia_id: str,
        mensaje: str,
    ) -> None:
        """
        Save a sent follow-up alert to prevent duplicates.

        Args:
            cliente_id: Client ID
            tipo: Follow-up type
            referencia_id: Lead ID or appointment ID
            mensaje: Message sent
        """
        try:
            alerta = {
                "cliente_id": cliente_id,
                "tipo": tipo,
                "referencia_id": referencia_id,
                "mensaje": mensaje,
                "canal_envio": "whatsapp",
                "leida": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.supabase.table("alertas").insert(alerta).execute()

        except Exception as e:
            logger.error(f"Error saving alert: {e}")

    async def enviar_seguimiento(
        self,
        cliente_id: str,
        telefono: str,
        mensaje: str,
    ) -> bool:
        """
        Send follow-up message via WhatsApp using Meta API.

        Args:
            cliente_id: Client ID
            telefono: Recipient phone (format: 34612345678)
            mensaje: Message text

        Returns:
            True if sent successfully
        """
        try:
            # Get WhatsApp credentials from canales_config
            creds_response = self.supabase.table("canales_config").select(
                "token, phone_number_id"
            ).eq("cliente_id", cliente_id).eq("canal", "whatsapp").limit(1).execute()

            if not creds_response.data:
                logger.warning(f"No WhatsApp credentials found for client {cliente_id}")
                return False

            creds = creds_response.data[0]
            token = creds.get("token")
            phone_number_id = creds.get("phone_number_id")

            if not token or not phone_number_id:
                logger.warning(f"Missing credentials for client {cliente_id}")
                return False

            # Construct Meta API request
            url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "text",
                "text": {"body": mensaje},
            }

            response = await self.http_client.post(url, json=payload, headers=headers)

            if response.status_code in (200, 201):
                logger.info(f"Seguimiento sent to {telefono}", extra={"cliente_id": cliente_id})
                return True
            else:
                logger.error(
                    f"Failed to send seguimiento to {telefono}: {response.status_code}",
                    extra={"cliente_id": cliente_id, "response": response.text}
                )
                return False

        except Exception as e:
            logger.error(f"Error sending seguimiento to {telefono}: {e}", exc_info=True)
            return False
