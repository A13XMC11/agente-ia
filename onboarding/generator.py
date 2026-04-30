"""
Generator: Automatically generates client configuration and templates.

Takes wizard data and produces finalized agent setup, notifies admin for review.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ConfigGenerator:
    """Generates complete client configuration from onboarding data."""

    def __init__(self, supabase_client: Any, sendgrid_api_key: str):
        """
        Initialize config generator.

        Args:
            supabase_client: Supabase client
            sendgrid_api_key: SendGrid API key for notifications
        """
        self.supabase = supabase_client
        self.sendgrid_api_key = sendgrid_api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def generate_complete_config(
        self,
        client_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Generate complete client configuration.

        Args:
            client_id: Client ID

        Returns:
            Complete config dict or None
        """
        try:
            # Get client
            client_response = self.supabase.table("clients").select(
                "*"
            ).eq("id", client_id).single().execute()

            if not client_response.data:
                logger.error(f"Client not found: {client_id}")
                return None

            client = client_response.data

            # Get onboarding session
            session_response = self.supabase.table("onboarding_sessions").select(
                "*"
            ).eq("client_id", client_id).single().execute()

            session = session_response.data or {}
            wizard_data = session.get("data", {})

            # Generate system prompt
            system_prompt = await self._generate_enhanced_prompt(client, wizard_data)

            # Generate templates
            templates = await self._generate_templates(wizard_data)

            # Generate routing rules
            routing_rules = await self._generate_routing_rules(wizard_data)

            # Build complete config
            config = {
                "client_id": client_id,
                "name": client.get("name", ""),
                "system_prompt": system_prompt,
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "response_delay_ms": 1000,
                },
                "modules": await self._generate_module_config(wizard_data),
                "channels": {
                    "whatsapp": {
                        "enabled": True,
                        "phone_number_id": "",  # Will be set after Meta auth
                    },
                    "instagram": {"enabled": False},
                    "facebook": {"enabled": False},
                    "email": {"enabled": False},
                },
                "business_hours": {
                    "start": "08:00",
                    "end": "18:00",
                    "timezone": wizard_data.get("timezone", "America/Guayaquil"),
                },
                "templates": templates,
                "routing_rules": routing_rules,
                "generated_at": datetime.utcnow().isoformat(),
            }

            # Save config to Supabase
            self.supabase.table("client_config_full").insert({
                "client_id": client_id,
                "config": config,
                "status": "pending_review",
                "created_at": datetime.utcnow().isoformat(),
            }).execute()

            logger.info(f"Complete config generated for {client_id}")

            # Notify admin
            await self._notify_admin_for_review(client, config)

            return config

        except Exception as e:
            logger.error(f"Error generating config: {e}")
            return None

    async def _generate_enhanced_prompt(
        self,
        client: dict[str, Any],
        wizard_data: dict[str, Any],
    ) -> str:
        """
        Generate sophisticated system prompt.

        Args:
            client: Client data
            wizard_data: Wizard data

        Returns:
            System prompt
        """
        business_name = client.get("name", "")
        industry = wizard_data.get("industry", "")
        services = wizard_data.get("services", "")

        prompt = f"""Tu nombre es asistente de {business_name}.

CONTEXTO DEL NEGOCIO:
- Empresa: {business_name}
- Industria: {industry}
- Servicios: {services}

TONO Y ESTILO:
- Sé amigable, profesional y entusiasta
- Usa emojis ocasionalmente pero con moderación
- Mantén respuestas concisas y claras
- Simula escritura natural con pequeños delays

RESPONSABILIDADES PRINCIPALES:
1. Saludar y establecer rapport con clientes
2. Responder preguntas sobre servicios y productos
3. Calificar leads según interés y urgencia
4. Facilitar cotizaciones y presupuestos
5. Agendar citas y consultas
6. Detectar objeciones y manejarlas profesionalmente
7. Escalar conversaciones complejas a asesores humanos

FLUJO DE CONVERSACIÓN:
1. Saludo personalizado
2. Identificación de necesidad (¿Qué te trae hoy?)
3. Exploración (¿Cuál es tu situación actual?)
4. Propuesta (Esto es lo que ofrecemos)
5. Manejo de objeciones (Entiendo tu preocupación)
6. Cierre (¿Agendamos una llamada?)
7. Seguimiento si es necesario

REGLAS IMPORTANTES:
- NUNCA prijas, sé respetuoso
- NUNCA hagas promesas que no pueda cumplir
- SIEMPRE sé honesto si no sé algo
- SIEMPRE ofrece hablar con un asesor si es necesario
- NO inventes información del negocio

CUANDO ESCALAR:
- Cliente solicita hablar con alguien
- Pregunta fuera de mi conocimiento
- Solicitud especial o custom
- Cliente molesto o frustrado

Recuerda: tu objetivo es que el cliente se sienta bien atendido y listo para la próxima etapa."""

        return prompt

    async def _generate_templates(
        self,
        wizard_data: dict[str, Any],
    ) -> dict[str, list[str]]:
        """
        Generate message templates.

        Args:
            wizard_data: Wizard data

        Returns:
            Templates by category
        """
        return {
            "greetings": [
                "¡Hola! ¿Cómo estás? 👋",
                "¡Bienvenido! ¿En qué puedo ayudarte?",
                "¡Hola! Gracias por escribir. ¿Cuál es tu pregunta?",
            ],
            "followup_24h": [
                "Hola de nuevo! ¿Pudiste revisar lo que te envié?",
                "Seguía pensando en tu proyecto. ¿Tienes un momento para hablar?",
                "¡Hey! Quería ver si surgió algo de tu interés.",
            ],
            "send_quote": [
                "He preparado una cotización personalizada para ti. ¿La reviso contigo ahora?",
                "Basado en tus necesidades, esto es lo que te propongo:",
                "Te tengo un presupuesto. ¿Le echamos un vistazo?",
            ],
            "objection_price": [
                "Entiendo que el precio es importante. Pero considera que estás invirtiendo en [beneficio]. ¿Podemos hablar de opciones?",
                "Es una inversión. ¿Cuál es tu presupuesto máximo? Quizás tengamos un plan que funcione.",
                "Tenemos opciones de pago. ¿Cuál se ajusta mejor a ti?",
            ],
            "objection_time": [
                "Totalmente, la agenda está ocupada. ¿Cuándo sí tienes disponible?",
                "No hay problema. ¿Qué día funciona mejor para ti?",
                "Perfectamente, entiendo. Agendamos cuando sea.",
            ],
            "appointment_confirm": [
                "Perfecto. Tu cita está agendada para {date} a las {time}. Te envío un recordatorio.",
                "Listo, anotado para {date} a las {time}. ¿Algo más que necesites?",
            ],
            "escalation": [
                "Esto necesita un toque personal. Te voy a conectar con mi equipo especializado.",
                "Para esto es mejor que hables con nuestro especialista. Un momento...",
                "Esta es una pregunta excelente. Deja que nuestro experto te dé la mejor respuesta.",
            ],
        }

    async def _generate_routing_rules(
        self,
        wizard_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate routing rules for lead escalation.

        Args:
            wizard_data: Wizard data

        Returns:
            List of routing rules
        """
        return [
            {
                "trigger": "objection_count >= 2",
                "action": "escalate_to_human",
                "priority": "medium",
            },
            {
                "trigger": "lead_score >= 8",
                "action": "notify_admin",
                "priority": "high",
            },
            {
                "trigger": "explicit_request_human",
                "action": "escalate_to_human",
                "priority": "critical",
            },
            {
                "trigger": "conversation_length >= 10",
                "action": "offer_escalation",
                "priority": "medium",
            },
            {
                "trigger": "sentiment_negative",
                "action": "escalate_to_human",
                "priority": "high",
            },
        ]

    async def _generate_module_config(
        self,
        wizard_data: dict[str, Any],
    ) -> dict[str, bool]:
        """
        Generate module configuration.

        Args:
            wizard_data: Wizard data

        Returns:
            Module config dict
        """
        modules_text = wizard_data.get("modules", "")

        # Default modules
        config = {
            "ventas": True,
            "agendamiento": True,
            "cobros": False,
            "calificacion": True,
            "alertas": True,
            "seguimiento": True,
            "links_pago": False,
            "campanas": False,
            "analytics": True,
        }

        # Enable based on modules text
        modules_lower = modules_text.lower()

        if "cobro" in modules_lower or "pago" in modules_lower:
            config["cobros"] = True

        if "link" in modules_lower:
            config["links_pago"] = True

        if "campana" in modules_lower or "campaign" in modules_lower:
            config["campanas"] = True

        return config

    async def _notify_admin_for_review(
        self,
        client: dict[str, Any],
        config: dict[str, Any],
    ) -> bool:
        """
        Notify admin to review new client config.

        Args:
            client: Client data
            config: Generated config

        Returns:
            True if notification sent
        """
        try:
            admin_email = "admin@agente-ia.com"

            subject = f"Nueva configuración pendiente de revisión: {client.get('name')}"

            body = f"""
Hola,

Hay una nueva cliente que requiere revisión:

Nombre: {client.get('name')}
Email: {client.get('email')}
Teléfono: {client.get('phone')}
Industria: {client.get('industry')}
Cliente ID: {client.get('id')}

La configuración está en estado "pending_review" en la base de datos.

Módulos habilitados:
{json.dumps(config.get('modules'), indent=2, ensure_ascii=False)}

Por favor revisa y aprueba o rechaza la configuración.

Saludos,
Agente IA
"""

            # Send via SendGrid
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": admin_email}],
                        "subject": subject,
                    }
                ],
                "from": {
                    "email": "noreply@agente-ia.com",
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": body,
                    }
                ],
            }

            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json",
            }

            response = await self.http_client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
            )

            if response.status_code in (200, 201, 202):
                logger.info(f"Admin notified about {client.get('id')}")
                return True
            else:
                logger.error(f"Failed to notify admin: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
            return False

    async def approve_config(self, client_id: str) -> bool:
        """
        Approve and activate client config.

        Args:
            client_id: Client ID

        Returns:
            True if approved
        """
        try:
            # Update client status
            self.supabase.table("clients").update({
                "status": "active",
            }).eq("id", client_id).execute()

            # Update config status
            self.supabase.table("client_config_full").update({
                "status": "approved",
            }).eq("client_id", client_id).execute()

            logger.info(f"Config approved for {client_id}")

            return True

        except Exception as e:
            logger.error(f"Error approving config: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()
