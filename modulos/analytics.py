"""
Analytics module: metrics, reporting, and business intelligence.

Provides dashboards, KPIs, and historical trends for client performance.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalyticsModule:
    """Analytics and reporting operations."""

    def __init__(self, supabase_client: Any):
        """
        Initialize analytics module.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def get_dashboard_summary(
        self,
        client_id: str,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Get executive dashboard summary.

        Args:
            client_id: Client ID
            dias: Days to analyze (default 30)

        Returns:
            Dashboard KPIs and metrics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=dias)).isoformat()

            # Get message count
            messages_response = self.supabase.table("messages").select(
                "id", count="exact"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            message_count = messages_response.count or 0

            # Get unique users
            users_response = self.supabase.table("conversations").select(
                "user_id"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            unique_users = len(set(c["user_id"] for c in users_response.data or []))

            # Get lead stats
            leads_response = self.supabase.table("leads").select(
                "state, score"
            ).eq("client_id", client_id).gte("updated_at", cutoff_date).execute()

            leads = leads_response.data or []

            lead_states = defaultdict(int)
            hot_leads_count = 0

            for lead in leads:
                lead_states[lead.get("state", "curioso")] += 1
                if lead.get("score", 0) >= 8:
                    hot_leads_count += 1

            # Get sales quotes
            quotes_response = self.supabase.table("quotes").select(
                "total, status"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            quotes = quotes_response.data or []

            quotes_value = sum(q.get("total", 0) for q in quotes)
            quotes_accepted = sum(
                1 for q in quotes if q.get("status") == "accepted"
            )

            # Get payments
            payments_response = self.supabase.table("payments").select(
                "amount"
            ).eq("client_id", client_id).eq("status", "verified").gte(
                "created_at", cutoff_date
            ).execute()

            payments = payments_response.data or []
            payments_total = sum(p.get("amount", 0) for p in payments)

            # Get appointments
            appointments_response = self.supabase.table("appointments").select(
                "id"
            ).eq("client_id", client_id).eq("status", "scheduled").gte(
                "created_at", cutoff_date
            ).execute()

            appointments_count = len(appointments_response.data or [])

            return {
                "periodo_dias": dias,
                "fecha_analisis": datetime.utcnow().isoformat(),
                "mensajes": message_count,
                "usuarios_unicos": unique_users,
                "leads": {
                    "total": len(leads),
                    "curioso": lead_states.get("curioso", 0),
                    "prospecto": lead_states.get("prospecto", 0),
                    "caliente": hot_leads_count,
                    "cliente": lead_states.get("cliente", 0),
                },
                "ventas": {
                    "cotizaciones_total": len(quotes),
                    "cotizaciones_valor": round(quotes_value, 2),
                    "cotizaciones_aceptadas": quotes_accepted,
                    "conversion_rate": round(
                        quotes_accepted / len(quotes) * 100, 2
                    ) if quotes else 0,
                },
                "pagos": {
                    "transacciones": len(payments),
                    "monto_total": round(payments_total, 2),
                    "promedio": round(payments_total / len(payments), 2) if payments else 0,
                },
                "agendamiento": {
                    "citas_programadas": appointments_count,
                },
            }

        except Exception as e:
            logger.error(f"Error generating dashboard summary: {e}")
            return {"error": str(e)}

    async def get_sales_analytics(
        self,
        client_id: str,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Get detailed sales analytics.

        Args:
            client_id: Client ID
            dias: Days to analyze

        Returns:
            Sales metrics and trends
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=dias)).isoformat()

            # Quotes by status
            quotes_response = self.supabase.table("quotes").select(
                "status, total, created_at"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            quotes = quotes_response.data or []

            # Group by status
            by_status = defaultdict(lambda: {"count": 0, "value": 0})

            for quote in quotes:
                status = quote.get("status", "pending")
                by_status[status]["count"] += 1
                by_status[status]["value"] += quote.get("total", 0)

            # Group by day
            by_day = defaultdict(lambda: {"count": 0, "value": 0})

            for quote in quotes:
                day = quote["created_at"][:10]
                by_day[day]["count"] += 1
                by_day[day]["value"] += quote.get("total", 0)

            return {
                "por_estado": dict(by_status),
                "por_dia": dict(sorted(by_day.items())),
                "total_quotes": len(quotes),
                "valor_total": round(sum(q.get("total", 0) for q in quotes), 2),
                "promedio_quote": round(
                    sum(q.get("total", 0) for q in quotes) / len(quotes), 2
                ) if quotes else 0,
            }

        except Exception as e:
            logger.error(f"Error generating sales analytics: {e}")
            return {"error": str(e)}

    async def get_engagement_analytics(
        self,
        client_id: str,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Get user engagement metrics.

        Args:
            client_id: Client ID
            dias: Days to analyze

        Returns:
            Engagement metrics and trends
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=dias)).isoformat()

            # Messages by day
            messages_response = self.supabase.table("messages").select(
                "created_at, sender_type"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            messages = messages_response.data or []

            by_day = defaultdict(lambda: {"user": 0, "agent": 0})

            for msg in messages:
                day = msg["created_at"][:10]
                sender_type = msg.get("sender_type", "user")
                if sender_type == "user":
                    by_day[day]["user"] += 1
                else:
                    by_day[day]["agent"] += 1

            # Conversations
            conversations_response = self.supabase.table("conversations").select(
                "id, created_at"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            conversations = conversations_response.data or []

            # Average response time (estimated from message timestamps)
            avg_response_time = "N/A"  # Would need message timestamps to calculate

            return {
                "messages_total": len(messages),
                "conversations_total": len(conversations),
                "por_dia": dict(sorted(by_day.items())),
                "average_messages_per_conversation": round(
                    len(messages) / len(conversations), 2
                ) if conversations else 0,
                "average_response_time": avg_response_time,
            }

        except Exception as e:
            logger.error(f"Error generating engagement analytics: {e}")
            return {"error": str(e)}

    async def get_channel_analytics(
        self,
        client_id: str,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Get channel usage and performance.

        Args:
            client_id: Client ID
            dias: Days to analyze

        Returns:
            Channel metrics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(dias=dias)).isoformat()

            # Messages by channel
            messages_response = self.supabase.table("messages").select(
                "channel"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            messages = messages_response.data or []

            by_channel = defaultdict(int)

            for msg in messages:
                channel = msg.get("channel", "unknown")
                by_channel[channel] += 1

            return {
                "messages_por_canal": dict(by_channel),
                "total_messages": len(messages),
                "canales_activos": len(by_channel),
                "canal_principal": max(by_channel, key=by_channel.get)
                if by_channel else "N/A",
            }

        except Exception as e:
            logger.error(f"Error generating channel analytics: {e}")
            return {"error": str(e)}

    async def get_lead_funnel(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """
        Get lead funnel metrics.

        Shows progression: curioso → prospecto → caliente → cliente

        Args:
            client_id: Client ID

        Returns:
            Funnel metrics with conversion rates
        """
        try:
            leads_response = self.supabase.table("leads").select(
                "state, score"
            ).eq("client_id", client_id).execute()

            leads = leads_response.data or []

            funnel = {
                "curioso": 0,
                "prospecto": 0,
                "caliente": 0,
                "cliente": 0,
                "descartado": 0,
            }

            for lead in leads:
                state = lead.get("state", "curioso")
                if state in funnel:
                    funnel[state] += 1

            total = sum(funnel.values())

            return {
                "funnel": funnel,
                "total_leads": total,
                "conversion_curioso_to_prospecto": round(
                    (funnel["prospecto"] / funnel["curioso"] * 100)
                    if funnel["curioso"] > 0
                    else 0,
                    2,
                ),
                "conversion_prospecto_to_caliente": round(
                    (funnel["caliente"] / funnel["prospecto"] * 100)
                    if funnel["prospecto"] > 0
                    else 0,
                    2,
                ),
                "conversion_caliente_to_cliente": round(
                    (funnel["cliente"] / funnel["caliente"] * 100)
                    if funnel["caliente"] > 0
                    else 0,
                    2,
                ),
                "overall_conversion": round(
                    (funnel["cliente"] / total * 100) if total > 0 else 0,
                    2,
                ),
            }

        except Exception as e:
            logger.error(f"Error generating lead funnel: {e}")
            return {"error": str(e)}

    async def get_payment_analytics(
        self,
        client_id: str,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Get payment and revenue analytics.

        Args:
            client_id: Client ID
            dias: Days to analyze

        Returns:
            Payment metrics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(dias=dias)).isoformat()

            # Verified payments
            payments_response = self.supabase.table("payments").select(
                "amount, created_at, status"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            payments = payments_response.data or []

            by_status = defaultdict(lambda: {"count": 0, "amount": 0})

            for payment in payments:
                status = payment.get("status", "pending")
                by_status[status]["count"] += 1
                by_status[status]["amount"] += payment.get("amount", 0)

            verified_total = sum(
                p.get("amount", 0) for p in payments if p.get("status") == "verified"
            )

            return {
                "por_estado": dict(by_status),
                "total_payments": len(payments),
                "verified_amount": round(verified_total, 2),
                "failed_amount": round(
                    sum(
                        p.get("amount", 0)
                        for p in payments
                        if p.get("status") == "failed"
                    ),
                    2,
                ),
                "verification_rate": round(
                    (
                        sum(1 for p in payments if p.get("status") == "verified")
                        / len(payments)
                        * 100
                    )
                    if payments
                    else 0,
                    2,
                ),
            }

        except Exception as e:
            logger.error(f"Error generating payment analytics: {e}")
            return {"error": str(e)}

    async def get_token_usage(
        self,
        client_id: str,
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Get token consumption metrics.

        Args:
            client_id: Client ID
            dias: Days to analyze

        Returns:
            Token usage metrics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(dias=dias)).isoformat()

            # Token logs
            logs_response = self.supabase.table("token_logs").select(
                "tokens_used, created_at"
            ).eq("client_id", client_id).gte("created_at", cutoff_date).execute()

            logs = logs_response.data or []

            total_tokens = sum(log.get("tokens_used", 0) for log in logs)

            # Average per day
            days_with_activity = len(set(log["created_at"][:10] for log in logs))
            avg_per_day = round(total_tokens / days_with_activity, 0) if days_with_activity > 0 else 0

            return {
                "total_tokens": total_tokens,
                "promedio_por_dia": avg_per_day,
                "cost_usd": round(total_tokens * 0.00002, 2),  # Approximate cost
                "dias_analizados": dias,
                "dias_con_actividad": days_with_activity,
            }

        except Exception as e:
            logger.error(f"Error generating token usage: {e}")
            return {"error": str(e)}

    async def export_report(
        self,
        client_id: str,
        tipo: str = "summary",
        dias: int = 30,
    ) -> dict[str, Any]:
        """
        Generate comprehensive report.

        Types: summary, detailed, executive

        Args:
            client_id: Client ID
            tipo: Report type
            dias: Days to include

        Returns:
            Report data
        """
        try:
            report = {
                "client_id": client_id,
                "report_type": tipo,
                "periodo_dias": dias,
                "fecha_generacion": datetime.utcnow().isoformat(),
                "data": {},
            }

            if tipo in ("summary", "detailed", "executive"):
                report["data"]["dashboard"] = await self.get_dashboard_summary(
                    client_id, dias
                )

            if tipo in ("detailed", "executive"):
                report["data"]["sales"] = await self.get_sales_analytics(
                    client_id, dias
                )
                report["data"]["engagement"] = await self.get_engagement_analytics(
                    client_id, dias
                )
                report["data"]["channels"] = await self.get_channel_analytics(
                    client_id, dias
                )
                report["data"]["leads_funnel"] = await self.get_lead_funnel(client_id)
                report["data"]["payments"] = await self.get_payment_analytics(
                    client_id, dias
                )

            if tipo == "executive":
                report["data"]["tokens"] = await self.get_token_usage(client_id, dias)

            return {"success": True, "report": report}

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}
