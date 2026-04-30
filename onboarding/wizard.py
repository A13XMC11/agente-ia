"""
Onboarding wizard: Conversational agent that guides new clients through setup.

Runs on WhatsApp, collects business info, and generates agent configuration.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OnboardingWizard:
    """Guides new clients through setup via conversational messages."""

    STEPS = {
        "welcome": {
            "message": "¡Hola! 👋 Bienvenido a Agente IA. Soy tu asistente de configuración. Necesito recopilar información sobre tu negocio para personalizar tu agente. ¿Cuál es el nombre de tu empresa?",
            "next_step": "business_name",
            "extract_key": "business_name",
        },
        "business_name": {
            "message": "Perfecto, {business_name}. ¿Cuál es tu industria o rubro principal? (ej: Venta de ropa, servicios de consultoría, alquiler de propiedades)",
            "next_step": "industry",
            "extract_key": "industry",
        },
        "industry": {
            "message": "Entendido. ¿Cuáles son tus principales servicios o productos? (breve descripción)",
            "next_step": "services",
            "extract_key": "services",
        },
        "services": {
            "message": "¿Cuál es tu horario de atención? (ej: Lunes a viernes 9am-6pm)",
            "next_step": "business_hours",
            "extract_key": "business_hours",
        },
        "business_hours": {
            "message": "¿En qué zona horaria operas? (ej: America/Guayaquil, America/Bogota)",
            "next_step": "timezone",
            "extract_key": "timezone",
        },
        "timezone": {
            "message": "¿Tienes un número de WhatsApp propio para este agente? Necesitaremos autenticarlo con Meta.",
            "next_step": "whatsapp_number",
            "extract_key": "whatsapp_number",
        },
        "whatsapp_number": {
            "message": "Perfecto. Te enviaré instrucciones para conectar tu número con nuestro sistema. Mientras tanto, ¿cuál es tu correo para recibir las credenciales?",
            "next_step": "email",
            "extract_key": "email",
        },
        "email": {
            "message": "Excelente. ¿Qué módulos te interesan? (Ventas, Agendamiento, Cobros, Lead Scoring, Alertas, Seguimientos, Campañas, Analytics)",
            "next_step": "modules",
            "extract_key": "modules",
        },
        "modules": {
            "message": "Perfecto. Tu configuración está lista. Mi equipo la revisará y te contactaremos en las próximas 24 horas para activar tu agente. ¿Alguna pregunta adicional?",
            "next_step": "complete",
            "extract_key": None,
        },
        "complete": {
            "message": "¡Configuración completada! Tu agente estará activo pronto. Recibirás un correo con todos los detalles.",
            "next_step": None,
            "extract_key": None,
        },
    }

    def __init__(self, supabase_client: Any):
        """
        Initialize onboarding wizard.

        Args:
            supabase_client: Supabase client
        """
        self.supabase = supabase_client

    async def start_wizard(self, phone_number: str) -> dict[str, Any]:
        """
        Start onboarding process for a new client.

        Args:
            phone_number: Client's phone number

        Returns:
            Wizard state dict
        """
        try:
            wizard_state = {
                "phone_number": phone_number,
                "current_step": "welcome",
                "data": {},
                "created_at": __import__("datetime").datetime.utcnow().isoformat(),
            }

            # Save wizard state
            self.supabase.table("onboarding_sessions").insert(
                wizard_state
            ).execute()

            logger.info(f"Onboarding started for {phone_number}")

            return wizard_state

        except Exception as e:
            logger.error(f"Error starting wizard: {e}")
            return None

    async def get_wizard_state(self, phone_number: str) -> Optional[dict[str, Any]]:
        """
        Get wizard state for a phone number.

        Args:
            phone_number: Client's phone number

        Returns:
            Wizard state or None
        """
        try:
            response = self.supabase.table("onboarding_sessions").select(
                "*"
            ).eq("phone_number", phone_number).order(
                "created_at", desc=True
            ).limit(1).execute()

            if response.data:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error fetching wizard state: {e}")
            return None

    async def process_response(
        self,
        phone_number: str,
        user_response: str,
    ) -> dict[str, Any]:
        """
        Process user response and advance wizard.

        Args:
            phone_number: Client's phone number
            user_response: User's message response

        Returns:
            Wizard state and next message
        """
        try:
            wizard = await self.get_wizard_state(phone_number)

            if not wizard:
                logger.warning(f"No wizard state found for {phone_number}")
                return None

            current_step = wizard.get("current_step")
            step_config = self.STEPS.get(current_step)

            if not step_config:
                logger.error(f"Invalid step: {current_step}")
                return None

            # Extract data from response
            if step_config.get("extract_key"):
                wizard["data"][step_config["extract_key"]] = user_response

            # Advance to next step
            next_step = step_config.get("next_step")

            if next_step:
                wizard["current_step"] = next_step

                # Format next message
                next_config = self.STEPS.get(next_step)
                next_message = next_config.get("message", "")

                # Insert variables
                if "{" in next_message:
                    next_message = next_message.format(**wizard["data"])

                # Update wizard state
                self.supabase.table("onboarding_sessions").update({
                    "current_step": next_step,
                    "data": wizard["data"],
                }).eq("phone_number", phone_number).execute()

                return {
                    "status": "continue",
                    "message": next_message,
                    "step": next_step,
                }

            else:
                # Wizard complete, generate config
                await self._generate_client_config(phone_number, wizard["data"])

                return {
                    "status": "complete",
                    "message": step_config.get("message", ""),
                    "data": wizard["data"],
                }

        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return None

    async def _generate_client_config(
        self,
        phone_number: str,
        wizard_data: dict[str, Any],
    ) -> bool:
        """
        Generate client configuration from wizard data.

        Args:
            phone_number: Client's phone number
            wizard_data: Collected data

        Returns:
            True if config generated successfully
        """
        try:
            # Create client record
            client_id = str(__import__("uuid").uuid4())

            client = {
                "id": client_id,
                "name": wizard_data.get("business_name", ""),
                "email": wizard_data.get("email", ""),
                "phone": phone_number,
                "industry": wizard_data.get("industry", ""),
                "status": "pending_review",
                "created_at": __import__("datetime").datetime.utcnow().isoformat(),
            }

            self.supabase.table("clients").insert(client).execute()

            # Create client config
            modules = self._parse_modules(wizard_data.get("modules", ""))

            config = {
                "client_id": client_id,
                "system_prompt": await self._generate_system_prompt(wizard_data),
                "temperature": 0.7,
                "max_tokens": 4000,
                "active_modules": modules,
                "business_hours_start": "08:00",
                "business_hours_end": "18:00",
                "business_hours_timezone": wizard_data.get("timezone", "America/Guayaquil"),
            }

            self.supabase.table("client_config").insert(config).execute()

            # Create client channels record for WhatsApp
            whatsapp_channel = {
                "client_id": client_id,
                "channel_type": "whatsapp",
                "channel_identifier": wizard_data.get("whatsapp_number", ""),
                "status": "pending_verification",
                "channel_credentials": {},
            }

            self.supabase.table("client_channels").insert(
                whatsapp_channel
            ).execute()

            # Mark onboarding as complete
            self.supabase.table("onboarding_sessions").update({
                "current_step": "complete",
                "client_id": client_id,
                "completed_at": __import__("datetime").datetime.utcnow().isoformat(),
            }).eq("phone_number", phone_number).execute()

            logger.info(f"Client config generated for {client_id}")

            return True

        except Exception as e:
            logger.error(f"Error generating config: {e}")
            return False

    async def _generate_system_prompt(
        self,
        wizard_data: dict[str, Any],
    ) -> str:
        """
        Generate system prompt based on wizard data.

        Args:
            wizard_data: Wizard data

        Returns:
            System prompt string
        """
        business_name = wizard_data.get("business_name", "")
        industry = wizard_data.get("industry", "")
        services = wizard_data.get("services", "")
        hours = wizard_data.get("business_hours", "")

        prompt = f"""Eres un agente de atención al cliente para {business_name}, una empresa en el rubro de {industry}.

