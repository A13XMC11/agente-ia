"""
Appointment management module with Google Calendar integration.

Handles appointment scheduling, availability checking, rescheduling,
and cancellation with robust error handling and automatic fallback to Supabase.

Key guarantees:
- Never escalates to human for calendar errors
- Google Calendar failures don't block appointment creation
- All operations logged with detailed context
- Availability slots in 30-minute increments (9am-6pm default)
"""

import base64
import json
import logging
import os
from datetime import datetime, date, timedelta, time
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AppointmentError(Exception):
    """Base exception for appointment operations."""


class AppointmentNotFoundError(AppointmentError):
    """Raised when appointment is not found in database."""


class InvalidSlotError(AppointmentError):
    """Raised when requested time slot is not available."""


class GoogleCalendarService:
    """Wrapper for Google Calendar operations with error handling."""

    def __init__(self, credentials_json: Optional[str] = None):
        """
        Initialize Google Calendar service.

        Args:
            credentials_json: Google Service Account JSON (raw or base64).
                Falls back to GOOGLE_CALENDAR_CREDENTIALS_JSON env var.
        """
        self._service = None
        self._calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self._timezone = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "America/Guayaquil")
        self._is_available = False

        credentials = credentials_json or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
        if credentials:
            self._init_service(credentials)
        else:
            logger.warning("Google Calendar credentials not found — calendar operations will use Supabase only")

    def _init_service(self, credentials_json: str) -> None:
        """Initialize Google Calendar API client."""
        try:
            try:
                credentials_dict = json.loads(credentials_json)
            except json.JSONDecodeError:
                credentials_dict = json.loads(base64.b64decode(credentials_json))

            if credentials_dict.get("type") != "service_account":
                logger.warning("Google Calendar requires Service Account credentials")
                return

            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            self._service = build("calendar", "v3", credentials=credentials)
            self._is_available = True
            logger.info("Google Calendar service initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Google Calendar service: {e}")
            self._is_available = False

    def is_available(self) -> bool:
        """Check if Google Calendar service is available."""
        return self._is_available

    def list_events(self, date_str: str, start_time: str, end_time: str) -> list[dict]:
        """
        List events for a specific date range.

        Args:
            date_str: Date in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format

        Returns:
            List of events (empty list if service unavailable or error)
        """
        if not self._is_available:
            return []

        try:
            start_dt = datetime.fromisoformat(f"{date_str}T{start_time}:00")
            end_dt = datetime.fromisoformat(f"{date_str}T{end_time}:00")

            result = self._service.events().list(
                calendarId=self._calendar_id,
                timeMin=start_dt.isoformat() + "Z",
                timeMax=end_dt.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = [
                e for e in result.get("items", [])
                if e.get("status") != "cancelled"
            ]
            logger.debug(f"Google Calendar: found {len(events)} events on {date_str}")
            return events

        except Exception as e:
            logger.warning(f"Error listing Google Calendar events for {date_str}: {e}")
            return []

    def create_event(
        self,
        date_str: str,
        start_time: str,
        end_time: str,
        summary: str,
        description: str = "",
    ) -> Optional[str]:
        """
        Create event in Google Calendar.

        Args:
            date_str: Date in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            summary: Event title
            description: Event description

        Returns:
            Event ID if successful, None if failed (no exception raised)
        """
        if not self._is_available:
            return None

        try:
            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "dateTime": f"{date_str}T{start_time}:00",
                    "timeZone": self._timezone,
                },
                "end": {
                    "dateTime": f"{date_str}T{end_time}:00",
                    "timeZone": self._timezone,
                },
            }

            result = self._service.events().insert(
                calendarId=self._calendar_id,
                body=event
            ).execute()

            event_id = result.get("id")
            logger.info(f"Google Calendar event created: {event_id} ({summary})")
            return event_id

        except Exception as e:
            logger.warning(f"Failed to create Google Calendar event: {e}")
            return None

    def delete_event(self, event_id: str) -> bool:
        """
        Delete event from Google Calendar.

        Args:
            event_id: Event ID to delete

        Returns:
            True if successful, False if failed (no exception raised)
        """
        if not self._is_available or not event_id:
            return False

        try:
            self._service.events().delete(
                calendarId=self._calendar_id,
                eventId=event_id
            ).execute()
            logger.info(f"Google Calendar event deleted: {event_id}")
            return True

        except Exception as e:
            logger.warning(f"Failed to delete Google Calendar event {event_id}: {e}")
            return False


