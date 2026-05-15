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

logger = logging.getLogger(__name__)


class AppointmentError(Exception):
    pass


class GoogleCalendarService:
    def __init__(self, credentials_json: Optional[str] = None):
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
        return self._is_available

    def list_events(self, date_str: str, start_time: str, end_time: str) -> list[dict]:
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
                showDeleted=False,
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
    DEFAULT_START_HOUR = 9
    DEFAULT_END_HOUR = 18
    SLOT_DURATION_MINUTES = 30

    def __init__(self, supabase_client: Any, google_credentials_json: Optional[str] = None,
                 alertas_module: Any = None):
        self.supabase = supabase_client
        self.alertas = alertas_module
        self.google = GoogleCalendarService(google_credentials_json)
        logger.info("Appointment module initialized")

    def _generate_slots(self, start_hour: int, end_hour: int) -> list[str]:
        slots = []
        current = datetime.combine(date.today(), time(start_hour, 0))
        end = datetime.combine(date.today(), time(end_hour, 0))

        while current < end:
            slots.append(f"{current.hour:02d}:{current.minute:02d}")
            current += timedelta(minutes=self.SLOT_DURATION_MINUTES)

        return slots

    def _get_booked_slots(self, cliente_id: str, fecha: str) -> set[str]:
        booked = set()

        try:
            response = self.supabase.table("citas").select(
                "hora,duracion_minutos"
            ).eq("cliente_id", cliente_id).eq("fecha", fecha).neq(
                "estado", "cancelada"
            ).execute()

            for cita in response.data or []:
                hora = str(cita.get("hora", ""))[:5]
                duracion = int(cita.get("duracion_minutos", 30))
                booked.update(self._block_slots(hora, duracion))

        except Exception as e:
            logger.warning(f"Error fetching booked appointments from Supabase: {e}")

        if self.google.is_available():
            try:
                start_str = f"{self.DEFAULT_START_HOUR:02d}:00"
                end_str = f"{self.DEFAULT_END_HOUR:02d}:00"

                events = self.google.list_events(fecha, start_str, end_str)
                for event in events:
                    start_iso = event.get("start", {}).get("dateTime", "")
                    end_iso = event.get("end", {}).get("dateTime", "")

                    if start_iso and end_iso:
                        start_time = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                        end_time = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))

                        event_start = start_time.strftime("%H:%M")
                        duration_min = int((end_time - start_time).total_seconds() / 60)

                        booked.update(self._block_slots(event_start, duration_min))

            except Exception as e:
                logger.warning(f"Error fetching Google Calendar events: {e}")

        return booked

    def _block_slots(self, start_time: str, duration_minutes: int) -> set[str]:
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
        cliente_id: str,
        fecha: str,
    ) -> dict[str, Any]:
        logger.info(f"Checking availability for client {cliente_id} on {fecha}")

        try:
            all_slots = self._generate_slots(self.DEFAULT_START_HOUR, self.DEFAULT_END_HOUR)
            booked = self._get_booked_slots(cliente_id, fecha)
            available = [s for s in all_slots if s not in booked]

            result = {
                "fecha": fecha,
                "disponibles": available,
                "ocupados": sorted(booked),
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
        cliente_id: str,
        fecha: str,
        hora: str,
        nombre_cliente: str,
        telefono_cliente: str,
        servicio: str,
        email_cliente: str = "",
        duracion_minutos: int = 60,
    ) -> dict[str, Any]:
        logger.info(
            f"Creating appointment: cliente_id={cliente_id}, "
            f"fecha={fecha}, hora={hora}, cliente={nombre_cliente}"
        )

        try:
            availability = await self.consultar_disponibilidad(cliente_id, fecha)

            if hora not in availability.get("disponibles", []):
                logger.warning(f"Slot {hora} not available on {fecha}")
                return {
                    "error": f"El horario {hora} no está disponible en {fecha}",
                    "disponibles": availability.get("disponibles", []),
                    "ocupados": availability.get("ocupados", []),
                    "message": availability.get("message", ""),
                }

            end_dt = datetime.fromisoformat(f"{fecha}T{hora}:00") + timedelta(
                minutes=duracion_minutos
            )
            end_time = end_dt.strftime("%H:%M")

            summary = f"{servicio} - {nombre_cliente}"

            google_event_id = None
            if self.google.is_available():
                google_event_id = self.google.create_event(
                    date_str=fecha,
                    start_time=hora,
                    end_time=end_time,
                    summary=summary,
                    description=f"Cliente: {nombre_cliente}\nEmail: {email_cliente or 'N/A'}",
                )

            appointment = {
                "cliente_id": cliente_id,
                "nombre_cliente": nombre_cliente,
                "email_cliente": email_cliente or "",
                "telefono_cliente": telefono_cliente,
                "servicio": servicio,
                "fecha": fecha,
                "hora": hora,
                "duracion_minutos": duracion_minutos,
                "estado": "confirmada",
                "google_event_id": google_event_id,
            }

            response = self.supabase.table("citas").insert(appointment).execute()
            cita_id = response.data[0].get("id") if response.data else None

            logger.info(
                f"Appointment created: id={cita_id}, google_id={google_event_id}, "
                f"cliente={nombre_cliente}"
            )

            # Send important alert to owner about new appointment
            if self.alertas:
                try:
                    mensaje = (
                        f"Nueva cita agendada:\n\n"
                        f"👤 Cliente: {nombre_cliente}\n"
                        f"📅 Fecha: {fecha}\n"
                        f"🕐 Hora: {hora}\n"
                        f"📋 Servicio: {servicio}\n"
                        f"📱 Teléfono: {telefono_cliente}"
                    )
                    await self.alertas.enviar_alerta_importante(
                        client_id=cliente_id,
                        tipo="appointment_scheduled",
                        mensaje=mensaje,
                        datos_extras={"cita_id": cita_id, "cliente": nombre_cliente},
                    )
                except Exception as alert_err:
                    logger.warning(f"Error sending appointment alert: {alert_err}")

            return {
                "success": True,
                "cita_id": cita_id,
                "fecha": fecha,
                "hora": hora,
                "cliente_nombre": nombre_cliente,
                "message": f"✓ Cita agendada para {fecha} a las {hora}",
            }

        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return {
                "error": f"Error al crear la cita: {str(e)}",
                "message": "Lo siento, hubo un problema al crear la cita. Por favor intenta nuevamente.",
            }

    async def reagendar_cita(
        self,
        cliente_id: str,
        telefono_cliente: str,
        nueva_fecha: str,
        nueva_hora: str,
    ) -> dict[str, Any]:
        logger.info(
            f"Rescheduling appointment: cliente_id={cliente_id}, "
            f"telefono={telefono_cliente}, nueva_fecha={nueva_fecha}, nueva_hora={nueva_hora}"
        )

        try:
            response = self.supabase.table("citas").select(
                "id,nombre_cliente,email_cliente,servicio,"
                "duracion_minutos,google_event_id,fecha,hora"
            ).eq("cliente_id", cliente_id).eq("telefono_cliente", telefono_cliente).eq(
                "estado", "confirmada"
            ).order("created_at", desc=True).limit(1).execute()

            if not response.data:
                logger.warning(f"No confirmed appointment found for cliente_id={cliente_id}, telefono={telefono_cliente}")
                return {
                    "error": "No tienes citas activas para reagendar",
                    "message": "No encontré citas confirmadas en tu nombre.",
                }

            old_appointment = response.data[0]
            cita_id = old_appointment.get("id")

            availability = await self.consultar_disponibilidad(cliente_id, nueva_fecha)
            if nueva_hora not in availability.get("disponibles", []):
                logger.warning(f"Slot {nueva_hora} not available on {nueva_fecha}")
                return {
                    "error": f"El horario {nueva_hora} no está disponible en {nueva_fecha}",
                    "disponibles": availability.get("disponibles", []),
                    "ocupados": availability.get("ocupados", []),
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
                    description="",
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
                "cita_id": cita_id,
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

    async def cancelar_cita(
        self,
        cliente_id: str,
        telefono_cliente: str,
    ) -> dict[str, Any]:
        logger.info(
            f"Cancelling appointment: cliente_id={cliente_id}, "
            f"telefono={telefono_cliente}"
        )

        try:
            response = self.supabase.table("citas").select(
                "id,google_event_id,nombre_cliente,fecha,hora"
            ).eq("cliente_id", cliente_id).eq("telefono_cliente", telefono_cliente).eq(
                "estado", "confirmada"
            ).order("created_at", desc=True).limit(1).execute()

            if not response.data:
                logger.warning(f"No confirmed appointment found for cliente_id={cliente_id}, telefono={telefono_cliente}")
                return {
                    "error": "No tienes citas activas para cancelar",
                    "message": "No encontré citas confirmadas en tu nombre.",
                }

            appointment = response.data[0]
            cita_id = appointment.get("id")
            google_event_id = appointment.get("google_event_id")

            if google_event_id:
                self.google.delete_event(google_event_id)

            self.supabase.table("citas").update({
                "estado": "cancelada",
            }).eq("id", cita_id).execute()

            logger.info(f"Appointment {cita_id} cancelled successfully")

            return {
                "success": True,
                "cita_id": cita_id,
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
