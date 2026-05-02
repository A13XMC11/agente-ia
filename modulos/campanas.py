"""
Campaigns module: bulk messaging campaigns and broadcast messages.

Handles campaign creation, scheduling, targeting, and delivery tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class CampanasModule:
    """Bulk messaging and campaign operations."""

    def __init__(self, supabase_client: Any):
        """
        Initialize campaigns module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def crear_campana(
        self,
        client_id: str,
        titulo: str,
        mensaje: str,
        target_segment: str = "all",
        canal: str = "whatsapp",
        programada_para: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Create a bulk messaging campaign.

        Target segments: all, hot_leads, inactive, customers, custom

        Args:
            client_id: Client ID
            titulo: Campaign title
            mensaje: Message to send
            target_segment: Audience segment
            canal: Channel (whatsapp, email)
            programada_para: Schedule time (if None, now)

        Returns:
            Campaign creation confirmation
        """
        try:
            if not programada_para:
                programada_para = datetime.utcnow()

            campaign = {
                "id": str(uuid4()),
                "client_id": client_id,
                "title": titulo,
                "message": mensaje,
                "target_segment": target_segment,
                "channel": canal,
                "scheduled_for": programada_para.isoformat(),
                "status": "draft",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("campanas").insert(campaign).execute()

            logger.info(
                f"Campaign created: {titulo} (ID: {campaign['id']})",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "campaign_id": campaign["id"],
                "titulo": titulo,
                "target_segment": target_segment,
                "mensaje": "Campaña creada en borrador",
            }

        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return {"error": str(e)}

    async def establecer_recipients(
        self,
        client_id: str,
        campaign_id: str,
        user_ids: Optional[list[str]] = None,
        criterios: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Set target recipients for campaign.

        Can specify explicit user_ids or use criterios (criteria):
        - state: curioso, prospecto, caliente, cliente
        - score_min, score_max: Lead score range
        - last_interaction_days: Inactive for N days
        - tags: Custom tags array

        Args:
            client_id: Client ID
            campaign_id: Campaign ID
            user_ids: Explicit list of user IDs (optional)
            criterios: Filter criteria (optional)

        Returns:
            Recipients count and preview
        """
        try:
            if user_ids:
                recipients = user_ids
            else:
                # Build query based on criteria
                query = self.supabase.table("leads").select("user_id").eq(
                    "client_id", client_id
                )

                if criterios:
                    if "state" in criterios:
                        query = query.eq("state", criterios["state"])

                    if "score_min" in criterios:
                        query = query.gte("score", criterios["score_min"])

                    if "score_max" in criterios:
                        query = query.lte("score", criterios["score_max"])

                    if "last_interaction_days" in criterios:
                        cutoff_date = (
                            datetime.utcnow()
                            - timedelta(days=criterios["last_interaction_days"])
                        ).isoformat()
                        query = query.lt("last_interaction", cutoff_date)

                response = query.execute()
                recipients = [lead["user_id"] for lead in response.data or []]

            # Save recipients
            recipient_records = [
                {
                    "id": str(uuid4()),
                    "campaign_id": campaign_id,
                    "user_id": user_id,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                }
                for user_id in recipients
            ]

            self.supabase.table("campaign_recipients").insert(
                recipient_records
            ).execute()

            logger.info(
                f"Campaign {campaign_id}: {len(recipients)} recipients set",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "campaign_id": campaign_id,
                "recipients_count": len(recipients),
                "preview": recipients[:5],  # First 5
            }

        except Exception as e:
            logger.error(f"Error setting recipients: {e}")
            return {"error": str(e)}

    async def lanzar_campana(
        self,
        client_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Launch a campaign (change from draft to scheduled).

        Args:
            client_id: Client ID
            campaign_id: Campaign ID

        Returns:
            Launch confirmation
        """
        try:
            # Fetch campaign
            response = self.supabase.table("campanas").select("*").eq(
                "id", campaign_id
            ).eq("client_id", client_id).single().execute()

            campaign = response.data

            # Check recipients exist
            recipients_response = self.supabase.table(
                "campaign_recipients"
            ).select("id", count="exact").eq("campaign_id", campaign_id).execute()

            recipients_count = recipients_response.count or 0

            if recipients_count == 0:
                return {"error": "Campaign has no recipients"}

            # Update campaign status
            self.supabase.table("campanas").update(
                {
                    "status": "scheduled",
                    "recipients_count": recipients_count,
                    "launched_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", campaign_id).execute()

            logger.info(
                f"Campaign launched: {campaign['title']} ({recipients_count} recipients)",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "campaign_id": campaign_id,
                "status": "scheduled",
                "recipients_count": recipients_count,
                "mensaje": f"Campaña lanzada a {recipients_count} destinatarios",
            }

        except Exception as e:
            logger.error(f"Error launching campaign: {e}")
            return {"error": str(e)}

    async def ejecutar_campanas_programadas(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """
        Execute scheduled campaigns (internal cron job).

        Args:
            client_id: Client ID

        Returns:
            Execution summary
        """
        try:
            now = datetime.utcnow()

            # Fetch scheduled campaigns due now
            response = self.supabase.table("campanas").select("*").eq(
                "client_id", client_id
            ).eq("status", "scheduled").lte(
                "scheduled_for", now.isoformat()
            ).execute()

            campaigns = response.data or []

            executed = 0

            for campaign in campaigns:
                try:
                    # Fetch recipients
                    recipients_response = self.supabase.table(
                        "campaign_recipients"
                    ).select("*").eq("campaign_id", campaign["id"]).eq(
                        "status", "pending"
                    ).execute()

                    recipients = recipients_response.data or []

                    # Mark as sent (actual delivery via worker)
                    for recipient in recipients:
                        self.supabase.table("campaign_recipients").update(
                            {"status": "sent"}
                        ).eq("id", recipient["id"]).execute()

                    # Mark campaign as sent
                    self.supabase.table("campanas").update(
                        {
                            "status": "sent",
                            "sent_at": datetime.utcnow().isoformat(),
                        }
                    ).eq("id", campaign["id"]).execute()

                    executed += 1

                except Exception as e:
                    logger.error(f"Error executing campaign {campaign['id']}: {e}")

            logger.info(
                f"Executed {executed} campaigns",
                extra={"client_id": client_id},
            )

            return {"executed": executed}

        except Exception as e:
            logger.error(f"Error executing campaigns: {e}")
            return {"error": str(e)}

    async def get_campaign_stats(
        self,
        client_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Get campaign statistics.

        Args:
            client_id: Client ID
            campaign_id: Campaign ID

        Returns:
            Stats including sent, delivered, failed
        """
        try:
            # Fetch recipients stats
            response = self.supabase.table("campaign_recipients").select(
                "status", count="exact"
            ).eq("campaign_id", campaign_id).execute()

            recipients = response.data or []

            stats = {
                "pending": 0,
                "sent": 0,
                "delivered": 0,
                "failed": 0,
                "total": len(recipients),
            }

            for recipient in recipients:
                status = recipient.get("status", "pending")
                if status in stats:
                    stats[status] += 1

            return stats

        except Exception as e:
            logger.error(f"Error fetching campaign stats: {e}")
            return {"error": str(e)}

    async def get_campaigns(
        self,
        client_id: str,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get campaigns for a client.

        Args:
            client_id: Client ID
            status: Filter by status (draft, scheduled, sent, cancelled)
            limit: Max results

        Returns:
            List of campaigns
        """
        try:
            query = self.supabase.table("campanas").select("*").eq(
                "client_id", client_id
            )

            if status:
                query = query.eq("status", status)

            response = query.order("created_at", desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching campaigns: {e}")
            return []

    async def cancelar_campana(
        self,
        client_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Cancel a campaign.

        Args:
            client_id: Client ID
            campaign_id: Campaign ID

        Returns:
            Cancellation confirmation
        """
        try:
            self.supabase.table("campanas").update(
                {"status": "cancelled", "cancelled_at": datetime.utcnow().isoformat()}
            ).eq("id", campaign_id).eq("client_id", client_id).execute()

            logger.info(
                f"Campaign cancelled: {campaign_id}",
                extra={"client_id": client_id},
            )

            return {"success": True, "campaign_id": campaign_id}

        except Exception as e:
            logger.error(f"Error cancelling campaign: {e}")
            return {"error": str(e)}