class AgendamientoModule:
    """Appointment management with Google Calendar integration."""

    # Default business hours: 9am to 6pm
    DEFAULT_START_HOUR = 9
    DEFAULT_END_HOUR = 18
    SLOT_DURATION_MINUTES = 30

    def __init__(self, supabase_client: Any, google_credentials_json: Optional[str] = None):
        """
        Initialize appointment module.

        Args:
            supabase_client: Supabase client instance
            google_credentials_json: Optional Google credentials JSON (raw or base64)
        """
        self.supabase = supabase_client
        self.google = GoogleCalendarService(google_credentials_json)
        logger.info("Appointment module initialized")

    def _get_business_hours(self, client_id: str) -> tuple[int, int, int, int]:
        """
        Get business hours for a client.

        Args:
            client_id: Client ID

        Returns:
            Tuple of (start_hour, start_min, end_hour, end_min)
        """
        try:
            response = self.supabase.table("agentes").select(
                "horario_atencion_inicio,horario_atencion_fin"
            ).eq("cliente_id", client_id).single().execute()

            data = response.data or {}
            start_str = str(data.get("horario_atencion_inicio", "09:00"))[:5]
            end_str = str(data.get("horario_atencion_fin", "18:00"))[:5]

            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))

            return start_h, start_m, end_h, end_m

        except Exception as e:
            logger.debug(f"Error fetching business hours for {client_id}: {e}, using defaults")
            return self.DEFAULT_START_HOUR, 0, self.DEFAULT_END_HOUR, 0

    def _generate_slots(self, start_hour: int, start_min: int, end_hour: int, end_min: int) -> list[str]:
        """
        Generate 30-minute time slots between start and end times.

        Args:
            start_hour: Start hour (0-23)
            start_min: Start minute (0-59)
            end_hour: End hour (0-23)
            end_min: End minute (0-59)

        Returns:
            List of time slots in HH:MM format
        """
        slots = []
        current = datetime.combine(date.today(), time(start_hour, start_min))
        end = datetime.combine(date.today(), time(end_hour, end_min))

        while current < end:
            slots.append(f"{current.hour:02d}:{current.minute:02d}")
            current += timedelta(minutes=self.SLOT_DURATION_MINUTES)

        return slots

    def _get_booked_slots(self, client_id: str, date_str: str) -> set[str]:
        """
        Get all booked time slots for a date from both Supabase and Google Calendar.

        Args:
            client_id: Client ID
            date_str: Date in YYYY-MM-DD format

        Returns:
            Set of booked time slots in HH:MM format
        """
        booked = set()

        try:
            response = self.supabase.table("citas").select(
                "hora,duracion_minutos"
            ).eq("cliente_id", client_id).eq("fecha", date_str).neq(
                "estado", "cancelada"
            ).execute()

            for cita in response.data or []:
                hora = str(cita.get("hora", ""))[:5]
                duracion = int(cita.get("duracion_minutos", 30))
                booked.update(self._block_slots(hora, duracion))
                logger.debug(f"Blocked slots from Supabase: {hora} + {duracion}min")

        except Exception as e:
            logger.warning(f"Error fetching booked appointments from Supabase: {e}")

        if self.google.is_available():
            start_h, start_m, end_h, end_m = self._get_business_hours(client_id)
            start_str = f"{start_h:02d}:{start_m:02d}"
            end_str = f"{end_h:02d}:{end_m:02d}"

            try:
                events = self.google.list_events(date_str, start_str, end_str)
                for event in events:
                    start_iso = event.get("start", {}).get("dateTime", "")
                    end_iso = event.get("end", {}).get("dateTime", "")

                    if start_iso and end_iso:
                        start_time = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                        end_time = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))

                        event_start = start_time.strftime("%H:%M")
                        duration_min = int((end_time - start_time).total_seconds() / 60)

                        booked.update(self._block_slots(event_start, duration_min))
                        logger.debug(f"Blocked slots from Google Calendar: {event_start} + {duration_min}min")

            except Exception as e:
                logger.warning(f"Error fetching Google Calendar events: {e}")

        return booked

    def _block_slots(self, start_time: str, duration_minutes: int) -> set[str]:
        """
        Get all 30-minute slots blocked by an appointment.

        Args:
            start_time: Start time in HH:MM format
            duration_minutes: Duration in minutes

        Returns:
            Set of blocked time slots
        """
        try:
            hour, minute = map(int, start_time.split(":"))
            start = datetime.combine(date.today(), time(hour, minute))
            end = start + timedelta(minutes=duration_minutes)

            blocked = set()
            current = start
            while current < end:
                blocked.add(f"{current.hour:02d}:{current.minute:02d}")
                current += timedelta(minutes=self.SLOT_DURATION_MINUTES)

            return blocked

        except Exception as e:
            logger.error(f"Error calculating blocked slots for {start_time}: {e}")
            return set()

    async def consultar_disponibilidad(
        self,
        client_id: str,
        fecha: str,
    ) -> dict[str, Any]:
        """
        Check real availability for a specific date.

        Queries both Google Calendar and Supabase to determine available slots.

        Args:
            client_id: Client ID
            fecha: Date in YYYY-MM-DD format

        Returns:
            Dict with available slots, booked slots, and business hours
        """
        logger.info(f"Checking availability for client {client_id} on {fecha}")

        try:
            start_h, start_m, end_h, end_m = self._get_business_hours(client_id)
            start_str = f"{start_h:02d}:{start_m:02d}"
            end_str = f"{end_h:02d}:{end_m:02d}"

            all_slots = self._generate_slots(start_h, start_m, end_h, end_m)
            booked = self._get_booked_slots(client_id, fecha)

            available = [s for s in all_slots if s not in booked]

            result = {
                "fecha": fecha,
                "disponibles": available,
                "ocupados": sorted(booked),
                "horario_atencion": f"{start_str} - {end_str}",
                "total_disponibles": len(available),
                "total_ocupados": len(booked),
            }

            if available:
                result["message"] = (
                    f"✓ Tenemos {len(available)} horarios disponibles para el {fecha}. "
                    f"¿Cuál te acomoda mejor?"
                )
            else:
                result["message"] = (
                    f"Lamentablemente el {fecha} está completamente reservado. "
                    f"¿Quieres intentar otro día?"
                )

            logger.info(f"Availability check: {len(available)} slots available, {len(booked)} booked")
            return result

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {
                "fecha": fecha,
                "error": f"Error al verificar disponibilidad: {str(e)}",
                "disponibles": [],
                "ocupados": [],
            }

    async def crear_cita(
        self,
        client_id: str,
        fecha: str,
        hora: str,
        duracion_minutos: int,
        cliente_nombre: str,
        user_id: Optional[str] = None,
        cliente_email: Optional[str] = None,
        telefono_cliente: Optional[str] = None,
        servicio_nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create appointment after verifying availability.

        If Google Calendar fails, appointment is still created in Supabase.

        Args:
            client_id: Client ID (business)
            user_id: User ID (end user/customer)
            fecha: Date in YYYY-MM-DD format
            hora: Time in HH:MM format
            duracion_minutos: Duration in minutes
            cliente_nombre: Customer name
            cliente_email: Optional customer email
            telefono_cliente: Optional customer phone
            servicio_nombre: Optional service name
            descripcion: Optional appointment description

        Returns:
            Dict with success status and appointment details
        """
        logger.info(
            f"Creating appointment: client={client_id}, "
            f"date={fecha}, time={hora}, customer={cliente_nombre}"
        )

        try:
            availability = await self.consultar_disponibilidad(client_id, fecha)

            if hora not in availability.get("disponibles", []):
                logger.warning(f"Slot {hora} not available on {fecha}")
                return {
                    "error": f"El horario {hora} no está disponible en {fecha}",
                    "disponibles": availability.get("disponibles", []),
                    "ocupados": availability.get("ocupados", []),
                    "horario_atencion": availability.get("horario_atencion", ""),
                    "message": availability.get("message", ""),
                }

            end_dt = datetime.fromisoformat(f"{fecha}T{hora}:00") + timedelta(
                minutes=duracion_minutos
            )
            end_time = end_dt.strftime("%H:%M")

            summary = f"{servicio_nombre} - {cliente_nombre}" if servicio_nombre else f"Cita - {cliente_nombre}"

            google_event_id = None
            if self.google.is_available():
                google_event_id = self.google.create_event(
                    date_str=fecha,
                    start_time=hora,
                    end_time=end_time,
                    summary=summary,
                    description=descripcion or f"Cliente: {cliente_nombre}\nEmail: {cliente_email or 'N/A'}",
                )

            appointment = {
                "cliente_id": client_id,
                "usuario_id": user_id,
                "nombre_cliente": cliente_nombre,
                "email_cliente": cliente_email or "",
                "telefono_cliente": telefono_cliente or "",
                "servicio": servicio_nombre or "Cita general",
                "fecha": fecha,
                "hora": hora,
                "duracion_minutos": duracion_minutos,
                "estado": "confirmada",
                "google_event_id": google_event_id,
                "notas": descripcion or "",
            }

            response = self.supabase.table("citas").insert(appointment).execute()
            appointment_id = response.data[0].get("id") if response.data else None

            logger.info(
                f"Appointment created: id={appointment_id}, google_id={google_event_id}, "
                f"customer={cliente_nombre}"
            )

            return {
                "success": True,
                "appointment_id": appointment_id,
                "google_event_id": google_event_id,
                "fecha": fecha,
                "hora": hora,
                "cliente_nombre": cliente_nombre,
                "message": f"✓ Cita agendada para {fecha} a las {hora}",
            }

        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return {
                "error": f"Error al crear la cita: {str(e)}",
                "message": "Lo siento, hubo un problema al crear la cita. Por favor intenta nuevamente.",
            }

    async def cancelar_cita(
        self,
        client_id: str,
        cita_id: str,
        user_id: Optional[str] = None,
        motivo: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Cancel appointment.

        Args:
            client_id: Client ID (business)
            user_id: User ID (end user/customer)
            cita_id: Appointment ID
            motivo: Optional cancellation reason

        Returns:
            Dict with cancellation confirmation
        """
        logger.info(f"Cancelling appointment: id={cita_id}, client={client_id}, user={user_id}")

        try:
            response = self.supabase.table("citas").select(
                "id,google_event_id,nombre_cliente,fecha,hora"
            ).eq("id", cita_id).eq("cliente_id", client_id).eq(
                "usuario_id", user_id
            ).single().execute()

            if not response.data:
                logger.warning(f"Appointment {cita_id} not found")
                return {
                    "error": f"No se encontró la cita con ID {cita_id}",
                    "message": "No tengo citas con ese ID en el sistema.",
                }

            appointment = response.data
            google_event_id = appointment.get("google_event_id")

            if google_event_id:
                self.google.delete_event(google_event_id)

            self.supabase.table("citas").update({
                "estado": "cancelada",
                "notas": motivo or "Cancelada por usuario",
            }).eq("id", cita_id).execute()

            logger.info(f"Appointment {cita_id} cancelled successfully")

            return {
                "success": True,
                "appointment_id": cita_id,
                "fecha_original": appointment["fecha"],
                "hora_original": appointment["hora"],
                "message": f"✓ Cita del {appointment['fecha']} a las {appointment['hora']} cancelada",
            }

        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {
                "error": f"Error al cancelar la cita: {str(e)}",
                "message": "Lo siento, hubo un problema al cancelar la cita.",
            }

    async def reagendar_cita(
        self,
        client_id: str,
        cita_id: str,
        nueva_fecha: str,
        nueva_hora: str,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Reschedule appointment to new date/time.

        If Google Calendar fails, update is still saved in Supabase.

        Args:
            client_id: Client ID (business)
            user_id: User ID (end user/customer)
            cita_id: Appointment ID
            nueva_fecha: New date in YYYY-MM-DD format
            nueva_hora: New time in HH:MM format

        Returns:
            Dict with new appointment details
        """
        logger.info(
            f"Rescheduling appointment: id={cita_id}, "
            f"new_date={nueva_fecha}, new_time={nueva_hora}, user={user_id}"
        )

        try:
            response = self.supabase.table("citas").select(
                "id,nombre_cliente,email_cliente,telefono_cliente,servicio,"
                "duracion_minutos,notas,google_event_id,fecha,hora"
            ).eq("id", cita_id).eq("cliente_id", client_id).eq(
                "usuario_id", user_id
            ).single().execute()

            if not response.data:
                logger.warning(f"Appointment {cita_id} not found for rescheduling")
                return {
                    "error": f"No se encontró la cita con ID {cita_id}",
                    "message": "No tengo citas con ese ID en el sistema.",
                }

            old_appointment = response.data

            availability = await self.consultar_disponibilidad(client_id, nueva_fecha)
            if nueva_hora not in availability.get("disponibles", []):
                logger.warning(f"Slot {nueva_hora} not available on {nueva_fecha}")
                return {
                    "error": f"El horario {nueva_hora} no está disponible en {nueva_fecha}",
                    "disponibles": availability.get("disponibles", []),
                    "ocupados": availability.get("ocupados", []),
                    "horario_atencion": availability.get("horario_atencion", ""),
                    "message": availability.get("message", ""),
                }

            old_google_event_id = old_appointment.get("google_event_id")
            duracion = old_appointment.get("duracion_minutos", 30)
            servicio = old_appointment.get("servicio", "Cita general")
            nombre = old_appointment.get("nombre_cliente", "")

            if old_google_event_id:
                self.google.delete_event(old_google_event_id)

            new_google_event_id = None
            if self.google.is_available():
                end_dt = datetime.fromisoformat(f"{nueva_fecha}T{nueva_hora}:00") + timedelta(
                    minutes=duracion
                )
                end_time = end_dt.strftime("%H:%M")

                summary = f"{servicio} - {nombre}"
                new_google_event_id = self.google.create_event(
                    date_str=nueva_fecha,
                    start_time=nueva_hora,
                    end_time=end_time,
                    summary=summary,
                    description=old_appointment.get("notas", ""),
                )

            self.supabase.table("citas").update({
                "fecha": nueva_fecha,
                "hora": nueva_hora,
                "google_event_id": new_google_event_id,
                "estado": "confirmada",
            }).eq("id", cita_id).execute()

            logger.info(
                f"Appointment {cita_id} rescheduled: "
                f"{old_appointment['fecha']} {old_appointment['hora']} -> "
                f"{nueva_fecha} {nueva_hora}"
            )

            return {
                "success": True,
                "appointment_id": cita_id,
                "fecha_anterior": old_appointment["fecha"],
                "hora_anterior": old_appointment["hora"],
                "nueva_fecha": nueva_fecha,
                "nueva_hora": nueva_hora,
                "message": (
                    f"✓ Cita reprogramada: "
                    f"{old_appointment['fecha']} {old_appointment['hora']} → "
                    f"{nueva_fecha} {nueva_hora}"
                ),
            }

        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {
                "error": f"Error al reprogramar la cita: {str(e)}",
                "message": "Lo siento, hubo un problema al reprogramar la cita.",
            }

    async def obtener_citas_usuario(
        self,
        client_id: str,
        user_id: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Get existing appointments for a specific user.

        Used to find appointments before rescheduling or canceling.

        Args:
            client_id: Client ID (business)
            user_id: User ID (end user/customer)
            limit: Max appointments to return

        Returns:
            Dict with list of appointments
        """
        logger.info(f"Fetching appointments for client={client_id}, user={user_id} (limit={limit})")

        try:
            response = self.supabase.table("citas").select(
                "id,nombre_cliente,email_cliente,servicio,fecha,hora,estado"
            ).eq("cliente_id", client_id).eq("usuario_id", user_id).eq(
                "estado", "confirmada"
            ).order(
                "fecha", desc=False
            ).limit(limit).execute()

            appointments = response.data or []

            message = (
                f"Encontré {len(appointments)} cita(s) confirmada(s) para ti."
                if appointments
                else "No hay citas confirmadas en el sistema."
            )

            logger.info(f"Found {len(appointments)} appointments for client={client_id}, user={user_id}")

            return {
                "success": True,
                "appointments": appointments,
                "total": len(appointments),
                "message": message,
            }

        except Exception as e:
            logger.error(f"Error fetching appointments for client={client_id}, user={user_id}: {e}")
            return {
                "success": False,
                "error": f"Error al obtener citas: {str(e)}",
                "appointments": [],
                "total": 0,
                "message": "No pude recuperar tus citas del sistema.",
            }
