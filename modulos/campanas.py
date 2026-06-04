"""
Campaigns module: bulk messaging campaigns and broadcast messages.

Handles campaign creation, scheduling, targeting, and delivery tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Seconds between each WhatsApp message to avoid Meta rate limiting
_SEND_DELAY_SECONDS = 1.2


class CampanasModule:
    """Bulk messaging and campaign operations."""

    def __init__(self, supabase_client: Any):
        self.supabase = supabase_client

    async def crear_campana(
        self,
        client_id: str,
        titulo: str,
        mensaje: str,
        target_segment: str = "all",
        canal: str = "whatsapp",
        programada_para: Optional[datetime] = None,
        template_name: Optional[str] = None,
        template_variables: Optional[list[str]] = None,
        template_language: str = "es",
    ) -> dict[str, Any]:
        """
        Create a bulk messaging campaign.

        Target segments: all, hot_leads, inactive, customers
        template_name: Meta-approved template name (required for outbound outside 24h window)
        template_variables: values for {{1}}, {{2}}, ... placeholders
        """
        try:
            if not programada_para:
                programada_para = datetime.utcnow()

            campaign = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "title": titulo,
                "message": mensaje,
                "target_segment": target_segment,
                "channel": canal,
                "scheduled_for": programada_para.isoformat(),
                "status": "draft",
                "template_name": template_name,
                "template_variables": template_variables or [],
                "template_language": template_language,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("campanas").insert(campaign).execute()

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

    async def _get_phone_number_id(self, client_id: str) -> Optional[str]:
        """Get the WhatsApp phone_number_id for a client."""
        try:
            response = (
                self.supabase.table("canales_config")
                .select("phone_number_id")
                .eq("cliente_id", client_id)
                .eq("canal", "whatsapp")
                .limit(1)
                .execute()
            )
            records = response.data or []
            if records:
                return records[0].get("phone_number_id")
        except Exception as e:
            logger.error(f"Error fetching phone_number_id for client {client_id}: {e}")
        return None

    async def _get_recipients_with_phones(
        self, client_id: str, target_segment: str
    ) -> list[dict[str, str]]:
        """
        Fetch recipients (user_id + phone) for a given segment.

        Returns list of {"user_id": ..., "phone": ...}
        """
        try:
            base_query = (
                self.supabase.table("conversaciones")
                .select("user_id, usuario_telefono")
                .eq("cliente_id", client_id)
                .eq("canal", "whatsapp")
                .neq("usuario_telefono", "")
                .not_.is_("usuario_telefono", "null")
            )

            if target_segment in ("hot_leads", "customers"):
                state_value = "caliente" if target_segment == "hot_leads" else "cliente"
                leads_resp = (
                    self.supabase.table("leads")
                    .select("user_id")
                    .eq("cliente_id", client_id)
                    .eq("state", state_value)
                    .execute()
                )
                user_ids = [r["user_id"] for r in (leads_resp.data or [])]
                if not user_ids:
                    return []
                base_query = base_query.in_("user_id", user_ids)

            elif target_segment == "inactive":
                cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
                base_query = base_query.lt("updated_at", cutoff)

            response = base_query.execute()
            rows = response.data or []

            seen: set[str] = set()
            recipients: list[dict[str, str]] = []
            for row in rows:
                phone = row.get("usuario_telefono", "").strip()
                uid = row.get("user_id", "")
                if phone and uid and uid not in seen:
                    seen.add(uid)
                    recipients.append({"user_id": uid, "phone": phone})

            return recipients

        except Exception as e:
            logger.error(f"Error fetching recipients for client {client_id}: {e}")
            return []

    async def ejecutar_campanas_programadas(
        self,
        whatsapp_handler: Any,
    ) -> dict[str, Any]:
        """
        Execute all scheduled campaigns whose scheduled_for <= now.

        Called by APScheduler every 5 minutes. Sends real WhatsApp messages.
        """
        now = datetime.utcnow()

        try:
            response = (
                self.supabase.table("campanas")
                .select("*")
                .eq("status", "scheduled")
                .lte("scheduled_for", now.isoformat())
                .execute()
            )
            campaigns = response.data or []
        except Exception as e:
            logger.error(f"Error fetching scheduled campaigns: {e}")
            return {"error": str(e)}

        executed = 0
        total_sent = 0
        total_failed = 0

        for campaign in campaigns:
            campaign_id = campaign["id"]
            client_id = campaign["cliente_id"]
            message = campaign.get("message", "")
            target_segment = campaign.get("target_segment", "all")

            try:
                phone_number_id = await self._get_phone_number_id(client_id)
                if not phone_number_id:
                    logger.error(f"No phone_number_id for client {client_id}, skipping campaign {campaign_id}")
                    continue

                recipients = await self._get_recipients_with_phones(client_id, target_segment)

                if not recipients:
                    logger.warning(f"Campaign {campaign_id}: no recipients found for segment '{target_segment}'")
                    self.supabase.table("campanas").update({
                        "status": "sent",
                        "sent_at": datetime.utcnow().isoformat(),
                        "recipients_count": 0,
                        "updated_at": datetime.utcnow().isoformat(),
                    }).eq("id", campaign_id).execute()
                    executed += 1
                    continue

                # Persist recipient records before sending
                recipient_records = [
                    {
                        "id": str(uuid4()),
                        "campaign_id": campaign_id,
                        "user_id": r["user_id"],
                        "status": "pending",
                        "created_at": datetime.utcnow().isoformat(),
                    }
                    for r in recipients
                ]
                self.supabase.table("campaign_recipients").insert(recipient_records).execute()

                sent = 0
                failed = 0

                for i, recipient in enumerate(recipients):
                    phone = recipient["phone"]
                    user_id = recipient["user_id"]
                    record_id = recipient_records[i]["id"]

                    try:
                        template_name = campaign.get("template_name")
                        if template_name:
                            success = await whatsapp_handler.send_template_message(
                                phone_number_id=phone_number_id,
                                recipient_phone=phone,
                                template_name=template_name,
                                template_variables=campaign.get("template_variables") or [],
                                client_id=client_id,
                                language_code=campaign.get("template_language", "es"),
                            )
                        else:
                            success = await whatsapp_handler.send_message(
                                phone_number_id=phone_number_id,
                                recipient_phone=phone,
                                text=message,
                                client_id=client_id,
                            )
                        new_status = "sent" if success else "failed"
                        if success:
                            sent += 1
                        else:
                            failed += 1
                    except Exception as send_err:
                        logger.error(f"Campaign {campaign_id}: error sending to {phone}: {send_err}")
                        new_status = "failed"
                        failed += 1

                    self.supabase.table("campaign_recipients").update(
                        {"status": new_status}
                    ).eq("id", record_id).execute()

                    # Rate limiting: pause between sends
                    if i < len(recipients) - 1:
                        await asyncio.sleep(_SEND_DELAY_SECONDS)

                # Mark campaign as sent
                self.supabase.table("campanas").update({
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                    "recipients_count": len(recipients),
                    "updated_at": datetime.utcnow().isoformat(),
                }).eq("id", campaign_id).execute()

                print(f"[CAMPANAS] Campaign {campaign_id} sent: {sent} ok, {failed} failed")
                executed += 1
                total_sent += sent
                total_failed += failed

            except Exception as e:
                logger.error(f"Error executing campaign {campaign_id}: {e}")

        return {"executed": executed, "sent": total_sent, "failed": total_failed}

    async def lanzar_campana(
        self,
        client_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Launch a campaign (draft → scheduled)."""
        try:
            response = (
                self.supabase.table("campanas")
                .select("*")
                .eq("id", campaign_id)
                .eq("cliente_id", client_id)
                .single()
                .execute()
            )
            campaign = response.data

            # Estimate recipients count for UI display
            recipients = await self._get_recipients_with_phones(client_id, campaign.get("target_segment", "all"))

            self.supabase.table("campanas").update({
                "status": "scheduled",
                "recipients_count": len(recipients),
                "launched_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", campaign_id).execute()

            return {
                "success": True,
                "campaign_id": campaign_id,
                "status": "scheduled",
                "recipients_count": len(recipients),
                "mensaje": f"Campaña programada para {len(recipients)} destinatarios",
            }

        except Exception as e:
            logger.error(f"Error launching campaign: {e}")
            return {"error": str(e)}

    async def cancelar_campana(
        self,
        client_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Cancel a campaign."""
        try:
            self.supabase.table("campanas").update({
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", campaign_id).eq("cliente_id", client_id).execute()

            return {"success": True, "campaign_id": campaign_id}

        except Exception as e:
            logger.error(f"Error cancelling campaign: {e}")
            return {"error": str(e)}

    async def get_campaigns(
        self,
        client_id: str,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get campaigns for a client."""
        try:
            query = (
                self.supabase.table("campanas")
                .select("*")
                .eq("cliente_id", client_id)
            )
            if status:
                query = query.eq("status", status)

            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching campaigns: {e}")
            return []

    async def get_campaign_stats(
        self,
        client_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Get campaign statistics."""
        try:
            response = (
                self.supabase.table("campaign_recipients")
                .select("status")
                .eq("campaign_id", campaign_id)
                .execute()
            )
            recipients = response.data or []

            stats: dict[str, int] = {"pending": 0, "sent": 0, "failed": 0, "total": len(recipients)}
            for r in recipients:
                s = r.get("status", "pending")
                if s in stats:
                    stats[s] += 1

            return stats

        except Exception as e:
            logger.error(f"Error fetching campaign stats: {e}")
            return {"error": str(e)}
