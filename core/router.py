"""
Router module: routes normalized messages to correct agent per client.

Handles client identification, agent instantiation, and message processing.
"""

import logging
from typing import Any, Optional

from core.agent import AgentEngine

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes messages to correct agent instance per client."""

    def __init__(self, supabase_client: Any, supabase_service_client: Any = None):
        """
        Initialize message router.

        Args:
            supabase_client: Supabase client instance
            supabase_service_client: Service role Supabase client (for elevated permissions)
        """
        self.supabase = supabase_client
        self.supabase_service = supabase_service_client or supabase_client
        self.agent_instances = {}  # Cache of AgentEngine instances by client_id

    async def initialize(self) -> None:
        """Initialize message router. Supabase client is already initialized."""
        logger.info("message_router_initialized")

    async def close(self) -> None:
        """Cleanup and close message router."""
        self.agent_instances.clear()
        logger.info("message_router_closed")

    async def _get_client_config(self, client_id: str) -> dict[str, Any]:
        """
        Fetch client configuration from Supabase.

        Args:
            client_id: Client ID

        Returns:
            Client config with agent settings
        """
        defaults = {
            "client_id": client_id,
            "system_prompt": "You are a helpful business assistant.",
            "temperature": 0.7,
            "max_tokens": 4000,
            "active_modules": {
                "ventas": True,
                "agendamiento": True,
                "cobros": True,
                "links_pago": True,
                "calificacion": True,
                "campanas": False,
                "alertas": True,
                "seguimientos": True,
                "documentos": True,
            },
            "business_hours_start": "08:00",
            "business_hours_end": "18:00",
            "business_hours_timezone": "America/Guayaquil",
        }

        try:
            response = self.supabase.table("agentes").select("*").eq(
                "cliente_id", client_id
            ).limit(1).execute()

            if not response.data:
                logger.warning(
                    f"No agentes config found for client_id={client_id}, using defaults with calificacion FORCED ENABLED",
                    extra={"client_id": client_id}
                )
                defaults["active_modules"]["calificacion"] = True
                return defaults

            config = response.data[0]
            logger.info(
                f"agentes row fetched for client_id={client_id}: keys={list(config.keys())}"
            )

            # Map column names to internal keys (handle both Spanish and English naming)
            if "system_prompt" in config and config["system_prompt"]:
                config["system_prompt"] = config["system_prompt"]
            elif "prompt_sistema" in config and config["prompt_sistema"]:
                config["system_prompt"] = config["prompt_sistema"]

            if "temperature" in config and config["temperature"] is not None:
                config["temperature"] = config["temperature"]
            elif "temperatura" in config and config["temperatura"] is not None:
                config["temperature"] = config["temperatura"]

            if "max_tokens" in config and config["max_tokens"] is not None:
                config["max_tokens"] = config["max_tokens"]
            elif "tokens_maximos" in config and config["tokens_maximos"] is not None:
                config["max_tokens"] = config["tokens_maximos"]

            merged = {**defaults, **config}

            # Ensure active_modules exists and has calificacion enabled
            if "active_modules" not in merged or not isinstance(merged["active_modules"], dict):
                merged["active_modules"] = defaults["active_modules"].copy()
            else:
                # Merge with defaults to ensure all modules are present
                merged["active_modules"] = {
                    **defaults["active_modules"],
                    **merged.get("active_modules", {})
                }

            # CRITICAL: Ensure calificacion is always enabled
            merged["active_modules"]["calificacion"] = True

            system_prompt = merged.get("system_prompt", "")
            logger.info(
                f"system_prompt for client_id={client_id} "
                f"({'from agentes' if system_prompt != defaults['system_prompt'] else 'DEFAULT fallback'}): "
                f"{system_prompt[:100]!r}",
                extra={"active_modules": merged.get("active_modules", {})}
            )
            return merged

        except Exception as e:
            logger.warning(
                f"Could not fetch config for {client_id}: {e}, using defaults with calificacion FORCED ENABLED",
                extra={"client_id": client_id}
            )
            defaults["active_modules"]["calificacion"] = True
            return {
                "client_id": client_id,
                "system_prompt": defaults.get("system_prompt", "You are a helpful business assistant."),
                "temperature": defaults.get("temperature", 0.7),
                "max_tokens": defaults.get("max_tokens", 4000),
                "active_modules": defaults["active_modules"].copy(),
                "business_hours_start": defaults.get("business_hours_start", "08:00"),
                "business_hours_end": defaults.get("business_hours_end", "18:00"),
                "business_hours_timezone": defaults.get("business_hours_timezone", "America/Guayaquil"),
            }

    async def _get_or_create_agent(self, client_id: str) -> AgentEngine:
        """
        Get cached agent instance or create new one.

        Args:
            client_id: Client ID

        Returns:
            AgentEngine instance for this client
        """
        if client_id in self.agent_instances:
            return self.agent_instances[client_id]

        # Fetch client config
        config = await self._get_client_config(client_id)
        config["client_id"] = client_id

        # Create agent instance with both regular and service clients
        # Service client allows CalificacionModule to bypass RLS for lead scoring
        agent = AgentEngine(
            config,
            supabase_client=self.supabase,
            supabase_service_client=self.supabase_service
        )
        self.agent_instances[client_id] = agent

        logger.info(f"Agent instance created for client {client_id}")

        return agent

    async def identify_client(
        self,
        identifier: str,
        identifier_type: str = "id",
    ) -> Optional[str]:
        """
        Identify client from webhook identifier.

        identifier_type can be:
        - "id": Direct client ID
        - "phone_number_id": WhatsApp phone_number_id
        - "page_id": Instagram/Facebook page_id
        - "sender_email": Email sender domain

        Args:
            identifier: The identifier value
            identifier_type: Type of identifier

        Returns:
            Client ID if found, None otherwise
        """
        try:
            if identifier_type == "id":
                return identifier

            elif identifier_type == "phone_number_id":
                # Map WhatsApp phone_number_id to client
                response = self.supabase.table("canales_config").select(
                    "cliente_id"
                ).eq("canal", "whatsapp").eq(
                    "phone_number_id", identifier
                ).single().execute()

                return response.data["cliente_id"] if response.data else None

            elif identifier_type == "page_id":
                # Map Instagram/Facebook page_id to client
                response = self.supabase.table("canales_config").select(
                    "cliente_id"
                ).eq("canal", "instagram").eq(
                    "page_id", identifier
                ).single().execute()

                return response.data["cliente_id"] if response.data else None

            elif identifier_type == "sender_email":
                # Map email domain to client
                response = self.supabase.table("canales_config").select(
                    "cliente_id"
                ).eq("canal", "email").eq(
                    "email_address", identifier
                ).single().execute()

                return response.data["cliente_id"] if response.data else None

        except Exception as e:
            logger.warning(f"Could not identify client: {e}")

        return None

    async def route_message(
        self,
        client_id: str,
        mensaje_normalizado: dict[str, Any],
        memory_context: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Route message to agent and get response.

        Args:
            client_id: Client ID (from webhook or header)
            mensaje_normalizado: Normalized message dict with:
                - text: str
                - sender_id: str
                - channel: str
                - media_url: Optional[str]
                - media_type: Optional[str]
            memory_context: Previous conversation turns (from memory.py)

        Returns:
            Agent response with:
                - response_text: str
                - function_calls: list[dict]
                - typing_indicator_ms: int
                - message_delay_ms: int
                - split_messages: list[str]
                - escalated: bool
        """
        try:
            logger.info(
                f"Routing message from {mensaje_normalizado.get('sender_id')}",
                extra={
                    "client_id": client_id,
                    "channel": mensaje_normalizado.get("channel"),
                },
            )

            # Validate client exists
            client_response = self.supabase.table("clientes").select("id, estado").eq(
                "id", client_id
            ).single().execute()

            if not client_response.data:
                logger.error(f"Client not found: {client_id}")
                return {
                    "error": "Client not found",
                    "escalated": True,
                }

            client = client_response.data

            # Check if client is active
            if client.get("estado") != "activo":
                logger.warning(f"Client {client_id} is not active: {client.get('estado')}")
                return {
                    "response_text": "El servicio está temporalmente inactivo. Intenta más tarde.",
                    "escalated": True,
                }

            # Get agent instance for this client
            agent = await self._get_or_create_agent(client_id)

            # Process message
            logger.info(f"🟡 === CALLING agent.process_message ===")
            logger.info(f"🟡 client_id={client_id}, sender_id={mensaje_normalizado.get('sender_id')}")
            response = await agent.process_message(
                mensaje_normalizado, client_id, memory_context
            )
            logger.info(f"🟡 === agent.process_message RETURNED ===")
            logger.info(f"🟡 response_text length={len(response.get('response_text', ''))}")

            logger.info(
                f"Message processed",
                extra={
                    "client_id": client_id,
                    "request_id": response.get("request_id"),
                    "escalated": response.get("escalated", False),
                },
            )

            return response

        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)

            return {
                "response_text": "Disculpa, hubo un error procesando tu mensaje.",
                "function_calls": [],
                "typing_indicator_ms": 1000,
                "message_delay_ms": 500,
                "split_messages": [
                    "Disculpa, hubo un error procesando tu mensaje.",
                    "Un agente humano te contactará pronto.",
                ],
                "escalated": True,
                "error": str(e),
            }

    def invalidate_agent_cache(self, client_id: str) -> None:
        """
        Invalidate cached agent instance (e.g., after config change).

        Args:
            client_id: Client ID
        """
        if client_id in self.agent_instances:
            del self.agent_instances[client_id]
            logger.info(f"Agent cache invalidated for client {client_id}")

    def get_agent_status(self, client_id: str) -> dict[str, Any]:
        """
        Get status of agent instance for a client.

        Args:
            client_id: Client ID

        Returns:
            Status dict with cached status
        """
        is_cached = client_id in self.agent_instances

        return {
            "client_id": client_id,
            "agent_cached": is_cached,
            "total_agents_cached": len(self.agent_instances),
        }
