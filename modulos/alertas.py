"""
Alerts module: notifications to business owner via multiple channels.

Handles alert creation, routing, and delivery via WhatsApp, Email, and Dashboard.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"  # Immediate via WhatsApp
    IMPORTANT = "important"  # Via WhatsApp + Email
    INFO = "info"  # Via Email + Dashboard


class AlertasModule:
    """Alert and notification operations."""

    def __init__(self, supabase_client: Any, whatsapp_handler: Any = None,
                 email_handler: Any = None):
        """
        Initialize alerts module.

        Args:
            supabase_client: Supabase client instance
            whatsapp_handler: WhatsApp API handler (optional)
            email_handler: Email handler via SendGrid (optional)
        """
        self.supabase = supabase_client
        self.whatsapp = whatsapp_handler
        self.email = email_handler

    async def enviar_recordatorio(
        self,
        client_id: str,
        usuario_id: str,
        tipo: str,
        mensaje: str,
        canal: str = "whatsapp",
    ) -> dict[str, Any]:
        """
        Send reminder to customer.

        Args:
            client_id: Client ID
            usuario_id: User ID to send reminder to
            tipo: Reminder type (follow-up, payment, appointment, etc)
            mensaje: Reminder message
            canal: Channel (whatsapp, email, etc)

        Returns:
            Delivery status
        """
        try:
            # Create reminder record
            reminder = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": usuario_id,
                "type": tipo,
                "message": mensaje,
                "channel": canal,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("reminders").insert(reminder).execute()

            # Send via specified channel
            delivery_status = await self._send_reminder(
                client_id, usuario_id, mensaje, canal
            )

            if delivery_status.get("sent"):
                self.supabase.table("reminders").update(
                    {"status": "sent", "sent_at": datetime.utcnow().isoformat()}
                ).eq("id", reminder["id"]).execute()

            logger.info(
                f"Reminder sent via {canal} to user {usuario_id}: {tipo}",
                extra={"client_id": client_id},
            )

            return {
                "success": delivery_status.get("sent", False),
                "reminder_id": reminder["id"],
                "channel": canal,
                "message": "Recordatorio enviado" if delivery_status.get("sent") else "Error al enviar",
            }

        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return {"success": False, "error": str(e)}

    async def _send_reminder(
        self,
        client_id: str,
        usuario_id: str,
        mensaje: str,
        canal: str,
    ) -> dict[str, Any]:
        """
        Send reminder via specified channel.

        Args:
            client_id: Client ID
            usuario_id: User ID
            mensaje: Message to send
            canal: Channel (whatsapp, email)

        Returns:
            Delivery result
        """
        try:
            if canal == "whatsapp" and self.whatsapp:
                # Send via WhatsApp
                result = await self.whatsapp.send_message(
                    client_id=client_id,
                    user_id=usuario_id,
                    text=mensaje,
                )
                return {"sent": result.get("success", False)}

            elif canal == "email" and self.email:
                # Send via Email
                result = await self.email.send_message(
                    client_id=client_id,
                    user_id=usuario_id,
                    subject="Recordatorio",
                    body=mensaje,
                )
                return {"sent": result.get("success", False)}

            else:
                # Default: just log to database (dashboard notification)
                return {"sent": True}

        except Exception as e:
            logger.error(f"Error in _send_reminder: {e}")
            return {"sent": False}

    async def crear_alerta(
        self,
        client_id: str,
        nivel: AlertLevel,
        titulo: str,
        mensaje: str,
        datos: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Create alert for business owner.

        Alert routing:
        - CRITICAL: WhatsApp (immediate)
        - IMPORTANT: WhatsApp + Email
        - INFO: Email + Dashboard

        Args:
            client_id: Client ID
            nivel: Alert level (critical, important, info)
            titulo: Alert title
            mensaje: Alert message
            datos: Optional metadata

        Returns:
            Alert confirmation
        """
        try:
            alert = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "level": nivel.value,
                "title": titulo,
                "message": mensaje,
                "data": datos or {},
                "read": False,
                "sent_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("alertas").insert(alert).execute()

            # Route alert to admin
            admin_response = self.supabase.table("usuarios").select(
                "id, phone, email"
            ).eq("cliente_id", client_id).eq("rol", "admin").single().execute()

            if admin_response.data:
                admin = admin_response.data
                await self._route_alert(admin, nivel, titulo, mensaje)

            logger.info(
                f"Alert created: {titulo} ({nivel.value})",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "alert_id": alert["id"],
                "message": f"Alerta {nivel.value} enviada",
            }

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return {"error": str(e)}

    async def _route_alert(
        self,
        admin: dict[str, Any],
        nivel: AlertLevel,
        titulo: str,
        mensaje: str,
    ) -> None:
        """
        Route alert to appropriate channels based on level.

        Args:
            admin: Admin user data
            nivel: Alert level
            titulo: Alert title
            mensaje: Alert message
        """
        try:
            if nivel == AlertLevel.CRITICAL:
                # Send via WhatsApp immediately
                if self.whatsapp and admin.get("phone"):
                    await self.whatsapp.send_message(
                        user_id=admin["id"],
                        text=f"🚨 CRÍTICO: {titulo}\n\n{mensaje}",
                    )

            elif nivel == AlertLevel.IMPORTANT:
                # Send via WhatsApp and Email
                if self.whatsapp and admin.get("phone"):
                    await self.whatsapp.send_message(
                        user_id=admin["id"],
                        text=f"⚠️ IMPORTANTE: {titulo}\n\n{mensaje}",
                    )

                if self.email and admin.get("email"):
                    await self.email.send_message(
                        user_id=admin["id"],
                        subject=f"IMPORTANTE: {titulo}",
                        body=mensaje,
                    )

            elif nivel == AlertLevel.INFO:
                # Send via Email (dashboard shows automatically)
                if self.email and admin.get("email"):
                    await self.email.send_message(
                        user_id=admin["id"],
                        subject=f"INFO: {titulo}",
                        body=mensaje,
                    )

        except Exception as e:
            logger.error(f"Error routing alert: {e}")

    async def crear_alerta_lead_caliente(
        self,
        client_id: str,
        lead: dict[str, Any],
        score: float,
    ) -> dict[str, Any]:
        """
        Create hot lead alert.

        Args:
            client_id: Client ID
            lead: Lead data
            score: Lead score

        Returns:
            Alert confirmation
        """
        titulo = f"🔥 Lead Caliente: {lead.get('name', 'Unknown')}"
        mensaje = f"""
Lead Score: {score}/10
Contacto: {lead.get('phone') or lead.get('email') or 'N/A'}
Empresa: {lead.get('company', 'N/A')}

Acciones sugeridas:
1. Contactar ahora mismo
2. Preparar propuesta personalizada
3. Agendar demo/llamada
        """

        return await self.crear_alerta(
            client_id=client_id,
            nivel=AlertLevel.CRITICAL,
            titulo=titulo,
            mensaje=mensaje,
            datos={"lead_id": lead.get("id"), "score": score},
        )

    async def crear_alerta_pago_verificado(
        self,
        client_id: str,
        usuario_id: str,
        monto: float,
    ) -> dict[str, Any]:
        """
        Create payment verification alert.

        Args:
            client_id: Client ID
            usuario_id: User ID
            monto: Payment amount

        Returns:
            Alert confirmation
        """
        titulo = f"✅ Pago Verificado: ${monto:.2f}"
        mensaje = f"Pago de ${monto:.2f} ha sido verificado y acreditado."

        return await self.crear_alerta(
            client_id=client_id,
            nivel=AlertLevel.IMPORTANT,
            titulo=titulo,
            mensaje=mensaje,
            datos={"user_id": usuario_id, "amount": monto},
        )

    async def crear_alerta_cita_proxima(
        self,
        client_id: str,
        appointment: dict[str, Any],
        horas_avance: int = 24,
    ) -> dict[str, Any]:
        """
        Create upcoming appointment reminder alert.

        Args:
            client_id: Client ID
            appointment: Appointment data
            horas_avance: Hours in advance to alert (default 24)

        Returns:
            Alert confirmation
        """
        titulo = f"📅 Cita próxima: {appointment.get('title', 'Unknown')}"
        mensaje = f"""
Hora: {appointment.get('start_time', 'N/A')}
Descripción: {appointment.get('description', 'N/A')}

Recuerda confirmar asistencia.
        """

        return await self.crear_alerta(
            client_id=client_id,
            nivel=AlertLevel.IMPORTANT,
            titulo=titulo,
            mensaje=mensaje,
            datos={"appointment_id": appointment.get("id")},
        )

    async def marcar_alerta_leida(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """
        Mark alert as read.

        Args:
            alert_id: Alert ID

        Returns:
            Update confirmation
        """
        try:
            self.supabase.table("alertas").update(
                {"read": True, "read_at": datetime.utcnow().isoformat()}
            ).eq("id", alert_id).execute()

            logger.info(f"Alert marked as read: {alert_id}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Error marking alert as read: {e}")
            return {"error": str(e)}

    async def get_alertas_sin_leer(
        self,
        client_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get unread alerts for a client.

        Args:
            client_id: Client ID
            limit: Max results

        Returns:
            List of unread alerts
        """
        try:
            response = self.supabase.table("alertas").select("*").eq(
                "cliente_id", client_id
            ).eq("read", False).order("created_at", desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching unread alerts: {e}")
            return []

    async def get_alertas(
        self,
        client_id: str,
        nivel: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get alerts filtered by level.

        Args:
            client_id: Client ID
            nivel: Alert level (optional filter)
            limit: Max results

        Returns:
            List of alerts
        """
        try:
            query = self.supabase.table("alertas").select("*").eq(
                "cliente_id", client_id
            )

            if nivel:
                query = query.eq("level", nivel)

            response = query.order("created_at", desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
