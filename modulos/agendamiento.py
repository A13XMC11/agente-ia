"""
Booking module: Google Calendar integration and appointment management.

Handles appointment scheduling, availability checking, rescheduling,
and calendar synchronization per client.
"""

import base64
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgendamientoModule:
    """Booking and calendar operations."""

    def __init__(self, supabase_client: Any, google_credentials_json: Optional[str] = None):
        """
        Initialize booking module.

        Args:
            supabase_client: Supabase client instance
            google_credentials_json: Google credentials JSON (raw or base64).
                Falls back to GOOGLE_CALENDAR_CREDENTIALS_JSON env var if not provided.
        """
        self.supabase = supabase_client
        self._calendar_service = None
        credentials = google_credentials_json or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
        if credentials:
            self._init_google_calendar(credentials)
        else:
            logger.warning("GOOGLE_CALENDAR_CREDENTIALS_JSON not set — Google Calendar disabled")

    def _init_google_calendar(self, credentials_json: str) -> None:
        """
        Attempt to initialize Google Calendar. Skips OAuth2 'web' credentials —
        those require an interactive authorization flow not supported here.
        """
        try:
            try:
                credentials_dict = json.loads(credentials_json)
            except json.JSONDecodeError:
                credentials_dict = json.loads(base64.b64decode(credentials_json))

            cred_type = credentials_dict.get("type", "")
            if cred_type == "web" or ("client_secret" in credentials_dict and cred_type != "service_account"):
                logger.warning(
                    "Google Calendar requiere configuración OAuth2 adicional — "
                    "las credenciales tipo 'web' necesitan autorización interactiva del usuario. "
                    "Las citas se guardarán solo en Supabase."
                )
                return

            from google.oauth2.service_account import Credentials
            from googleapiclient import discovery

            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            self._calendar_service = discovery.build(
                "calendar", "v3", credentials=credentials
            )
            logger.info("Google Calendar service initialized")
        except Exception as e:
            logger.error(f"Error initializing Google Calendar: {e}")

    async def consultar_disponibilidad(
        self,
        client_id: str,
        fecha_inicio: str,
        fecha_fin: str,
    ) -> dict[str, Any]:
        """
        Return available appointment slots based on business hours config.

        Google Calendar integration is optional — falls back to static schedule.
        """
        start_str = "09:00"
        end_str = "18:00"

        try:
            config_response = self.supabase.table("agentes").select(
                "horario_atencion_inicio,horario_atencion_fin"
            ).eq("cliente_id", client_id).single().execute()

            config = config_response.data or {}
            raw_start = config.get("horario_atencion_inicio")
            raw_end = config.get("horario_atencion_fin")
            if raw_start:
                start_str = str(raw_start)[:5]
            if raw_end:
                end_str = str(raw_end)[:5]
        except Exception as e:
            logger.warning(f"Could not fetch business hours for client {client_id}: {e}")

        logger.info(
            f"Returning static availability for client {client_id} "
            f"({start_str}–{end_str}, no Calendar query)",
            extra={"client_id": client_id},
        )

        return {
            "disponibilidad": (
                f"Tenemos disponibilidad de lunes a viernes de {start_str} a {end_str} "
                "y sábados de 9:00am a 1:00pm. ¿Qué día y hora te acomoda mejor?"
            ),
            "slots": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
            "horario_inicio": start_str,
            "horario_fin": end_str,
        }

    async def crear_cita(
        self,
        client_id: str,
        user_id: str,
        fecha: str,
        hora: str,
        duracion_minutos: int,
        cliente_nombre: str,
        cliente_email: str,
        descripcion: Optional[str] = None,
        servicio_nombre: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create appointment in Google Calendar and Supabase.

        Falls back to Supabase-only on Google Calendar failure and notifies the owner.

        Args:
            client_id: Client ID
            user_id: User ID
            fecha: Date (YYYY-MM-DD)
            hora: Time (HH:MM)
            duracion_minutos: Duration in minutes
            cliente_nombre: Customer name
            cliente_email: Customer email
            descripcion: Optional appointment description
            servicio_nombre: Optional service name (included in calendar event title)

        Returns:
            Appointment details with Google Calendar ID if available
        """
        try:
            start_datetime = datetime.fromisoformat(f"{fecha}T{hora}:00")
            end_datetime = start_datetime + timedelta(minutes=duracion_minutos)

            summary = (
                f"{servicio_nombre} - {cliente_nombre}"
                if servicio_nombre
                else f"Cita - {cliente_nombre}"
            )

            calendar_event_id = None
            google_calendar_url = None
            google_calendar_ok = False

            if self._calendar_service:
                try:
                    event = {
                        "summary": summary,
                        "description": descripcion or f"Cliente: {cliente_nombre}\nEmail: {cliente_email}",
                        "start": {"dateTime": start_datetime.isoformat(), "timeZone": "UTC"},
                        "end": {"dateTime": end_datetime.isoformat(), "timeZone": "UTC"},
                        "attendees": [{"email": cliente_email, "responseStatus": "needsAction"}],
                        "reminders": {
                            "useDefault": False,
                            "overrides": [
                                {"method": "email", "minutes": 24 * 60},
                                {"method": "popup", "minutes": 30},
                            ],
                        },
                    }

                    calendar_event = (
                        self._calendar_service.events()
                        .insert(calendarId="primary", body=event, sendNotifications=True)
                        .execute()
                    )
                    calendar_event_id = calendar_event["id"]
                    google_calendar_url = calendar_event.get("htmlLink")
                    google_calendar_ok = True
                except Exception as gc_error:
                    logger.error(
                        f"Google Calendar event creation failed for client {client_id}: {gc_error}"
                    )

            if not google_calendar_ok:
                logger.warning(
                    f"Saving appointment to Supabase only for client {client_id}"
                )
                try:
                    self.supabase.table("alertas").insert({
                        "id": str(uuid4()),
                        "cliente_id": client_id,
                        "tipo": "importante",
                        "mensaje": (
                            f"No se pudo sincronizar la cita de {cliente_nombre} "
                            f"({fecha} {hora}) con Google Calendar. "
                            "Guardada solo en Supabase — revisa la configuración de credenciales."
                        ),
                        "created_at": datetime.utcnow().isoformat(),
                    }).execute()
                except Exception as alert_error:
                    logger.error(f"Failed to insert alert for owner: {alert_error}")

            # Save to database (with or without Google Calendar)
            appointment = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "nombre_cliente": cliente_nombre,
                "email_cliente": cliente_email,
                "servicio": servicio_nombre or "Cita general",
                "fecha": fecha,
                "hora": hora,
                "duracion_minutos": duracion_minutos,
                "estado": "pendiente",
                "google_event_id": calendar_event_id,
                "notas": descripcion,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            logger.info(f"Intentando crear cita: {appointment}")

            resultado = self.supabase.table("citas").insert(appointment).execute()

            logger.info(f"Resultado Supabase: {resultado}")

            logger.info(
                f"Appointment created: {appointment['id']} for client {client_id} "
                f"({cliente_nombre} — {fecha} {hora})",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "appointment_id": appointment["id"],
                "calendar_event_id": calendar_event_id,
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "google_calendar_url": google_calendar_url,
                "message": f"Cita agendada para {fecha} a las {hora}",
            }

        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return {"error": str(e)}

    async def cancelar_cita(
        self,
        client_id: str,
        cita_id: str,
        motivo: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Cancel an appointment.

        Args:
            client_id: Client ID
            cita_id: Appointment ID to cancel
            motivo: Cancellation reason

        Returns:
            Cancellation confirmation
        """
        try:
            # Fetch appointment
            response = self.supabase.table("citas").select("*").eq(
                "id", cita_id
            ).eq("cliente_id", client_id).single().execute()

            appointment = response.data

            # Cancel in Google Calendar
            if self._calendar_service and appointment.get("google_event_id"):
                self._calendar_service.events().delete(
                    calendarId="primary", eventId=appointment["google_event_id"]
                ).execute()

            # Update database
            self.supabase.table("citas").update(
                {
                    "estado": "cancelada",
                    "notas": motivo,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", cita_id).execute()

            logger.info(
                f"Appointment {cita_id} cancelled: {motivo}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "appointment_id": cita_id,
                "message": "Cita cancelada exitosamente",
            }

        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {"error": str(e)}

    async def reagendar_cita(
        self,
        client_id: str,
        cita_id: str,
        nueva_fecha: str,
        nueva_hora: str,
    ) -> dict[str, Any]:
        """
        Reschedule an existing appointment.

        Args:
            client_id: Client ID
            cita_id: Appointment ID to reschedule
            nueva_fecha: New date (YYYY-MM-DD)
            nueva_hora: New time (HH:MM)

        Returns:
            Updated appointment details
        """
        try:
            # Fetch appointment
            response = self.supabase.table("citas").select("*").eq(
                "id", cita_id
            ).eq("cliente_id", client_id).single().execute()

            old_appointment = response.data

            # Update in Google Calendar
            if self._calendar_service and old_appointment.get("google_event_id"):
                duracion = old_appointment.get("duracion_minutos", 30)
                new_start = datetime.fromisoformat(f"{nueva_fecha}T{nueva_hora}:00")
                new_end = new_start + timedelta(minutes=duracion)

                event = self._calendar_service.events().get(
                    calendarId="primary", eventId=old_appointment["google_event_id"]
                ).execute()

                event["start"] = {"dateTime": new_start.isoformat(), "timeZone": "UTC"}
                event["end"] = {"dateTime": new_end.isoformat(), "timeZone": "UTC"}

                self._calendar_service.events().update(
                    calendarId="primary",
                    eventId=old_appointment["google_event_id"],
                    body=event,
                    sendNotifications=True,
                ).execute()

            # Update database
            self.supabase.table("citas").update(
                {
                    "fecha": nueva_fecha,
                    "hora": nueva_hora,
                    "estado": "confirmada",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", cita_id).execute()

            logger.info(
                f"Appointment {cita_id} rescheduled to {nueva_fecha} {nueva_hora}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "appointment_id": cita_id,
                "nueva_fecha": nueva_fecha,
                "nueva_hora": nueva_hora,
                "message": f"Cita reprogramada para {nueva_fecha} a las {nueva_hora}",
            }

        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {"error": str(e)}

    async def get_upcoming_appointments(
        self,
        client_id: str,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Get upcoming appointments for the next N days.

        Args:
            client_id: Client ID
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming appointments
        """
        try:
            future_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()

            response = self.supabase.table("citas").select("*").eq(
                "cliente_id", client_id
            ).eq("status", "scheduled").lt("start_time", future_date).gte(
                "start_time", datetime.utcnow().isoformat()
            ).order("start_time", desc=False).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching upcoming appointments: {e}")
            return []
