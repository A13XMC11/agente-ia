"""
Lead qualification module: automatic lead scoring and categorization.

Handles lead profiling, score calculation, and state transitions
based on interaction patterns and behavior.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import os

logger = logging.getLogger(__name__)


class CalificacionModule:
    """Lead scoring and qualification operations."""

    def __init__(self, supabase_client: Any):
        """
        Initialize lead qualification module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.score_threshold_hot = float(
            os.environ.get("LEAD_SCORE_HOT_THRESHOLD", 8)
        )
        self.notification_enabled = (
            os.environ.get("LEAD_SCORE_NOTIFICATION_ENABLED", "true").lower() == "true"
        )

    async def guardar_lead(
        self,
        client_id: str,
        usuario_id: str,
        nombre: str,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        empresa: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Save or update lead information.

        Args:
            client_id: Client ID
            usuario_id: User ID (lead identifier)
            nombre: Lead name
            email: Lead email
            telefono: Lead phone
            empresa: Lead company
            tags: Tags for categorization

        Returns:
            Lead profile with score
        """
        try:
            # Check if lead exists
            existing_response = self.supabase.table("leads").select("*").eq(
                "client_id", client_id
            ).eq("user_id", usuario_id).execute()

            lead_data = {
                "client_id": client_id,
                "user_id": usuario_id,
                "name": nombre,
                "email": email,
                "phone": telefono,
                "company": empresa,
                "tags": tags or [],
                "updated_at": datetime.utcnow().isoformat(),
            }

            if existing_response.data:
                # Update existing lead
                lead_id = existing_response.data[0]["id"]
                self.supabase.table("leads").update(lead_data).eq(
                    "id", lead_id
                ).execute()

                logger.info(
                    f"Lead updated: {usuario_id} ({nombre})",
                    extra={"client_id": client_id},
                )

                return {
                    "success": True,
                    "lead_id": lead_id,
                    "action": "updated",
                    "message": f"Lead {nombre} actualizado",
                }
            else:
                # Create new lead
                new_lead = {
                    "id": str(uuid4()),
                    **lead_data,
                    "score": 0.0,
                    "state": "curioso",  # Initial state
                    "urgency": 0.0,
                    "budget": None,
                    "decision_power": 0.0,
                    "interaction_count": 0,
                    "last_interaction": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                }

                self.supabase.table("leads").insert(new_lead).execute()

                logger.info(
                    f"Lead created: {usuario_id} ({nombre})",
                    extra={"client_id": client_id},
                )

                return {
                    "success": True,
                    "lead_id": new_lead["id"],
                    "action": "created",
                    "message": f"Lead {nombre} guardado",
                }

        except Exception as e:
            logger.error(f"Error saving lead: {e}")
            return {"error": str(e)}

    async def actualizar_score_lead(
        self,
        client_id: str,
        usuario_id: str,
        score: float,
        razon: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update lead qualification score (0-10 scale).

        Automatically transitions lead state based on score:
        - 0-3: curioso (just browsing)
        - 4-7: prospecto (showed interest)
        - 8-10: caliente (hot lead)

        Args:
            client_id: Client ID
            usuario_id: User ID
            score: New score (0-10)
            razon: Reason for score update

        Returns:
            Updated lead with new state and notifications
        """
        try:
            if not (0 <= score <= 10):
                return {"error": "Score must be between 0 and 10"}

            # Fetch lead
            lead_response = self.supabase.table("leads").select("*").eq(
                "client_id", client_id
            ).eq("user_id", usuario_id).single().execute()

            lead = lead_response.data

            # Calculate new state based on score
            if score >= self.score_threshold_hot:
                new_state = "caliente"
            elif score >= 4:
                new_state = "prospecto"
            else:
                new_state = "curioso"

            old_state = lead.get("state", "curioso")

            # Update lead
            update_data = {
                "score": score,
                "state": new_state,
                "score_reason": razon,
                "score_updated_at": datetime.utcnow().isoformat(),
                "interaction_count": lead.get("interaction_count", 0) + 1,
                "last_interaction": datetime.utcnow().isoformat(),
            }

            self.supabase.table("leads").update(update_data).eq(
                "id", lead["id"]
            ).execute()

            result = {
                "success": True,
                "lead_id": lead["id"],
                "usuario_id": usuario_id,
                "old_score": lead.get("score", 0),
                "new_score": score,
                "old_state": old_state,
                "new_state": new_state,
                "message": f"Score actualizado a {score}/10",
            }

            # Send notification if hot lead and state changed
            if (
                new_state == "caliente"
                and old_state != "caliente"
                and self.notification_enabled
            ):
                notification = await self._send_hot_lead_notification(
                    client_id, lead, score
                )
                result["notification"] = notification

            logger.info(
                f"Lead score updated: {usuario_id} -> {score} ({new_state})",
                extra={"client_id": client_id},
            )

            return result

        except Exception as e:
            logger.error(f"Error updating lead score: {e}")
            return {"error": str(e)}

    async def _send_hot_lead_notification(
        self,
        client_id: str,
        lead: dict[str, Any],
        score: float,
    ) -> dict[str, Any]:
        """
        Send notification when lead becomes hot.

        Args:
            client_id: Client ID
            lead: Lead data
            score: Lead score

        Returns:
            Notification status
        """
        try:
            notification = {
                "id": str(uuid4()),
                "client_id": client_id,
                "type": "hot_lead",
                "lead_id": lead["id"],
                "lead_name": lead.get("name"),
                "score": score,
                "message": f"🔥 Lead Caliente: {lead.get('name')} (Score: {score}/10)",
                "priority": "high",
                "created_at": datetime.utcnow().isoformat(),
                "read": False,
            }

            self.supabase.table("notifications").insert(notification).execute()

            logger.info(
                f"Hot lead notification sent for {lead['name']} (score: {score})",
                extra={"client_id": client_id},
            )

            return {"sent": True, "notification_id": notification["id"]}

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {"sent": False, "error": str(e)}

    async def get_lead_score_factors(
        self,
        client_id: str,
        usuario_id: str,
    ) -> dict[str, Any]:
        """
        Get breakdown of lead score factors.

        Args:
            client_id: Client ID
            usuario_id: User ID

        Returns:
            Score breakdown with contributing factors
        """
        try:
            # Fetch lead
            lead_response = self.supabase.table("leads").select("*").eq(
                "client_id", client_id
            ).eq("user_id", usuario_id).single().execute()

            lead = lead_response.data

            # Fetch conversation metrics
            conversation_response = self.supabase.table("conversaciones").select(
                "id"
            ).eq("client_id", client_id).eq("user_id", usuario_id).execute()

            num_conversations = len(conversation_response.data or [])

            # Fetch message count
            messages_response = self.supabase.table("mensajes").select(
                "id", count="exact"
            ).eq("client_id", client_id).eq("user_id", usuario_id).execute()

            num_messages = messages_response.count or 0

            # Calculate recency score (0-2 points)
            last_interaction = datetime.fromisoformat(lead.get("last_interaction", ""))
            days_since = (datetime.utcnow() - last_interaction).days
            recency_score = max(0, 2 - (days_since / 7))

            # Calculate engagement score (0-3 points)
            engagement_score = min(3, num_messages / 10)

            # Get other factors
            urgency = lead.get("urgency", 0)
            decision_power = lead.get("decision_power", 0)
            budget = lead.get("budget", 0)

            factors = {
                "recency": round(recency_score, 2),
                "engagement": round(engagement_score, 2),
                "urgency": urgency,
                "decision_power": decision_power,
                "budget": budget,
                "conversations": num_conversations,
                "messages": num_messages,
                "interaction_count": lead.get("interaction_count", 0),
                "current_score": lead.get("score", 0),
                "current_state": lead.get("state", "curioso"),
            }

            return factors

        except Exception as e:
            logger.error(f"Error getting score factors: {e}")
            return {"error": str(e)}

    async def get_hot_leads(
        self,
        client_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get all hot leads (score >= threshold) for a client.

        Args:
            client_id: Client ID
            limit: Max results

        Returns:
            List of hot leads sorted by score descending
        """
        try:
            response = self.supabase.table("leads").select("*").eq(
                "client_id", client_id
            ).gte("score", self.score_threshold_hot).order(
                "score", desc=True
            ).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching hot leads: {e}")
            return []

    async def get_leads_by_state(
        self,
        client_id: str,
        state: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get leads filtered by state.

        Args:
            client_id: Client ID
            state: Lead state (curioso, prospecto, caliente, cliente, descartado)
            limit: Max results

        Returns:
            List of leads in specified state
        """
        try:
            response = self.supabase.table("leads").select("*").eq(
                "client_id", client_id
            ).eq("state", state).order(
                "score", desc=True
            ).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching leads by state: {e}")
            return []

    async def get_lead_pipeline_summary(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """
        Get pipeline summary with lead counts by state.

        Args:
            client_id: Client ID

        Returns:
            Pipeline with counts and average scores per state
        """
        try:
            response = self.supabase.table("leads").select(
                "state, score"
            ).eq("client_id", client_id).execute()

            leads = response.data or []

            pipeline = {
                "curioso": {"count": 0, "avg_score": 0},
                "prospecto": {"count": 0, "avg_score": 0},
                "caliente": {"count": 0, "avg_score": 0},
                "cliente": {"count": 0, "avg_score": 0},
                "descartado": {"count": 0, "avg_score": 0},
            }

            score_sums = {state: 0 for state in pipeline}

            for lead in leads:
                state = lead.get("state", "curioso")
                if state in pipeline:
                    pipeline[state]["count"] += 1
                    score_sums[state] += lead.get("score", 0)

            for state in pipeline:
                if pipeline[state]["count"] > 0:
                    pipeline[state]["avg_score"] = round(
                        score_sums[state] / pipeline[state]["count"], 2
                    )

            return pipeline

        except Exception as e:
            logger.error(f"Error fetching pipeline summary: {e}")
            return {}
