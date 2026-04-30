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

    def __init__(self, supabase_client: Any):
        """
        Initialize message router.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
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
        try:
            response = self.supabase.table("client_config").select("*").eq(
                "client_id", client_id
            ).single().execute()

            config = response.data

            # Merge with defaults
            defaults = {
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

            # Merge config with defaults (config takes precedence)
            merged = {**defaults, **config}

            return merged

        except Exception as e:
            logger.warning(f"Could not fetch config for {client_id}: {e}, using defaults")
            return {
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

        # Create agent instance
        agent = AgentEngine(config)
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
                response = self.supabase.table("client_channels").select(
                    "client_id"
                ).eq("channel_type", "whatsapp").eq(
                    "channel_identifier", identifier
                ).single().execute()

                return response.data["client_id"] if response.data else None

            elif identifier_type == "page_id":
                # Map Instagram/Facebook page_id to client
                response = self.supabase.table("client_channels").select(
                    "client_id"
                ).eq("channel_type", "instagram").eq(
                    "channel_identifier", identifier
                ).single().execute()

                return response.data["client_id"] if response.data else None

            elif identifier_type == "sender_email":
                # Map email domain to client
                response = self.supabase.table("client_channels").select(
                    "client_id"
                ).eq("channel_type", "email").eq(
                    "channel_identifier", identifier
                ).single().execute()

                return response.data["client_id"] if response.data else None

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
            client_response = self.supabase.table("clients").select("id, status").eq(
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
            if client.get("status") != "active":
                logger.warning(f"Client {client_id} is not active: {client.get('status')}")
                return {
                    "response_text": "El servicio está temporalmente inactivo. Intenta más tarde.",
                    "escalated": True,
                }

            # Get agent instance for this client
            agent = await self._get_or_create_agent(client_id)

            # Process message
            response = await agent.process_message(
                mensaje_normalizado, client_id, memory_context
            )

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
