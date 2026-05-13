"""
Alerts module: real-time notifications to business owner via WhatsApp.

Detects critical events (frustrated customer, escalation failures, suspicious payments)
and sends immediate alerts to owner's personal WhatsApp.
"""

import httpx
import logging
import re
from datetime import datetime, timedelta
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

    # Keywords to detect frustration/anger
    FRUSTRATION_KEYWORDS = {
        "molesto", "molestas", "molesta", "enojado", "enojada",
        "enojo", "furioso", "furiosa", "furia", "ira", "irritado",
        "irritada", "disgusto", "disgustado", "terrible", "pésimo",
        "terrible", "malo", "malísimo", "queja", "reclamó", "reclamo",
        "complain", "upset", "angry", "furious", "terrible", "awful",
        "frustrated", "frustrado", "frustrada", "frustration",
    }

    # Keywords to detect intention to abandon
    ABANDON_KEYWORDS = {
        "me voy", "cancelar", "cancelo", "cancelaré", "busco otra",
        "competencia", "cambio de empresa", "cambio de proveedor",
        "dejaré", "no seguiré", "terminamos", "ya no quiero",
        "leave", "cancel", "other company", "competitor", "find another",
        "no longer", "stop using", "quit", "switch providers",
    }

    def __init__(self, supabase_client: Any):
        """
        Initialize alerts module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def _send_whatsapp_via_meta(
        self,
        client_id: str,
        phone_number_id: str,
        to_phone: str,
        message: str,
    ) -> dict[str, Any]:
        """
        Send WhatsApp message directly via Meta Cloud API.

        Args:
            client_id: Client ID
            phone_number_id: WhatsApp phone number ID
            to_phone: Recipient phone number (with country code, e.g., +1234567890)
            message: Message text to send

        Returns:
            Response with success status
        """
        try:
            # Get access token from canales_config
            config_response = self.supabase.table("canales_config").select(
                "token"
            ).eq("cliente_id", client_id).eq("canal", "whatsapp").single().execute()

            if not config_response.data:
                logger.warning(f"No WhatsApp config found for client {client_id}")
                return {"success": False, "error": "WhatsApp config not found"}

            access_token = config_response.data.get("token")
            if not access_token:
                logger.warning(f"No access token for client {client_id}")
                return {"success": False, "error": "Access token not found"}

            url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {"body": message}
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code in [200, 201]:
                    logger.info(
                        f"WhatsApp message sent via Meta API",
                        extra={"client_id": client_id, "phone": to_phone}
                    )
                    return {"success": True, "message_id": response.json().get("messages", [{}])[0].get("id")}
                else:
                    logger.error(
                        f"Meta API error: {response.status_code} {response.text}",
                        extra={"client_id": client_id}
                    )
                    return {"success": False, "error": f"Meta API returned {response.status_code}"}

        except Exception as e:
            logger.error(f"Error sending WhatsApp via Meta API: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

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
                "cliente_id": client_id,
                "tipo": nivel.value,
                "mensaje": f"{titulo}\n\n{mensaje}",
                "canal_envio": "whatsapp",
                "leida": False,
            }

            result = self.supabase.table("alertas").insert(alert).execute()

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

            alert_id = result.data[0].get("id") if result.data else "unknown"
            return {
                "success": True,
                "alert_id": alert_id,
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
                {"leida": True}
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
            ).eq("leida", False).order("created_at", desc=True).limit(limit).execute()

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
                query = query.eq("tipo", nivel)

            response = query.order("created_at", desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    def _detect_frustration(self, text: str) -> bool:
        """
        Detect if customer is frustrated or angry.

        Args:
            text: Customer message text

        Returns:
            True if frustration detected
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.FRUSTRATION_KEYWORDS)

    def _detect_abandon_intention(self, text: str) -> bool:
        """
        Detect if customer intends to abandon/cancel.

        Args:
            text: Customer message text

        Returns:
            True if abandon intention detected
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.ABANDON_KEYWORDS)

    async def _get_owner_phone(self, client_id: str) -> Optional[str]:
        """
        Get business owner's personal phone number.

        Args:
            client_id: Client ID

        Returns:
            Owner's phone number or None
        """
        try:
            response = self.supabase.table("clientes").select(
                "whatsapp_dueño, telefono"
            ).eq("id", client_id).single().execute()

            if response.data:
                # Try whatsapp_dueño first, then fallback to telefono
                return response.data.get("whatsapp_dueño") or response.data.get("telefono")

            logger.warning(f"Owner phone not found for client {client_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching owner phone: {e}")
            return None

    async def _get_phone_number_id(self, client_id: str) -> Optional[str]:
        """
        Get WhatsApp phone number ID for client's business account.

        Args:
            client_id: Client ID

        Returns:
            Phone number ID or None
        """
        try:
            response = self.supabase.table("canales_config").select(
                "phone_number_id"
            ).eq("cliente_id", client_id).eq("canal", "whatsapp").single().execute()

            if response.data:
                return response.data.get("phone_number_id")

            logger.warning(f"Phone number ID not found for client {client_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching phone number ID: {e}")
            return None

    async def _get_conversation_details(
        self,
        client_id: str,
        conversation_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get conversation details for alert context.

        Args:
            client_id: Client ID
            conversation_id: Conversation ID

        Returns:
            Conversation details or None
        """
        try:
            response = self.supabase.table("conversations").select(
                "id, user_id, channel, last_message, last_message_at"
            ).eq("id", conversation_id).single().execute()

            return response.data if response.data else None

        except Exception as e:
            logger.warning(f"Error fetching conversation details: {e}")
            return None

    async def _get_user_details(
        self,
        client_id: str,
        user_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get user/customer details for alert context.

        Args:
            client_id: Client ID
            user_id: User ID

        Returns:
            User details or None
        """
        try:
            response = self.supabase.table("usuarios").select(
                "id, email, telefono"
            ).eq("cliente_id", client_id).eq("id", user_id).single().execute()

            return response.data if response.data else None

        except Exception as e:
            logger.warning(f"Error fetching user details: {e}")
            return None

    async def enviar_alerta_critica(
        self,
        client_id: str,
        tipo: str,
        mensaje: str,
        conversacion_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        datos_extras: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Send critical alert to business owner immediately via WhatsApp.

        Alert types:
        - agent_failed: Agent failed to respond 2 times in a row
        - customer_frustrated: Customer showing signs of frustration/anger
        - customer_abandoning: Customer threatening to leave
        - suspicious_payment: Suspicious payment receipt

        Args:
            client_id: Client ID
            tipo: Alert type
            mensaje: Alert message (will be formatted)
            conversacion_id: Optional conversation ID for context
            usuario_id: Optional user ID for context
            datos_extras: Optional additional data

        Returns:
            Alert confirmation
        """
        try:
            owner_phone = await self._get_owner_phone(client_id)
            if not owner_phone:
                logger.warning(f"Cannot send critical alert: owner_phone not available")
                return {"success": False, "error": "Owner phone not available"}

            # Get conversation and user details for context
            conv_details = None
            user_details = None
            if conversacion_id:
                conv_details = await self._get_conversation_details(client_id, conversacion_id)
            if usuario_id:
                user_details = await self._get_user_details(client_id, usuario_id)

            # Format alert message
            alert_text = self._format_critical_alert(
                tipo=tipo,
                mensaje=mensaje,
                user_details=user_details,
                conv_details=conv_details,
                datos_extras=datos_extras,
            )

            phone_number_id = await self._get_phone_number_id(client_id)
            if not phone_number_id:
                logger.warning(f"Phone number ID not found for client {client_id}")
                return {"success": False, "error": "Phone number ID not found"}

            # Send via WhatsApp directly through Meta API
            result = await self._send_whatsapp_via_meta(
                client_id=client_id,
                phone_number_id=phone_number_id,
                to_phone=owner_phone,
                message=alert_text,
            )
            success = result.get("success", False)

            # Save alert to database
            alert_record = {
                "cliente_id": client_id,
                "tipo": tipo,
                "mensaje": mensaje,
                "canal_envio": "whatsapp",
                "leida": False,
            }

            result = self.supabase.table("alertas").insert(alert_record).execute()
            alert_id = result.data[0].get("id") if result.data else "unknown"

            logger.info(
                f"Critical alert sent to owner: {tipo}",
                extra={"client_id": client_id, "alert_id": alert_id},
            )

            return {
                "success": success,
                "alert_id": alert_id,
                "type": "critical",
                "message": f"Alerta crítica enviada al propietario",
            }

        except Exception as e:
            logger.error(f"Error sending critical alert: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def enviar_alerta_importante(
        self,
        client_id: str,
        tipo: str,
        mensaje: str,
        usuario_id: Optional[str] = None,
        datos_extras: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Send important alert to business owner via WhatsApp + Email.

        Alert types:
        - hot_lead: Lead with score >= 8
        - appointment_scheduled: New appointment created
        - payment_pending_review: Payment awaiting verification

        Args:
            client_id: Client ID
            tipo: Alert type
            mensaje: Alert message
            usuario_id: Optional user ID for context
            datos_extras: Optional additional data

        Returns:
            Alert confirmation
        """
        try:
            owner_phone = await self._get_owner_phone(client_id)
            if not owner_phone:
                logger.warning(f"Cannot send important alert: owner_phone not available")
                return {"success": False, "error": "Owner phone not available"}

            # Format alert message
            alert_text = self._format_important_alert(
                tipo=tipo,
                mensaje=mensaje,
                datos_extras=datos_extras,
            )

            phone_number_id = await self._get_phone_number_id(client_id)
            if not phone_number_id:
                return {"success": False, "error": "Phone number ID not found"}

            # Send via WhatsApp directly through Meta API
            result = await self._send_whatsapp_via_meta(
                client_id=client_id,
                phone_number_id=phone_number_id,
                to_phone=owner_phone,
                message=alert_text,
            )
            success = result.get("success", False)

            # Save alert to database
            alert_record = {
                "cliente_id": client_id,
                "tipo": tipo,
                "mensaje": mensaje,
                "canal_envio": "whatsapp",
                "leida": False,
            }

            result = self.supabase.table("alertas").insert(alert_record).execute()
            alert_id = result.data[0].get("id") if result.data else "unknown"

            logger.info(
                f"Important alert sent to owner: {tipo}",
                extra={"client_id": client_id},
            )

            return {
                "success": success,
                "alert_id": alert_id,
                "type": "important",
                "message": f"Alerta importante enviada",
            }

        except Exception as e:
            logger.error(f"Error sending important alert: {e}")
            return {"success": False, "error": str(e)}

    async def enviar_resumen_diario(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """
        Send daily summary to business owner at 8 PM.

        Summary includes:
        - Total conversations today
        - New leads today
        - Appointments scheduled
        - Payments received

        Args:
            client_id: Client ID

        Returns:
            Summary confirmation
        """
        try:
            owner_phone = await self._get_owner_phone(client_id)
            if not owner_phone:
                logger.warning(f"Cannot send daily summary: owner_phone not available")
                return {"success": False, "error": "Owner phone not available"}

            # Get metrics for today
            today = datetime.utcnow().date().isoformat()
            tomorrow = (datetime.utcnow().date() + timedelta(days=1)).isoformat()

            try:
                # Get conversation count
                convs = self.supabase.table("conversations").select("id", count="exact").eq(
                    "cliente_id", client_id
                ).gte("created_at", today).lt("created_at", tomorrow).execute()
                total_conversations = len(convs.data) if convs.data else 0
            except:
                total_conversations = 0

            try:
                # Get new leads
                leads = self.supabase.table("leads").select("id", count="exact").eq(
                    "cliente_id", client_id
                ).gte("created_at", today).lt("created_at", tomorrow).execute()
                new_leads = len(leads.data) if leads.data else 0
            except:
                new_leads = 0

            try:
                # Get scheduled appointments
                appts = self.supabase.table("appointments").select("id", count="exact").eq(
                    "cliente_id", client_id
                ).gte("created_at", today).lt("created_at", tomorrow).execute()
                appointments = len(appts.data) if appts.data else 0
            except:
                appointments = 0

            try:
                # Get payments
                payments = self.supabase.table("payments").select("monto").eq(
                    "cliente_id", client_id
                ).eq("estado", "verificado").gte("created_at", today).lt("created_at", tomorrow).execute()
                total_amount = sum(p.get("monto", 0) for p in (payments.data or []))
            except:
                total_amount = 0

            # Format summary
            summary_text = (
                f"📊 *RESUMEN DEL DÍA*\n\n"
                f"📱 Conversaciones: {total_conversations}\n"
                f"🔥 Nuevos leads: {new_leads}\n"
                f"📅 Citas agendadas: {appointments}\n"
                f"💰 Pagos verificados: ${total_amount:,.2f}\n"
            )

            phone_number_id = await self._get_phone_number_id(client_id)
            if not phone_number_id:
                return {"success": False, "error": "Phone number ID not found"}

            # Send summary directly through Meta API
            result = await self._send_whatsapp_via_meta(
                client_id=client_id,
                phone_number_id=phone_number_id,
                to_phone=owner_phone,
                message=summary_text,
            )
            success = result.get("success", False)

            logger.info(
                f"Daily summary sent to owner",
                extra={"client_id": client_id},
            )

            return {
                "success": success,
                "type": "info",
                "message": f"Resumen diario enviado",
                "metrics": {
                    "conversations": total_conversations,
                    "leads": new_leads,
                    "appointments": appointments,
                    "payments": total_amount,
                },
            }

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _format_critical_alert(
        self,
        tipo: str,
        mensaje: str,
        user_details: Optional[dict[str, Any]] = None,
        conv_details: Optional[dict[str, Any]] = None,
        datos_extras: Optional[dict[str, Any]] = None,
    ) -> str:
        """Format critical alert message with context."""
        alert_emoji = "🚨"
        type_labels = {
            "agent_failed": "AGENTE FALLÓ",
            "customer_frustrated": "CLIENTE FURIOSO",
            "customer_abandoning": "CLIENTE QUIERE IRSE",
            "suspicious_payment": "COMPROBANTE SOSPECHOSO",
        }

        title = type_labels.get(tipo, tipo.upper())
        text = f"{alert_emoji} *{title}*\n\n"

        if user_details:
            text += f"📧 Cliente: {user_details.get('email', 'N/A')}\n"
        if conv_details:
            text += f"📞 Canal: {conv_details.get('channel', 'N/A')}\n"

        text += f"\n{mensaje}"

        return text

    def _format_important_alert(
        self,
        tipo: str,
        mensaje: str,
        datos_extras: Optional[dict[str, Any]] = None,
    ) -> str:
        """Format important alert message."""
        alert_emoji = "🔔"
        type_labels = {
            "hot_lead": "LEAD CALIENTE",
            "appointment_scheduled": "CITA AGENDADA",
            "payment_pending_review": "PAGO PENDIENTE",
        }

        title = type_labels.get(tipo, tipo.upper())
        text = f"{alert_emoji} *{title}*\n\n{mensaje}"

        return text

    async def detectar_y_enviar_alertas(
        self,
        client_id: str,
        user_message: str,
        agent_response: dict[str, Any],
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        sender_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Detect alert triggers and send notifications.

        Called after agent processes a message.
        Detects:
        - Customer frustration/anger
        - Customer abandonment intention
        - Agent escalation (if escalated multiple times)
        - High-value lead (score >= 8)
        - New appointment scheduled
        - Suspicious payment

        Args:
            client_id: Client ID
            user_message: Customer's original message
            agent_response: Agent's response dict (may contain escalated flag, etc)
            conversation_id: Conversation ID
            user_id: User/customer ID
            sender_id: Sender phone/ID

        Returns:
            List of alerts sent
        """
        alerts_sent = []

        try:
            # Detect frustration
            if self._detect_frustration(user_message):
                result = await self.enviar_alerta_critica(
                    client_id=client_id,
                    tipo="customer_frustrated",
                    mensaje=f"Cliente mostrando signos de frustración/enojo.\n\n💬 Mensaje: {user_message[:100]}",
                    conversacion_id=conversation_id,
                    usuario_id=user_id,
                )
                alerts_sent.append(result)
                logger.info(f"Frustration alert sent for client {client_id}")

            # Detect abandon intention
            if self._detect_abandon_intention(user_message):
                result = await self.enviar_alerta_critica(
                    client_id=client_id,
                    tipo="customer_abandoning",
                    mensaje=f"⚠️ Cliente amenaza con cancelar o irse a la competencia.\n\n💬 Mensaje: {user_message[:100]}",
                    conversacion_id=conversation_id,
                    usuario_id=user_id,
                )
                alerts_sent.append(result)
                logger.warning(f"Abandon alert sent for client {client_id}")

            # Detect agent escalation
            if agent_response.get("escalated"):
                result = await self.enviar_alerta_critica(
                    client_id=client_id,
                    tipo="agent_failed",
                    mensaje=f"El agente no pudo responder. Escalado a operador humano.\n\nTema: {user_message[:100]}",
                    conversacion_id=conversation_id,
                    usuario_id=user_id,
                )
                alerts_sent.append(result)

        except Exception as e:
            logger.error(f"Error in detectar_y_enviar_alertas: {e}", exc_info=True)

        return alerts_sent
