"""
Lead qualification module: automatic lead scoring and categorization.

Handles lead profiling, score calculation, and state transitions
based on interaction patterns and behavior. Includes signal-based
automatic scoring engine (0-10 scale with 5 states: CURIOSO, PROSPECTO,
INTERESADO, CALIENTE, URGENTE).
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import os

logger = logging.getLogger(__name__)

# Scoring signals (immutable keyword tuples with point values)
URGENCY_KEYWORDS = (
    "urgente",
    "ya",
    "hoy",
    "esta semana",
    "lo necesito pronto",
    "inmediatamente",
)
BUDGET_KEYWORDS = (
    "cuanto cuesta",
    "precio",
    "presupuesto",
    "puedo pagar",
    "tengo presupuesto",
    "costo",
)
DECISION_POWER_KEYWORDS = (
    "yo decido",
    "soy dueño",
    "soy gerente",
    "mi empresa",
    "nosotros necesitamos",
    "soy el responsable",
)
DEMO_KEYWORDS = ("demo", "demostracion", "cita", "reunion", "quiero ver", "mostrarme")
CURIOSITY_KEYWORDS = (
    "solo preguntando",
    "solo viendo",
    "por curiosidad",
    "no tengo presupuesto",
)


@dataclass(frozen=True)
class ScoreSignal:
    """Immutable representation of a detected scoring signal."""

    name: str
    delta: int
    matched_keywords: tuple[str, ...]
    excerpt: str


@dataclass(frozen=True)
class ScoringResult:
    """Immutable result of message scoring."""

    score: int
    state: str
    signals: tuple[ScoreSignal, ...]
    breakdown: dict[str, int]


class LeadScoringEngine:
    """Pure, deterministic signal-based lead scoring engine."""

    def __init__(
        self,
        quick_response_threshold_sec: int = 120,
        min_question_count: int = 2,
    ):
        self.quick_response_threshold = quick_response_threshold_sec
        self.min_question_count = min_question_count

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text: lowercase + strip accents (NFKD)."""
        if not text:
            return ""
        nfkd = unicodedata.normalize("NFKD", text.lower())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    @staticmethod
    def _match_keywords(normalized: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
        """Match whole-word keywords (case-insensitive, accent-insensitive)."""
        matched = []
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, normalized):
                matched.append(keyword)
        return tuple(matched)

    @staticmethod
    def _count_questions(text: str) -> int:
        """Count interrogative sentences: '?' + interrogative word starts."""
        if not text:
            return 0
        count = text.count("?")
        interrogatives = (
            "que",
            "como",
            "cuanto",
            "cuando",
            "donde",
            "por que",
            "cual",
            "cuale",
        )
        normalized = LeadScoringEngine._normalize(text)
        for interrog in interrogatives:
            pattern = r"(?:^|\b)" + re.escape(interrog) + r"\b"
            count += len(re.findall(pattern, normalized))
        return count

    @staticmethod
    def _is_quick_response(
        prior_messages: tuple[dict, ...], current_ts: datetime
    ) -> bool:
        """Check if response time < threshold (last prior message to current)."""
        if not prior_messages:
            return False
        last_prior = prior_messages[-1]
        prior_ts_str = last_prior.get("timestamp")
        if not prior_ts_str:
            return False
        try:
            prior_ts = (
                datetime.fromisoformat(prior_ts_str)
                if isinstance(prior_ts_str, str)
                else prior_ts_str
            )
            delta_sec = (current_ts - prior_ts).total_seconds()
            return 0 < delta_sec < 120
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_short_repeated(current_text: str, prior_messages: tuple[dict, ...]) -> bool:
        """Check if current message is short (<3 words) and matches a prior one."""
        if not current_text or len(current_text.split()) >= 3:
            return False
        normalized_current = LeadScoringEngine._normalize(current_text)
        for prior in prior_messages:
            prior_text = prior.get("content", "")
            normalized_prior = LeadScoringEngine._normalize(prior_text)
            if normalized_prior and normalized_current == normalized_prior:
                return True
        return False

    def score_message(
        self,
        current_message: str,
        prior_messages: tuple[dict, ...] = (),
        current_ts: Optional[datetime] = None,
    ) -> ScoringResult:
        """
        Score a message based on signal detection.

        Args:
            current_message: The user message to score
            prior_messages: List of prior messages (with 'content' and 'timestamp' keys)
            current_ts: Current timestamp (defaults to now)

        Returns:
            ScoringResult with score (0-10), state, signals, and breakdown
        """
        if current_ts is None:
            current_ts = datetime.utcnow()

        normalized = self._normalize(current_message)
        signals = []
        breakdown = {}
        raw_score = 0

        # +3 points: Urgency
        if self._match_keywords(normalized, URGENCY_KEYWORDS):
            matched = self._match_keywords(normalized, URGENCY_KEYWORDS)
            signals.append(
                ScoreSignal(
                    name="urgency",
                    delta=3,
                    matched_keywords=matched,
                    excerpt=current_message[:200],
                )
            )
            breakdown["urgency"] = 3
            raw_score += 3

        # +3 points: Budget mention
        if self._match_keywords(normalized, BUDGET_KEYWORDS):
            matched = self._match_keywords(normalized, BUDGET_KEYWORDS)
            signals.append(
                ScoreSignal(
                    name="budget",
                    delta=3,
                    matched_keywords=matched,
                    excerpt=current_message[:200],
                )
            )
            breakdown["budget"] = 3
            raw_score += 3

        # +3 points: Decision power
        if self._match_keywords(normalized, DECISION_POWER_KEYWORDS):
            matched = self._match_keywords(normalized, DECISION_POWER_KEYWORDS)
            signals.append(
                ScoreSignal(
                    name="decision_power",
                    delta=3,
                    matched_keywords=matched,
                    excerpt=current_message[:200],
                )
            )
            breakdown["decision_power"] = 3
            raw_score += 3

        # +2 points: Specific questions (>= min_question_count)
        question_count = self._count_questions(current_message)
        if question_count >= self.min_question_count:
            signals.append(
                ScoreSignal(
                    name="specific_questions",
                    delta=2,
                    matched_keywords=(f"{question_count}_questions",),
                    excerpt=current_message[:200],
                )
            )
            breakdown["specific_questions"] = 2
            raw_score += 2

        # +2 points: Demo/meeting request
        if self._match_keywords(normalized, DEMO_KEYWORDS):
            matched = self._match_keywords(normalized, DEMO_KEYWORDS)
            signals.append(
                ScoreSignal(
                    name="demo_request",
                    delta=2,
                    matched_keywords=matched,
                    excerpt=current_message[:200],
                )
            )
            breakdown["demo_request"] = 2
            raw_score += 2

        # +2 points: Quick response (<2 min)
        if self._is_quick_response(prior_messages, current_ts):
            signals.append(
                ScoreSignal(
                    name="quick_response",
                    delta=2,
                    matched_keywords=("response_time_< 2min",),
                    excerpt=current_message[:200],
                )
            )
            breakdown["quick_response"] = 2
            raw_score += 2

        # -2 points: Only curiosity
        if self._match_keywords(normalized, CURIOSITY_KEYWORDS):
            matched = self._match_keywords(normalized, CURIOSITY_KEYWORDS)
            signals.append(
                ScoreSignal(
                    name="curiosity_only",
                    delta=-2,
                    matched_keywords=matched,
                    excerpt=current_message[:200],
                )
            )
            breakdown["curiosity_only"] = -2
            raw_score -= 2

        # -1 point: Very short repeated messages
        if self._is_short_repeated(current_message, prior_messages):
            signals.append(
                ScoreSignal(
                    name="short_repeated",
                    delta=-1,
                    matched_keywords=("repeated_short_message",),
                    excerpt=current_message[:200],
                )
            )
            breakdown["short_repeated"] = -1
            raw_score -= 1

        # Clamp score to [0, 10]
        final_score = max(0, min(10, raw_score))

        # Map score to state
        state = self._state_for_score(final_score)

        return ScoringResult(
            score=final_score,
            state=state,
            signals=tuple(signals),
            breakdown=breakdown,
        )

    @staticmethod
    def _state_for_score(score: int) -> str:
        """Map score (0-10) to lead state."""
        if score >= 9:
            return "urgente"
        elif score >= 7:
            return "caliente"
        elif score >= 5:
            return "interesado"
        elif score >= 3:
            return "prospecto"
        else:
            return "curioso"


