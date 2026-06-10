"""
Automatic follow-up system: 6 types of follow-ups (cold leads, hot leads, appointment reminders, post-sale, reactivation).

REQUIRED SQL MIGRATION before deployment:
    ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_24h_enviado BOOLEAN DEFAULT FALSE;
    ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_1h_enviado BOOLEAN DEFAULT FALSE;
    ALTER TABLE alertas ADD COLUMN IF NOT EXISTS referencia_id TEXT;
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
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

    async def _obtener_info_seguimiento(self, cliente_id: str) -> dict[str, str]:
        """Fetch agent name, company name, and timezone for personalized follow-up messages."""
        info: dict[str, str] = {
            "agente_nombre": "nuestro equipo",
            "empresa": "nosotros",
            "timezone": "America/Guayaquil",
        }
        try:
            agente_resp = self.supabase.table("agentes").select(
                "nombre, business_hours_timezone"
            ).eq("cliente_id", cliente_id).limit(1).execute()
            if agente_resp.data:
                row = agente_resp.data[0]
                if row.get("nombre"):
                    info["agente_nombre"] = row["nombre"]
                if row.get("business_hours_timezone"):
                    info["timezone"] = row["business_hours_timezone"]

            cliente_resp = self.supabase.table("clientes").select(
                "nombre_negocio"
            ).eq("id", cliente_id).limit(1).execute()
            if cliente_resp.data and cliente_resp.data[0].get("nombre_negocio"):
                info["empresa"] = cliente_resp.data[0]["nombre_negocio"]
        except Exception as e:
            logger.error(f"Error fetching follow-up info for {cliente_id}: {e}")
        return info

    def _esta_en_horario_envio(self, timezone_str: str) -> bool:
        """Return True if current local time is between 8:00 and 21:00 (inclusive start)."""
        try:
            tz = ZoneInfo(timezone_str)
            hora_local = datetime.now(tz).hour
            return 8 <= hora_local < 21
        except (ZoneInfoNotFoundError, Exception):
            hora_utc = datetime.now(timezone.utc).hour
            return 8 <= hora_utc < 21

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

            info = await self._obtener_info_seguimiento(cliente_id)

            result = {
                "frios": await self._verificar_prospectos_frios(cliente_id, info),
                "calientes": await self._verificar_leads_calientes(cliente_id, info),
                "cita_24h": await self._verificar_recordatorio_cita_24h(cliente_id, info),
                "cita_1h": await self._verificar_recordatorio_cita_1h(cliente_id, info),
                "post_venta": await self._verificar_post_venta(cliente_id, info),
                "reactivacion": await self._verificar_reactivacion(cliente_id, info),
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

    async def _verificar_prospectos_frios(self, cliente_id: str, info: dict[str, str]) -> int:
        """Cold lead follow-up: score < 5, active state, no response in 24h. Respects send hours."""
        try:
            if not self._esta_en_horario_envio(info["timezone"]):
                return 0

            enviados = 0
            now = datetime.now(timezone.utc)
            hace_24h = now - timedelta(hours=24)
            agente = info["agente_nombre"]
            empresa = info["empresa"]

            response = self.supabase.table("leads").select(
                "id, nombre, telefono"
            ).eq("cliente_id", cliente_id).lt("score", 5).neq(
                "estado", "descartado"
            ).neq("estado", "ganado").neq("estado", "cerrado").limit(200).execute()

            leads = response.data or []
            logger.debug(f"Found {len(leads)} cold leads for client {cliente_id}")

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

                fecha_str = conv_response.data[0].get("fecha_ultimo_mensaje")
                if not fecha_str:
                    continue

                if datetime.fromisoformat(fecha_str) < hace_24h:
                    if not await self._ya_enviado(cliente_id, "seguimiento_frio", lead_id, ventana_horas=24):
                        mensaje = (
                            f"Hola {nombre} 👋 Soy {agente} de {empresa}. "
                            f"Hace un momento hablamos sobre nuestros servicios. "
                            f"¿Pudiste revisar la información? Estoy aquí para resolver cualquier duda 😊"
                        )
                        if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                            await self._guardar_alerta_enviada(cliente_id, "seguimiento_frio", lead_id, mensaje)
                            enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_prospectos_frios for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_leads_calientes(self, cliente_id: str, info: dict[str, str]) -> int:
        """Hot lead follow-up: score >= 7, active state, no response in 2h. Respects send hours."""
        try:
            if not self._esta_en_horario_envio(info["timezone"]):
                return 0

            enviados = 0
            now = datetime.now(timezone.utc)
            hace_2h = now - timedelta(hours=2)
            agente = info["agente_nombre"]
            empresa = info["empresa"]

            response = self.supabase.table("leads").select(
                "id, nombre, telefono"
            ).eq("cliente_id", cliente_id).gte("score", 7).neq(
                "estado", "descartado"
            ).neq("estado", "ganado").neq("estado", "cerrado").limit(200).execute()

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

                fecha_str = conv_response.data[0].get("fecha_ultimo_mensaje")
                if not fecha_str:
                    continue

                if datetime.fromisoformat(fecha_str) < hace_2h:
                    if not await self._ya_enviado(cliente_id, "seguimiento_caliente", lead_id, ventana_horas=24):
                        mensaje = (
                            f"Hola {nombre} 🔥 Soy {agente} de {empresa}. "
                            f"Vi que estabas muy interesado en nuestros servicios. "
                            f"¿Tienes alguna pregunta que pueda resolver ahora mismo?"
                        )
                        if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                            await self._guardar_alerta_enviada(cliente_id, "seguimiento_caliente", lead_id, mensaje)
                            enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_leads_calientes for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_recordatorio_cita_24h(self, cliente_id: str, info: dict[str, str]) -> int:
        """Appointment reminder 24h before. Time-sensitive: no send-hours restriction."""
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            tomorrow = (now + timedelta(days=1)).date()
            empresa = info["empresa"]

            response = self.supabase.table("citas").select(
                "id, nombre_cliente, hora, telefono_cliente, fecha"
            ).eq("cliente_id", cliente_id).eq("estado", "confirmada").eq(
                "recordatorio_24h_enviado", False
            ).limit(200).execute()

            citas = response.data or []

            for cita in citas:
                cita_id = cita.get("id")
                fecha_str = cita.get("fecha")

                if not fecha_str:
                    continue

                if datetime.fromisoformat(fecha_str).date() == tomorrow:
                    nombre = cita.get("nombre_cliente", "Amigo/a")
                    hora = cita.get("hora", "la hora acordada")
                    telefono = cita.get("telefono_cliente")

                    if telefono:
                        mensaje = (
                            f"Hola {nombre} 👋 Te recuerda {empresa} que mañana tienes una cita a las {hora}. "
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

    async def _verificar_recordatorio_cita_1h(self, cliente_id: str, info: dict[str, str]) -> int:
        """Appointment reminder 1h before. Time-sensitive: no send-hours restriction."""
        try:
            enviados = 0
            now = datetime.now(timezone.utc)
            today = now.date()
            hora_actual = now.time()
            empresa = info["empresa"]

            response = self.supabase.table("citas").select(
                "id, nombre_cliente, hora, telefono_cliente, fecha"
            ).eq("cliente_id", cliente_id).eq("estado", "confirmada").eq(
                "recordatorio_1h_enviado", False
            ).limit(200).execute()

            citas = response.data or []

            for cita in citas:
                cita_id = cita.get("id")
                fecha_str = cita.get("fecha")
                hora_str = cita.get("hora")

                if not fecha_str or not hora_str:
                    continue

                if datetime.fromisoformat(fecha_str).date() != today:
                    continue

                try:
                    hora_cita = datetime.strptime(hora_str, "%H:%M").time()
                except ValueError:
                    continue

                if hora_cita > hora_actual:
                    tiempo_falta = datetime.combine(today, hora_cita) - now
                    if timedelta(minutes=0) <= tiempo_falta <= timedelta(hours=1):
                        nombre = cita.get("nombre_cliente", "Amigo/a")
                        telefono = cita.get("telefono_cliente")

                        if telefono:
                            mensaje = (
                                f"Hola {nombre} ⏰ Te recuerda {empresa}: en una hora tienes tu cita. ¡Te esperamos!"
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

    async def _verificar_post_venta(self, cliente_id: str, info: dict[str, str]) -> int:
        """Post-sale follow-up: 24h after confirmed payment. Respects send hours."""
        try:
            if not self._esta_en_horario_envio(info["timezone"]):
                return 0

            enviados = 0
            now = datetime.now(timezone.utc)
            hace_25h = now - timedelta(hours=25)
            hace_23h = now - timedelta(hours=23)
            agente = info["agente_nombre"]
            empresa = info["empresa"]

            response = self.supabase.table("pagos").select(
                "id, sender_telefono, created_at"
            ).eq("cliente_id", cliente_id).eq("estado", "confirmado").limit(200).execute()

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

                if hace_25h <= created_at <= hace_23h:
                    if not await self._ya_enviado(cliente_id, "seguimiento_post_venta", pago_id, ventana_horas=48):
                        telefono = pago.get("sender_telefono")
                        nombre = await self._obtener_nombre_usuario(cliente_id, telefono)

                        if telefono:
                            mensaje = (
                                f"Hola {nombre} 😊 Soy {agente} de {empresa}. "
                                f"¿Cómo ha sido tu experiencia con nuestro servicio? "
                                f"Tu opinión es muy importante para nosotros."
                            )
                            if await self.enviar_seguimiento(cliente_id, telefono, mensaje):
                                await self._guardar_alerta_enviada(cliente_id, "seguimiento_post_venta", pago_id, mensaje)
                                enviados += 1

            return enviados

        except Exception as e:
            logger.error(f"Error in _verificar_post_venta for {cliente_id}: {e}", exc_info=True)
            return 0

    async def _verificar_reactivacion(self, cliente_id: str, info: dict[str, str]) -> int:
        """Reactivation follow-up: 7 days without activity (WhatsApp only). Respects send hours."""
        try:
            if not self._esta_en_horario_envio(info["timezone"]):
                return 0

            enviados = 0
            now = datetime.now(timezone.utc)
            hace_7d = now - timedelta(days=7)
            agente = info["agente_nombre"]
            empresa = info["empresa"]

            response = self.supabase.table("conversaciones").select(
                "id, usuario_id, canal, usuario_nombre, fecha_ultimo_mensaje"
            ).eq("cliente_id", cliente_id).eq("canal", "whatsapp").lt(
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
                        f"Hola {nombre} 👋 Soy {agente} de {empresa}. "
                        f"Hace tiempo que no sabemos de ti. ¿Hay algo en lo que podamos ayudarte?"
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
                await self._guardar_mensaje_en_conversacion(cliente_id, telefono, mensaje)
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

    async def _obtener_nombre_usuario(self, cliente_id: str, telefono: str) -> str:
        """Look up user name from leads or conversations table."""
        try:
            lead_resp = self.supabase.table("leads").select(
                "nombre"
            ).eq("cliente_id", cliente_id).eq("telefono", telefono).limit(1).execute()
            if lead_resp.data and lead_resp.data[0].get("nombre"):
                return lead_resp.data[0]["nombre"]

            conv_resp = self.supabase.table("conversaciones").select(
                "usuario_nombre"
            ).eq("cliente_id", cliente_id).eq("usuario_id", telefono).order(
                "fecha_inicio", desc=True
            ).limit(1).execute()
            if conv_resp.data and conv_resp.data[0].get("usuario_nombre"):
                return conv_resp.data[0]["usuario_nombre"]
        except Exception as e:
            logger.error(f"Error fetching user name: {e}")
        return "Amigo/a"

    async def _guardar_mensaje_en_conversacion(
        self,
        cliente_id: str,
        telefono: str,
        mensaje: str,
    ) -> None:
        """Save the outgoing follow-up message to conversation history so the agent has context."""
        try:
            conv_response = self.supabase.table("conversaciones").select(
                "id"
            ).eq("cliente_id", cliente_id).eq("usuario_id", telefono).eq(
                "canal", "whatsapp"
            ).order("fecha_inicio", desc=True).limit(1).execute()

            if not conv_response.data:
                return

            conversation_id = conv_response.data[0]["id"]
            now = datetime.now(timezone.utc).isoformat()

            self.supabase.table("mensajes").insert({
                "id": str(uuid4()),
                "conversacion_id": conversation_id,
                "cliente_id": cliente_id,
                "sender_id": "agent",
                "sender_type": "agent",
                "contenido": mensaje,
                "tipo": "texto",
                "tokens_utilizados": 0,
            }).execute()

            self.supabase.table("conversaciones").update(
                {"fecha_ultimo_mensaje": now}
            ).eq("id", conversation_id).execute()

        except Exception as e:
            logger.error(f"Error saving seguimiento message to conversation: {e}")