Servicios ofrecidos: {services}

Horario de atención: {hours}

Tus responsabilidades:
1. Saludar cordialmente a los clientes
2. Responder preguntas sobre nuestros servicios
3. Ayudar con cotizaciones y presupuestos
4. Agendar citas cuando sea necesario
5. Calificar leads según su interés
6. Escalar a un asesor humano si es necesario

Sé amigable, profesional y eficiente. Simula escritura natural con pequeños delays.
Si no puedes resolver algo, ofrece contacto con un asesor humano."""

        return prompt

    def _parse_modules(self, modules_text: str) -> dict[str, bool]:
        """
        Parse modules from user text.

        Args:
            modules_text: User-provided module text

        Returns:
            Dict of enabled modules
        """
        module_map = {
            "ventas": "ventas",
            "sales": "ventas",
            "agendamiento": "agendamiento",
            "scheduling": "agendamiento",
            "citas": "agendamiento",
            "cobros": "cobros",
            "payment": "cobros",
            "payments": "cobros",
            "lead": "calificacion",
            "scoring": "calificacion",
            "qualification": "calificacion",
            "alertas": "alertas",
            "alerts": "alertas",
            "notifications": "alertas",
            "seguimiento": "seguimiento",
            "follow": "seguimiento",
            "followup": "seguimiento",
            "links": "links_pago",
            "payment_links": "links_pago",
            "pagos": "links_pago",
            "campanas": "campanas",
            "campaigns": "campanas",
            "broadcast": "campanas",
            "analytics": "analytics",
            "reports": "analytics",
            "reportes": "analytics",
        }

        modules_text_lower = modules_text.lower()

        enabled = {}

        for keyword, module in module_map.items():
            if keyword in modules_text_lower:
                enabled[module] = True

        # Default modules
        default_modules = ["ventas", "calificacion", "alertas"]

        for module in default_modules:
            if module not in enabled:
                enabled[module] = True

        return enabled

    async def get_wizard_progress(self, phone_number: str) -> float:
        """
        Get wizard progress as percentage.

        Args:
            phone_number: Client's phone number

        Returns:
            Progress percentage (0-100)
        """
        wizard = await self.get_wizard_state(phone_number)

        if not wizard:
            return 0

        current_step = wizard.get("current_step")

        step_order = [
            "welcome",
            "business_name",
            "industry",
            "services",
            "business_hours",
            "timezone",
            "whatsapp_number",
            "email",
            "modules",
            "complete",
        ]

        current_index = step_order.index(current_step) if current_step in step_order else 0
        total_steps = len(step_order)

        return (current_index / total_steps) * 100
