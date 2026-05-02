"""
Follow-up module: automated follow-up campaigns and lead nurturing.

Handles scheduled follow-ups, reminder sequences, and engagement tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SeguimientoModule:
    """Follow-up and lead nurturing operations."""

    def __init__(self, supabase_client: Any):
        """
        Initialize follow-up module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def crear_seguimiento(
        self,
        client_id: str,
        usuario_id: str,
        tipo: str,
        titulo: str,
        mensaje: str,
        programar_para: Optional[datetime] = None,
        canal: str = "whatsapp",
    ) -> dict[str, Any]:
        """
        Create a follow-up sequence.

        Types: follow_up (24h), post_sale (48h), reactivation (7d)

        Args:
            client_id: Client ID
            usuario_id: User ID to follow up with
            tipo: Follow-up type (follow_up, post_sale, reactivation)
            titulo: Follow-up title
            mensaje: Follow-up message
            programar_para: When to send (default based on type)
            canal: Channel (whatsapp, email)

        Returns:
            Follow-up creation confirmation
        """
        try:
            # Default timing based on type
            if not programar_para:
                if tipo == "follow_up":
                    programar_para = datetime.utcnow() + timedelta(hours=24)
                elif tipo == "post_sale":
                    programar_para = datetime.utcnow() + timedelta(hours=48)
                elif tipo == "reactivation":
                    programar_para = datetime.utcnow() + timedelta(days=7)
                else:
                    programar_para = datetime.utcnow() + timedelta(hours=24)

            followup = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": usuario_id,
                "type": tipo,
                "title": titulo,
                "message": mensaje,
                "channel": canal,
                "scheduled_for": programar_para.isoformat(),
                "status": "scheduled",
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("followups").insert(followup).execute()

            logger.info(
                f"Follow-up created: {tipo} for user {usuario_id}, scheduled for {programar_para}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "followup_id": followup["id"],
                "tipo": tipo,
                "programado_para": programar_para.isoformat(),
                "mensaje": "Seguimiento programado",
            }

        except Exception as e:
            logger.error(f"Error creating follow-up: {e}")
            return {"error": str(e)}

    async def crear_secuencia_24h(
        self,
        client_id: str,
        usuario_id: str,
        titulo: str,
    ) -> dict[str, Any]:
        """
        Create 24-hour follow-up sequence.

        Default flow: 1h, 6h, 24h

        Args:
            client_id: Client ID
            usuario_id: User ID
            titulo: Sequence title

        Returns:
            Sequence creation confirmation
        """
        try:
            now = datetime.utcnow()

            messages = [
                {
                    "title": f"{titulo} - Recordatorio 1h",
                    "message": f"Hola! 👋 Te escribo para confirmar tu interés en {titulo}. ¿Tienes alguna pregunta?",
                    "delay_hours": 1,
                },
                {
                    "title": f"{titulo} - Recordatorio 6h",
                    "message": f"Sabemos que {titulo} puede ser una decisión importante. Estamos aquí para resolver tus dudas.",
                    "delay_hours": 6,
                },
                {
                    "title": f"{titulo} - Última Oportunidad",
                    "message": f"Esta es tu última oportunidad hoy para obtener {titulo}. Contáctanos antes de las 5pm.",
                    "delay_hours": 24,
                },
            ]

            sequence_id = str(uuid4())

            for idx, msg in enumerate(messages):
                schedule_time = now + timedelta(hours=msg["delay_hours"])

                followup = {
                    "id": str(uuid4()),
                    "cliente_id": client_id,
                    "user_id": usuario_id,
                    "type": "follow_up_sequence",
                    "sequence_id": sequence_id,
                    "sequence_step": idx + 1,
                    "title": msg["title"],
                    "message": msg["message"],
                    "scheduled_for": schedule_time.isoformat(),
                    "status": "scheduled",
                    "created_at": datetime.utcnow().isoformat(),
                }

                self.supabase.table("followups").insert(followup).execute()

            logger.info(
                f"24h follow-up sequence created: {sequence_id} for user {usuario_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "sequence_id": sequence_id,
                "steps": len(messages),
                "mensaje": "Secuencia de 24h programada",
            }

        except Exception as e:
            logger.error(f"Error creating 24h sequence: {e}")
            return {"error": str(e)}

    async def crear_secuencia_post_venta(
        self,
        client_id: str,
        usuario_id: str,
        producto: str,
    ) -> dict[str, Any]:
        """
        Create post-sale follow-up sequence.

        Sequence: 48h, 3d, 7d

        Args:
            client_id: Client ID
            usuario_id: User ID who purchased
            producto: Product name

        Returns:
            Sequence creation confirmation
        """
        try:
            now = datetime.utcnow()

            messages = [
                {
                    "title": "Gracias por tu compra",
                    "message": f"¡Gracias por comprar {producto}! 🎉 ¿Cómo te está yendo con tu compra?",
                    "delay_days": 2,
                },
                {
                    "title": "Necesitas ayuda?",
                    "message": f"Queremos asegurarnos que {producto} cumpla tus expectativas. ¿Preguntas o problemas?",
                    "delay_days": 3,
                },
                {
                    "title": "Déjanos un testimonio",
                    "message": f"Tu experiencia con {producto} es importante. ¿Podrías compartir tu opinión?",
                    "delay_days": 7,
                },
            ]

            sequence_id = str(uuid4())

            for idx, msg in enumerate(messages):
                schedule_time = now + timedelta(days=msg["delay_days"])

                followup = {
                    "id": str(uuid4()),
                    "cliente_id": client_id,
                    "user_id": usuario_id,
                    "type": "post_sale_sequence",
                    "sequence_id": sequence_id,
                    "sequence_step": idx + 1,
                    "title": msg["title"],
                    "message": msg["message"],
                    "scheduled_for": schedule_time.isoformat(),
                    "status": "scheduled",
                    "created_at": datetime.utcnow().isoformat(),
                }

                self.supabase.table("followups").insert(followup).execute()

            logger.info(
                f"Post-sale sequence created: {sequence_id} for user {usuario_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "sequence_id": sequence_id,
                "steps": len(messages),
                "mensaje": "Secuencia post-venta programada",
            }

        except Exception as e:
            logger.error(f"Error creating post-sale sequence: {e}")
            return {"error": str(e)}

    async def crear_secuencia_reactivacion(
        self,
        client_id: str,
        usuario_id: str,
        dias_inactivo: int = 30,
    ) -> dict[str, Any]:
        """
        Create reactivation campaign for inactive leads.

        Sequence: 1d, 3d, 7d, 14d

        Args:
            client_id: Client ID
            usuario_id: Inactive user ID
            dias_inactivo: Days without interaction

        Returns:
            Sequence creation confirmation
        """
        try:
            now = datetime.utcnow()

            messages = [
                {
                    "title": "Te echamos de menos",
                    "message": f"¡Hola! Hace {dias_inactivo} días que no te vemos. ¿Cómo estás? 👋",
                    "delay_days": 1,
                },
                {
                    "title": "Nostalgia",
                    "message": "Tenemos nuevas ofertas que creo te interesarían. ¿Te gustaría verlas?",
                    "delay_days": 3,
                },
                {
                    "title": "Descuento Especial",
                    "message": "Solo para ti: 15% de descuento en tu próxima compra. ¡Válido por 7 días!",
                    "delay_days": 7,
                },
                {
                    "title": "Última Chance",
                    "message": "El descuento especial vence hoy. ¿Te lo vas a perder? 😢",
                    "delay_days": 14,
                },
            ]

            sequence_id = str(uuid4())

            for idx, msg in enumerate(messages):
                schedule_time = now + timedelta(days=msg["delay_days"])

                followup = {
                    "id": str(uuid4()),
                    "cliente_id": client_id,
                    "user_id": usuario_id,
                    "type": "reactivation_sequence",
                    "sequence_id": sequence_id,
                    "sequence_step": idx + 1,
                    "title": msg["title"],
                    "message": msg["message"],
                    "scheduled_for": schedule_time.isoformat(),
                    "status": "scheduled",
                    "created_at": datetime.utcnow().isoformat(),
                }

                self.supabase.table("followups").insert(followup).execute()

            logger.info(
                f"Reactivation sequence created: {sequence_id} for user {usuario_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "sequence_id": sequence_id,
                "steps": len(messages),
                "mensaje": "Secuencia de reactivación programada",
            }

        except Exception as e:
            logger.error(f"Error creating reactivation sequence: {e}")
            return {"error": str(e)}

    async def ejecutar_seguimientos_vencidos(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """
        Execute all due follow-ups (internal cron job).

        Args:
            client_id: Client ID

        Returns:
            Execution summary
        """
        try:
            now = datetime.utcnow()

            # Fetch due follow-ups
            response = self.supabase.table("followups").select("*").eq(
                "cliente_id", client_id
            ).eq("status", "scheduled").lte(
                "scheduled_for", now.isoformat()
            ).execute()

            due_followups = response.data or []

            executed = 0
            failed = 0

            for followup in due_followups:
                try:
                    # Mark as sent (actual delivery handled by worker)
                    self.supabase.table("followups").update(
                        {"status": "sent", "sent_at": datetime.utcnow().isoformat()}
                    ).eq("id", followup["id"]).execute()

                    executed += 1

                except Exception as e:
                    logger.error(f"Error executing followup {followup['id']}: {e}")
                    failed += 1

            logger.info(
                f"Executed {executed} follow-ups, {failed} failed",
                extra={"client_id": client_id},
            )

            return {
                "executed": executed,
                "failed": failed,
                "total": len(due_followups),
            }

        except Exception as e:
            logger.error(f"Error executing followups: {e}")
            return {"error": str(e)}

    async def get_followups_pendientes(
        self,
        client_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get pending follow-ups for a client.

        Args:
            client_id: Client ID
            limit: Max results

        Returns:
            List of pending follow-ups
        """
        try:
            now = datetime.utcnow()

            response = self.supabase.table("followups").select("*").eq(
                "cliente_id", client_id
            ).eq("status", "scheduled").lte(
                "scheduled_for", now.isoformat()
            ).order("scheduled_for", desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching pending followups: {e}")
            return []

    async def get_seguimientos_por_usuario(
        self,
        client_id: str,
        usuario_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get all follow-ups for a specific user.

        Args:
            client_id: Client ID
            usuario_id: User ID

        Returns:
            List of follow-ups
        """
        try:
            response = self.supabase.table("followups").select("*").eq(
                "cliente_id", client_id
            ).eq("user_id", usuario_id).order(
                "scheduled_for", desc=True
            ).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching user followups: {e}")
            return []