class CalificacionModule:
    """Lead scoring and qualification operations."""

    def __init__(self, supabase_client: Any, alertas_module: Any = None):
        """
        Initialize lead qualification module.

        Args:
            supabase_client: Supabase client instance
            alertas_module: AlertasModule instance for sending WhatsApp alerts (optional)
        """
        self.supabase = supabase_client
        self.alertas = alertas_module
        self.score_threshold_hot = float(
            os.environ.get("LEAD_SCORE_HOT_THRESHOLD", 8)
        )
        self.notification_enabled = (
            os.environ.get("LEAD_SCORE_NOTIFICATION_ENABLED", "true").lower() == "true"
        )
        self.scoring_engine = LeadScoringEngine()

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
            logger.info(f"Guardando lead para usuario_id={usuario_id}, nombre={nombre}", extra={"client_id": client_id})

            # Check if lead exists
            logger.info(f"Buscando lead existente: cliente_id={client_id}, usuario_id={usuario_id}")
            existing_response = self.supabase.table("leads").select("*").eq(
                "cliente_id", client_id
            ).eq("user_id", usuario_id).execute()

            lead_data = {
                "cliente_id": client_id,
                "user_id": usuario_id,
                "nombre": nombre,
                "email": email,
                "telefono": telefono,
                "company": empresa,
                "tags": tags or [],
                "updated_at": datetime.utcnow().isoformat(),
            }

            if existing_response.data:
                # Update existing lead
                lead_id = existing_response.data[0]["id"]
                logger.info(f"Lead encontrado: {lead_id}. Actualizando con datos: {lead_data}")
                result = self.supabase.table("leads").update(lead_data).eq(
                    "id", lead_id
                ).execute()
                logger.info(f"Lead actualizado exitosamente: {lead_id}")

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
                logger.info(f"Lead no existe. Creando nuevo lead...")
                new_lead = {
                    "id": str(uuid4()),
                    **lead_data,
                    "score": 0.0,
                    "estado": "curioso",
                    "urgency": 0.0,
                    "budget": None,
                    "decision_power": 0.0,
                    "interaction_count": 0,
                    "last_interaction": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                }
                logger.info(f"Insertando nuevo lead: {new_lead}")
                result = self.supabase.table("leads").insert(new_lead).execute()
                logger.info(f"Lead creado exitosamente: {new_lead['id']}")

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
            logger.error(f"Error saving lead: {e}", exc_info=True, extra={"client_id": client_id})
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
            logger.info(f"Actualizando score para usuario_id={usuario_id}, score={score}", extra={"client_id": client_id})

            if not (0 <= score <= 10):
                logger.warning(f"Score fuera de rango: {score}")
                return {"error": "Score must be between 0 and 10"}

            # Fetch lead
            logger.info(f"Buscando lead: cliente_id={client_id}, usuario_id={usuario_id}")
            lead_response = self.supabase.table("leads").select("*").eq(
                "cliente_id", client_id
            ).eq("user_id", usuario_id).single().execute()

            lead = lead_response.data
            logger.info(f"Lead encontrado: {lead.get('id')}, score actual: {lead.get('score')}")

            # Calculate new state based on score
            if score >= self.score_threshold_hot:
                new_state = "caliente"
            elif score >= 4:
                new_state = "prospecto"
            else:
                new_state = "curioso"

            old_state = lead.get("estado", "curioso")
            logger.info(f"Transición de estado: {old_state} -> {new_state}")

            # Update lead
            update_data = {
                "score": score,
                "estado": new_state,
                "score_reason": razon,
                "score_updated_at": datetime.utcnow().isoformat(),
                "interaction_count": lead.get("interaction_count", 0) + 1,
                "last_interaction": datetime.utcnow().isoformat(),
            }

            logger.info(f"Guardando score con datos: {update_data}")
            self.supabase.table("leads").update(update_data).eq(
                "id", lead["id"]
            ).execute()
            logger.info(f"Lead score guardado exitosamente: {lead['id']}")

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
                logger.info(f"Enviando notificación de lead caliente para {usuario_id}")
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
            logger.error(f"Error updating lead score: {e}", exc_info=True, extra={"client_id": client_id})
            return {"error": str(e)}

    async def _send_hot_lead_notification(
        self,
        client_id: str,
        lead: dict[str, Any],
        score: float,
    ) -> dict[str, Any]:
        """
        Send notification when lead becomes hot (score >= 8).

        Sends to:
        - Database notifications table
        - WhatsApp alert to owner (via AlertasModule if available)

        Args:
            client_id: Client ID
            lead: Lead data
            score: Lead score

        Returns:
            Notification status
        """
        try:
            lead_name = lead.get("nombre") or lead.get("name", "Lead sin nombre")
            logger.info(f"Enviando notificación de lead caliente: {lead_name} (score: {score})")

            notification = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "type": "hot_lead",
                "lead_id": lead["id"],
                "lead_name": lead_name,
                "score": score,
                "message": f"🔥 Lead Caliente: {lead_name} (Score: {score}/10)",
                "priority": "high",
                "created_at": datetime.utcnow().isoformat(),
                "read": False,
            }

            logger.info(f"Insertando notificación: {notification}")
            self.supabase.table("notifications").insert(notification).execute()
            logger.info(f"Notificación enviada: {notification['id']}")

            logger.info(
                f"Hot lead notification sent for {lead_name} (score: {score})",
                extra={"client_id": client_id},
            )

            # Send WhatsApp alert to owner
            alert_result = None
            if self.alertas:
                try:
                    mensaje = (
                        f"Lead muy caliente detectado:\n\n"
                        f"👤 Nombre: {lead_name}\n"
                        f"📊 Score: {score}/10\n"
                        f"📞 Teléfono: {lead.get('telefono') or lead.get('phone', 'N/A')}\n"
                        f"📧 Email: {lead.get('email', 'N/A')}\n"
                        f"🏢 Empresa: {lead.get('company', 'N/A')}"
                    )
                    logger.info(f"Enviando alerta WhatsApp: {mensaje[:100]}...")
                    alert_result = await self.alertas.enviar_alerta_importante(
                        client_id=client_id,
                        tipo="hot_lead",
                        mensaje=mensaje,
                        usuario_id=lead.get("user_id"),
                        datos_extras={"score": score, "lead_id": lead["id"]},
                    )
                    logger.info(f"Alerta WhatsApp enviada: {alert_result}")
                except Exception as alert_err:
                    logger.warning(f"Error sending hot lead WhatsApp alert: {alert_err}")

            return {
                "sent": True,
                "notification_id": notification["id"],
                "whatsapp_alert": alert_result,
            }

        except Exception as e:
            logger.error(f"Error sending notification: {e}", exc_info=True, extra={"client_id": client_id})
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
                "cliente_id", client_id
            ).eq("user_id", usuario_id).single().execute()

            lead = lead_response.data

            # Fetch conversation metrics
            conversation_response = self.supabase.table("conversaciones").select(
                "id"
            ).eq("cliente_id", client_id).eq("user_id", usuario_id).execute()

            num_conversations = len(conversation_response.data or [])

            # Fetch message count
            messages_response = self.supabase.table("mensajes").select(
                "id", count="exact"
            ).eq("cliente_id", client_id).eq("user_id", usuario_id).execute()

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
                "cliente_id", client_id
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
                "cliente_id", client_id
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
            ).eq("cliente_id", client_id).execute()

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

    async def calcular_score_automatico(
        self,
        client_id: str,
        usuario_id: str,
        current_message: str,
        prior_messages: list[dict[str, Any]] | None = None,
        current_ts: datetime | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Automatically score a lead based on signal detection.

        Runs the scoring engine on the current message, updates the lead score
        if it improves, and persists a history row for auditability.

        Args:
            client_id: Client ID
            usuario_id: User ID (lead identifier)
            current_message: Current user message to analyze
            prior_messages: List of prior messages with 'content' and 'timestamp' keys
            current_ts: Current timestamp (defaults to now)
            conversation_id: Conversation ID for linking

        Returns:
            {success: bool, new_score: float, new_state: str, signals: list[dict], delta: float}
            or {error: str} on failure (never raises)
        """
        try:
            logger.info(f"Calculando score para usuario_id={usuario_id}", extra={"client_id": client_id})

            if current_ts is None:
                current_ts = datetime.utcnow()

            # Convert prior_messages to tuple for engine
            prior_tuple = tuple(prior_messages or [])

            # Run deterministic scoring engine
            logger.info(f"Ejecutando scoring engine con mensaje: {current_message[:100]}")
            result = self.scoring_engine.score_message(
                current_message=current_message,
                prior_messages=prior_tuple,
                current_ts=current_ts,
            )
            logger.info(f"Score calculado: {result.score}, estado: {result.state}, señales: {[s.name for s in result.signals]}")

            # Fetch existing lead
            lead = None
            try:
                logger.info(f"Buscando lead existente: cliente_id={client_id}, usuario_id={usuario_id}")
                lead_response = (
                    self.supabase.table("leads")
                    .select("*")
                    .eq("cliente_id", client_id)
                    .eq("user_id", usuario_id)
                    .single()
                    .execute()
                )
                lead = lead_response.data
                logger.info(f"Lead encontrado: {lead.get('id')}, score actual: {lead.get('score')}")
            except Exception as e:
                logger.warning(f"Lead no existe para usuario_id={usuario_id}: {e}. Creando nuevo...")
                # Lead doesn't exist yet — create it with a zero score
                lead = {
                    "id": str(uuid4()),
                    "cliente_id": client_id,
                    "user_id": usuario_id,
                    "score": 0,
                    "estado": "curioso",
                    "interaction_count": 0,
                }
                logger.info(f"Nuevo lead preparado: {lead['id']}")

            # Blended score: keep lead hot once it reaches hot threshold
            old_score = lead.get("score", 0)
            new_score = max(old_score, result.score)
            delta = new_score - old_score
            new_state = LeadScoringEngine._state_for_score(new_score)
            old_state = lead.get("estado", "curioso")

            logger.info(f"Score blended: {old_score} -> {new_score} (delta: {delta}), estado: {old_state} -> {new_state}")

            # Build history row
            history_row = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "lead_id": lead.get("id"),
                "user_id": usuario_id,
                "score_before": old_score,
                "score_after": new_score,
                "delta": delta,
                "signal_type": ",".join(sig.name for sig in result.signals)
                if result.signals
                else "no_signal",
                "signal_keywords": [
                    kw for sig in result.signals for kw in sig.matched_keywords
                ],
                "message_excerpt": current_message[:500],
                "created_at": current_ts.isoformat(),
            }

            # Insert history (always, for audit trail)
            logger.info(f"Guardando history row: {history_row}")
            self.supabase.table("lead_score_history").insert(history_row).execute()
            logger.info(f"History row guardada: {history_row['id']}")

            # Update lead score only if it changed
            if delta > 0:
                logger.info(f"Score cambió (delta={delta}), actualizando lead...")
                update_data = {
                    "score": new_score,
                    "estado": new_state,
                    "score_reason": f"Signal: {history_row['signal_type']}",
                    "score_updated_at": current_ts.isoformat(),
                    "interaction_count": lead.get("interaction_count", 0) + 1,
                    "last_interaction": current_ts.isoformat(),
                }

                if not lead.get("id"):
                    # Create lead if it doesn't exist
                    logger.info("Lead ID no existe, creando nuevo lead en Supabase...")
                    lead["id"] = str(uuid4())
                    new_lead = {
                        "id": lead["id"],
                        "cliente_id": client_id,
                        "user_id": usuario_id,
                        "nombre": "",
                        "telefono": "",
                        **update_data,
                        "created_at": current_ts.isoformat(),
                    }
                    logger.info(f"Insertando nuevo lead: {new_lead}")
                    self.supabase.table("leads").insert(new_lead).execute()
                    logger.info(f"Lead creado: {lead['id']}")
                else:
                    # Update existing lead
                    logger.info(f"Actualizando lead existente: {lead['id']} con datos: {update_data}")
                    self.supabase.table("leads").update(update_data).eq(
                        "id", lead["id"]
                    ).execute()
                    logger.info(f"Lead actualizado: {lead['id']}")

                # Trigger hot lead notification if state changed to caliente
                if new_state == "caliente" and old_state != "caliente":
                    logger.info(f"Lead pasó a estado CALIENTE, enviando notificación...")
                    await self._send_hot_lead_notification(
                        client_id, lead, new_score
                    )

                logger.info(
                    f"Lead score updated: {usuario_id} -> {new_score} ({new_state})",
                    extra={"client_id": client_id},
                )
            else:
                logger.info(f"Score no cambió (delta={delta}), no actualizando lead")

            result_dict = {
                "success": True,
                "new_score": new_score,
                "new_state": new_state,
                "old_score": old_score,
                "old_state": old_state,
                "delta": delta,
                "signals": [
                    {
                        "name": sig.name,
                        "delta": sig.delta,
                        "keywords": list(sig.matched_keywords),
                    }
                    for sig in result.signals
                ],
                "breakdown": result.breakdown,
            }

            return result_dict

        except Exception as e:
            logger.error(f"Error in calcular_score_automatico para usuario_id={usuario_id}: {e}", exc_info=True, extra={"client_id": client_id})
            return {"error": str(e)}
