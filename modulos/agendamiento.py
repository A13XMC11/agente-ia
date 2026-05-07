"""
Booking module: Google Calendar integration and appointment management.

Handles appointment scheduling with real availability checking,
Google Calendar synchronization, and comprehensive error handling.
"""

import base64
import json
import logging
import os
from datetime import datetime, date, timedelta, time
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgendamientoModule:
    """Booking and calendar operations with availability verification."""

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
        """Initialize Google Calendar using Service Account credentials."""
        try:
            try:
                credentials_dict = json.loads(credentials_json)
            except json.JSONDecodeError:
                credentials_dict = json.loads(base64.b64decode(credentials_json))

            cred_type = credentials_dict.get("type", "")
            if cred_type != "service_account":
                logger.warning(
                    "Google Calendar requiere Service Account — "
                    "credenciales tipo 'web' necesitan autorización interactiva. "
                    "Las citas se guardarán solo en Supabase."
                )
                return

            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            self._calendar_service = build("calendar", "v3", credentials=credentials)
            logger.info("Google Calendar service initialized")
        except Exception as e:
            logger.error(f"Error initializing Google Calendar: {e}")

    async def consultar_disponibilidad(
        self,
        client_id: str,
        fecha: str,
    ) -> dict[str, Any]:
        """
        Check real availability for a specific date by querying:
        1. Google Calendar events for the day
        2. Supabase citas table for confirmed/pending appointments

        Args:
            client_id: Client ID
            fecha: Date (YYYY-MM-DD)

        Returns:
            Dict with available and booked time slots
            Example: {
                "fecha": "2026-05-09",
                "disponibles": ["09:00", "10:00", "14:00", "15:00"],
                "ocupados": ["11:00", "12:00"],
                "horario_atencion": "09:00 - 18:00"
            }
        """
        try:
            start_str = "09:00"
            end_str = "18:00"

            config_response = self.supabase.table("agentes").select(
                "horario_atencion_inicio,horario_atencion_fin,zona_horaria"
            ).eq("cliente_id", client_id).single().execute()

            config = config_response.data or {}
            raw_start = config.get("horario_atencion_inicio")
            raw_end = config.get("horario_atencion_fin")
            timezone = config.get("zona_horaria", "America/Guayaquil")

            if raw_start:
                start_str = str(raw_start)[:5]
            if raw_end:
                end_str = str(raw_end)[:5]

        except Exception as e:
            logger.warning(f"Could not fetch business hours for client {client_id}: {e}")
            timezone = "America/Guayaquil"

        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))

        all_slots = self._generate_hourly_slots(start_hour, start_min, end_hour, end_min)

        booked_times = set()

        try:
            citas_response = self.supabase.table("citas").select(
                "hora,duracion_minutos"
            ).eq("cliente_id", client_id).eq("fecha", fecha).neq(
                "estado", "cancelada"
            ).execute()

            citas = citas_response.data or []
            for cita in citas:
                hora_str = str(cita.get("hora", ""))[:5]
                duracion = cita.get("duracion_minutos", 30)
                booked_times.update(self._get_blocked_times(hora_str, duracion))

        except Exception as e:
            logger.warning(f"Error fetching booked appointments from Supabase: {e}")

        if self._calendar_service:
            try:
                calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
                start_datetime = f"{fecha}T{start_str}:00"
                end_datetime = f"{fecha}T{end_str}:00"

                events_result = self._calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=datetime.fromisoformat(start_datetime).isoformat() + "Z",
                    timeMax=datetime.fromisoformat(end_datetime).isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()

                events = events_result.get("items", [])
                for event in events:
                    if event.get("status") != "cancelled":
                        start_time = event.get("start", {}).get("dateTime", "")
                        if start_time:
                            event_hour = start_time[11:16]
                            duration_min = self._get_event_duration_minutes(event)
                            booked_times.update(self._get_blocked_times(event_hour, duration_min))

            except Exception as e:
                logger.warning(f"Error querying Google Calendar: {e}")

        available = [slot for slot in all_slots if slot not in booked_times]
        booked = sorted(booked_times)

        return {
            "fecha": fecha,
            "disponibles": available,
            "ocupados": booked,
            "horario_atencion": f"{start_str} - {end_str}",
            "message": (
                f"Tenemos {len(available)} horarios disponibles para el {fecha}. "
                f"¿Cuál te acomoda mejor?" if available else
                f"Lamentablemente ese día está completamente reservado. "
                f"¿Quieres intentar otro día?"
            ),
        }

    def _generate_hourly_slots(
        self,
        start_hour: int,
        start_min: int,
        end_hour: int,
        end_min: int,
    ) -> list[str]:
        """Generate list of hourly slots between start and end times."""
        slots = []
        current = time(start_hour, start_min)
        end = time(end_hour, end_min)

        while current < end:
            slots.append(f"{current.hour:02d}:{current.minute:02d}")
            current = (
                datetime.combine(date.today(), current) +
                timedelta(hours=1)
            ).time()

        return slots

    def _get_blocked_times(self, hora_str: str, duracion_minutos: int) -> set[str]:
        """Get all time slots blocked by an appointment."""
        try:
            hour, minute = map(int, hora_str.split(":"))
            start_time = datetime.combine(date.today(), time(hour, minute))
            end_time = start_time + timedelta(minutes=duracion_minutos)

            blocked = set()
            current = start_time
            while current < end_time:
                blocked.add(f"{current.hour:02d}:{current.minute:02d}")
                current += timedelta(hours=1)

            return blocked
        except Exception as e:
            logger.error(f"Error calculating blocked times: {e}")
            return set()

    def _get_event_duration_minutes(self, event: dict) -> int:
        """Calculate duration of a Google Calendar event in minutes."""
        try:
            start = event.get("start", {}).get("dateTime", "")
            end = event.get("end", {}).get("dateTime", "")

            if start and end:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                return int((end_dt - start_dt).total_seconds() / 60)
            return 30
        except Exception as e:
            logger.warning(f"Error calculating event duration: {e}")
            return 30

    async def crear_cita(
        self,
        client_id: str,
        fecha: str,
        hora: str,
        duracion_minutos: int,
        cliente_nombre: str,
        cliente_email: str,
        telefono_cliente: Optional[str] = None,
        servicio_nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create appointment after verifying availability.

        VALIDATION FLOW:
        1. Check if time slot is available
        2. Create event in Google Calendar
        3. Save to Supabase with google_event_id
        4. Return confirmation or available slots

        Args:
            client_id: Client ID
            fecha: Date (YYYY-MM-DD)
            hora: Time (HH:MM)
            duracion_minutos: Duration in minutes
            cliente_nombre: Customer name
            cliente_email: Customer email
            telefono_cliente: Optional customer phone
            servicio_nombre: Optional service name
            descripcion: Optional appointment description

        Returns:
            Success dict with appointment_id, or error dict with available slots
        """
        try:
            availability = await self.consultar_disponibilidad(client_id, fecha)

            if hora not in availability.get("disponibles", []):
                return {
                    "error": f"El horario {hora} no está disponible",
                    "disponibles": availability.get("disponibles", []),
                    "ocupados": availability.get("ocupados", []),
                    "message": availability.get("message", ""),
                }

            start_datetime = datetime.fromisoformat(f"{fecha}T{hora}:00")
            end_datetime = start_datetime + timedelta(minutes=duracion_minutos)

            summary = f"{servicio_nombre} - {cliente_nombre}" if servicio_nombre else f"Cita - {cliente_nombre}"

            calendar_event_id = None
            google_calendar_url = None

            if self._calendar_service:
                try:
                    timezone = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "America/Guayaquil")
                    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

                    event = {
                        "summary": summary,
                        "description": descripcion or f"Cliente: {cliente_nombre}\nEmail: {cliente_email}",
                        "start": {"dateTime": f"{fecha}T{hora}:00", "timeZone": timezone},
                        "end": {"dateTime": end_datetime.isoformat(), "timeZone": timezone},
                    }

                    calendar_event = self._calendar_service.events().insert(
                        calendarId=calendar_id, body=event
                    ).execute()
                    calendar_event_id = calendar_event["id"]
                    google_calendar_url = calendar_event.get("htmlLink")
                    logger.info(f"Google Calendar event created: {calendar_event_id}")

                except Exception as gc_error:
                    logger.error(f"Google Calendar creation failed: {gc_error}")
                    try:
                        self.supabase.table("alertas").insert({
                            "cliente_id": client_id,
                            "tipo": "importante",
                            "mensaje": (
                                f"Cita de {cliente_nombre} ({fecha} {hora}) guardada en Supabase "
                                f"pero no sincronizada con Google Calendar: {gc_error}"
                            ),
                        }).execute()
                    except Exception as alert_error:
                        logger.error(f"Failed to insert alert: {alert_error}")

            appointment = {
                "cliente_id": client_id,
                "nombre_cliente": cliente_nombre,
                "email_cliente": cliente_email,
                "telefono_cliente": telefono_cliente,
                "servicio": servicio_nombre or "Cita general",
                "fecha": fecha,
                "hora": hora,
                "duracion_minutos": duracion_minutos,
                "estado": "confirmada",
                "google_event_id": calendar_event_id,
                "notas": descripcion,
            }

            resultado = self.supabase.table("citas").insert(appointment).execute()
            appointment_id = resultado.data[0]["id"] if resultado.data else None

            logger.info(
                f"Appointment created: {appointment_id} for client {client_id} "
                f"({cliente_nombre} — {fecha} {hora})"
            )

            return {
                "success": True,
                "appointment_id": appointment_id,
                "calendar_event_id": calendar_event_id,
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "google_calendar_url": google_calendar_url,
                "message": f"✓ Cita agendada para {fecha} a las {hora}",
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
        Cancel an appointment and remove from Google Calendar.

        Args:
            client_id: Client ID
            cita_id: Appointment ID to cancel
            motivo: Optional cancellation reason

        Returns:
            Cancellation confirmation
        """
        try:
            response = self.supabase.table("citas").select(
                "id,google_event_id,nombre_cliente,fecha,hora"
            ).eq("id", cita_id).eq("cliente_id", client_id).single().execute()

            if not response.data:
                return {"error": f"Cita {cita_id} no encontrada"}

            appointment = response.data
            google_event_id = appointment.get("google_event_id")

            if self._calendar_service and google_event_id:
                try:
                    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
                    self._calendar_service.events().delete(
                        calendarId=calendar_id,
                        eventId=google_event_id
                    ).execute()
                    logger.info(f"Google Calendar event deleted: {google_event_id}")
                except Exception as gc_error:
                    logger.warning(f"Could not delete Google Calendar event: {gc_error}")

            self.supabase.table("citas").update({
                "estado": "cancelada",
                "notas": motivo or "Cancelada por usuario",
            }).eq("id", cita_id).execute()

            logger.info(f"Appointment {cita_id} cancelled: {motivo}")

            return {
                "success": True,
                "appointment_id": cita_id,
                "message": f"✓ Cita del {appointment['fecha']} a las {appointment['hora']} cancelada",
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
        Reschedule appointment to a new date/time.

        DELETION FLOW:
        1. Fetch old appointment with google_event_id
        2. Check new time availability
        3. Delete old Google Calendar event (idempotent)
        4. Create new Google Calendar event
        5. Update Supabase with new date/time/event_id

        Args:
            client_id: Client ID
            cita_id: Appointment ID to reschedule
            nueva_fecha: New date (YYYY-MM-DD)
            nueva_hora: New time (HH:MM)

        Returns:
            Success dict with new appointment details, or error with available slots
        """
        try:
            response = self.supabase.table("citas").select(
                "id,nombre_cliente,email_cliente,telefono_cliente,servicio,duracion_minutos,"
                "notas,google_event_id,fecha,hora"
            ).eq("id", cita_id).eq("cliente_id", client_id).single().execute()

            if not response.data:
                return {"error": f"Cita {cita_id} no encontrada"}

            old_appointment = response.data

            availability = await self.consultar_disponibilidad(client_id, nueva_fecha)
            if nueva_hora not in availability.get("disponibles", []):
                return {
                    "error": f"El horario {nueva_hora} no está disponible en {nueva_fecha}",
                    "disponibles": availability.get("disponibles", []),
                    "ocupados": availability.get("ocupados", []),
                    "message": availability.get("message", ""),
                }

            old_google_event_id = old_appointment.get("google_event_id")
            duracion = old_appointment.get("duracion_minutos", 30)

            if self._calendar_service and old_google_event_id:
                try:
                    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
                    self._calendar_service.events().delete(
                        calendarId=calendar_id,
                        eventId=old_google_event_id
                    ).execute()
                    logger.info(f"Old Google Calendar event deleted: {old_google_event_id}")
                except Exception as gc_delete_error:
                    logger.warning(f"Could not delete old event {old_google_event_id}: {gc_delete_error}")

            new_calendar_event_id = None
            if self._calendar_service:
                try:
                    timezone = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "America/Guayaquil")
                    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
                    new_start = datetime.fromisoformat(f"{nueva_fecha}T{nueva_hora}:00")
                    new_end = new_start + timedelta(minutes=duracion)

                    summary = (
                        f"{old_appointment['servicio']} - {old_appointment['nombre_cliente']}"
                        if old_appointment.get("servicio")
                        else f"Cita - {old_appointment['nombre_cliente']}"
                    )

                    event = {
                        "summary": summary,
                        "description": old_appointment.get("notas") or (
                            f"Cliente: {old_appointment['nombre_cliente']}\n"
                            f"Email: {old_appointment['email_cliente']}"
                        ),
                        "start": {"dateTime": f"{nueva_fecha}T{nueva_hora}:00", "timeZone": timezone},
                        "end": {"dateTime": new_end.isoformat(), "timeZone": timezone},
                    }

                    calendar_event = self._calendar_service.events().insert(
                        calendarId=calendar_id,
                        body=event
                    ).execute()
                    new_calendar_event_id = calendar_event["id"]
                    logger.info(f"New Google Calendar event created: {new_calendar_event_id}")

                except Exception as gc_create_error:
                    logger.error(f"Failed to create new Google Calendar event: {gc_create_error}")
                    try:
                        self.supabase.table("alertas").insert({
                            "cliente_id": client_id,
                            "tipo": "importante",
                            "mensaje": f"Cita reprogramada en Supabase pero no en Google Calendar: {gc_create_error}",
                        }).execute()
                    except Exception as alert_error:
                        logger.error(f"Failed to insert alert: {alert_error}")

            self.supabase.table("citas").update({
                "fecha": nueva_fecha,
                "hora": nueva_hora,
                "google_event_id": new_calendar_event_id,
                "estado": "confirmada",
            }).eq("id", cita_id).execute()

            logger.info(f"Appointment {cita_id} rescheduled to {nueva_fecha} {nueva_hora}")

            return {
                "success": True,
                "appointment_id": cita_id,
                "fecha_anterior": old_appointment["fecha"],
                "hora_anterior": old_appointment["hora"],
                "nueva_fecha": nueva_fecha,
                "nueva_hora": nueva_hora,
                "message": f"✓ Cita reagendada de {old_appointment['fecha']} {old_appointment['hora']} a {nueva_fecha} {nueva_hora}",
            }

        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {"error": str(e)}

    async def obtener_citas_usuario(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Get existing appointments for a user.

        Used to find the real UUID before rescheduling or canceling.

        Args:
            client_id: Client ID
            user_id: Optional user ID (if available)
            limit: Max number of appointments to return

        Returns:
            Dict with list of appointments and metadata
        """
        try:
            query = self.supabase.table("citas").select(
                "id, nombre_cliente, email_cliente, servicio, fecha, hora, estado"
            ).eq("cliente_id", client_id).eq("estado", "confirmada").order(
                "fecha", desc=False
            ).limit(limit)

            response = query.execute()
            appointments = response.data or []

            return {
                "success": True,
                "appointments": appointments,
                "total": len(appointments),
                "message": (
                    f"Encontré {len(appointments)} cita(s) confirmada(s) para ti. "
                    if appointments
                    else "No hay citas confirmadas en el sistema."
                ),
            }

        except Exception as e:
            logger.error(f"Error fetching appointments for client {client_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "appointments": [],
                "total": 0,
            }

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
