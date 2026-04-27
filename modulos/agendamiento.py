"""
Booking module: Google Calendar integration and appointment management.

Handles appointment scheduling, availability checking, rescheduling,
and calendar synchronization per client.
"""

import base64
import json
import logging
from datetime import datetime, timedelta, time
from typing import Any, Optional
from uuid import uuid4

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient import discovery
import pytz

logger = logging.getLogger(__name__)


class AgendamientoModule:
    """Booking and calendar operations."""

    def __init__(self, supabase_client: Any, google_credentials_json: str):
        """
        Initialize booking module with Google Calendar access.

        Args:
            supabase_client: Supabase client instance
            google_credentials_json: Base64-encoded Google service account JSON
        """
        self.supabase = supabase_client
        self._calendar_service = None
        self._init_google_calendar(google_credentials_json)

    def _init_google_calendar(self, credentials_json: str) -> None:
        """Initialize Google Calendar API client."""
        try:
            credentials_dict = json.loads(base64.b64decode(credentials_json))
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
        Check available appointment slots in date range.

        Args:
            client_id: Client ID
            fecha_inicio: Start date (YYYY-MM-DD)
            fecha_fin: End date (YYYY-MM-DD)

        Returns:
            Available slots with times
        """
        try:
            if not self._calendar_service:
                return {"error": "Google Calendar not configured"}

            # Fetch client config for business hours and timezone
            config_response = self.supabase.table("client_config").select(
                "business_hours_start,business_hours_end,business_hours_timezone"
            ).eq("client_id", client_id).single().execute()

            config = config_response.data or {}
            tz_name = config.get("business_hours_timezone", "America/Guayaquil")
            tz = pytz.timezone(tz_name)

            start_str = config.get("business_hours_start", "08:00")
            end_str = config.get("business_hours_end", "18:00")
            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))

            # Query Google Calendar for busy times
            body = {
                "timeMin": f"{fecha_inicio}T00:00:00Z",
                "timeMax": f"{fecha_fin}T23:59:59Z",
                "items": [{"id": config.get("google_calendar_id", "primary")}],
            }

            busy_response = self._calendar_service.freebusy().query(body=body).execute()
            busy_slots = busy_response.get("calendars", {}).get("primary", {}).get(
                "busy", []
            )

            # Generate available slots
            available = []
            current_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            end_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

            while current_date <= end_date:
                # Skip weekends
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                # Generate 1-hour slots
                current_time = time(start_hour, start_min)
                end_time = time(end_hour, end_min)

                while current_time < end_time:
                    slot_start = datetime.combine(current_date, current_time)
                    slot_end = slot_start + timedelta(hours=1)

                    # Check if slot is free
                    is_busy = any(
                        (
                            datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
                            <= slot_start
                            < datetime.fromisoformat(
                                busy["end"].replace("Z", "+00:00")
                            )
                        )
                        for busy in busy_slots
                    )

                    if not is_busy:
                        available.append(
                            {
                                "fecha": current_date.isoformat(),
                                "hora": current_time.strftime("%H:%M"),
                                "timestamp": slot_start.isoformat(),
                            }
                        )

                    current_time = (
                        datetime.combine(current_date, current_time)
                        + timedelta(hours=1)
                    ).time()

                current_date += timedelta(days=1)

            logger.info(
                f"Found {len(available)} available slots for client {client_id}",
                extra={"client_id": client_id},
            )

            return {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "slots_disponibles": available,
                "total": len(available),
            }

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {"error": str(e)}

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
    ) -> dict[str, Any]:
        """
        Create appointment in Google Calendar.

        Args:
            client_id: Client ID
            user_id: User ID
            fecha: Date (YYYY-MM-DD)
            hora: Time (HH:MM)
            duracion_minutos: Duration in minutes
            cliente_nombre: Customer name
            cliente_email: Customer email
            descripcion: Optional description

        Returns:
            Appointment details with Google Calendar ID
        """
        try:
            if not self._calendar_service:
                return {"error": "Google Calendar not configured"}

            # Build event
            start_datetime = datetime.fromisoformat(f"{fecha}T{hora}:00")
            end_datetime = start_datetime + timedelta(minutes=duracion_minutos)

            event = {
                "summary": f"Cita - {cliente_nombre}",
                "description": descripcion or f"Cita agendada para {cliente_nombre}",
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

            # Create in Google Calendar
            calendar_event = (
                self._calendar_service.events()
                .insert(calendarId="primary", body=event, sendNotifications=True)
                .execute()
            )

            # Save to database
            appointment = {
                "id": str(uuid4()),
                "client_id": client_id,
                "user_id": user_id,
                "calendar_event_id": calendar_event["id"],
                "title": f"Cita - {cliente_nombre}",
                "description": descripcion,
                "start_time": start_datetime.isoformat(),
                "end_time": end_datetime.isoformat(),
                "timezone": "UTC",
                "status": "scheduled",
                "google_calendar_url": calendar_event.get("htmlLink"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("appointments").insert(appointment).execute()

            logger.info(
                f"Appointment created: {appointment['id']} for user {user_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "appointment_id": appointment["id"],
                "calendar_event_id": calendar_event["id"],
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "google_calendar_url": calendar_event.get("htmlLink"),
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
            response = self.supabase.table("appointments").select("*").eq(
                "id", cita_id
            ).eq("client_id", client_id).single().execute()

            appointment = response.data

            # Cancel in Google Calendar
            if self._calendar_service:
                self._calendar_service.events().delete(
                    calendarId="primary", eventId=appointment["calendar_event_id"]
                ).execute()

            # Update database
            self.supabase.table("appointments").update(
                {
                    "status": "cancelled",
                    "cancellation_reason": motivo,
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
            response = self.supabase.table("appointments").select("*").eq(
                "id", cita_id
            ).eq("client_id", client_id).single().execute()

            old_appointment = response.data

            # Calculate new time
            new_start = datetime.fromisoformat(f"{nueva_fecha}T{nueva_hora}:00")
            duration = datetime.fromisoformat(old_appointment["end_time"]) - datetime.fromisoformat(
                old_appointment["start_time"]
            )
            new_end = new_start + duration

            # Update in Google Calendar
            if self._calendar_service:
                event = self._calendar_service.events().get(
                    calendarId="primary", eventId=old_appointment["calendar_event_id"]
                ).execute()

                event["start"] = {"dateTime": new_start.isoformat(), "timeZone": "UTC"}
                event["end"] = {"dateTime": new_end.isoformat(), "timeZone": "UTC"}

                self._calendar_service.events().update(
                    calendarId="primary",
                    eventId=old_appointment["calendar_event_id"],
                    body=event,
                    sendNotifications=True,
                ).execute()

            # Update database
            self.supabase.table("appointments").update(
                {
                    "start_time": new_start.isoformat(),
                    "end_time": new_end.isoformat(),
                    "status": "rescheduled",
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
                "new_start": new_start.isoformat(),
                "new_end": new_end.isoformat(),
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

            response = self.supabase.table("appointments").select("*").eq(
                "client_id", client_id
            ).eq("status", "scheduled").lt("start_time", future_date).gte(
                "start_time", datetime.utcnow().isoformat()
            ).order("start_time", desc=False).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching upcoming appointments: {e}")
            return []
