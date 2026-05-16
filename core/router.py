"""
Router module: routes normalized messages to correct agent per client.

Handles client identification, agent instantiation, and message processing.
"""

import logging
import time
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
        self.agent_cache_timestamps = {}  # Track creation time for TTL invalidation
        self.AGENT_CACHE_TTL_SECONDS = 300  # 5 minutes

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
            # 🔍 DIAGNOSTIC: Log the query parameters
            print(f"\n{'='*80}")
            print(f"🔍 [ROUTER CONFIG QUERY] Starting to fetch agentes config")
            print(f"   client_id being queried: {client_id!r}")
            print(f"{'='*80}\n")
            logger.info(
                f"🔍 Fetching agentes config for client_id={client_id!r}",
                extra={"client_id": client_id}
            )

            response = self.supabase.table("agentes").select("*").eq(
                "cliente_id", client_id
            ).limit(1).execute()

            # 🔍 DIAGNOSTIC: Log the query response
            print(f"\n{'='*80}")
            print(f"🔍 [ROUTER CONFIG RESPONSE] Query returned:")
            print(f"   Number of records: {len(response.data) if response.data else 0}")
            print(f"   response.data is None: {response.data is None}")
            print(f"   response.data is empty list: {response.data == []}")
            if response.data:
                print(f"   Available keys in first record: {list(response.data[0].keys())}")
            print(f"{'='*80}\n")

            if not response.data:
                print(f"\n❌ [ROUTER] NO CONFIG FOUND for client_id={client_id}")
                print(f"   → Falling back to DEFAULTS")
                print(f"   → Default system_prompt: {defaults['system_prompt'][:50]}...\n")
                logger.warning(
                    f"No agentes config found for client_id={client_id}, using defaults with calificacion FORCED ENABLED",
                    extra={"client_id": client_id}
                )
                defaults["active_modules"]["calificacion"] = True
                return defaults

            config = response.data[0]

            # 🔍 DIAGNOSTIC: Log the raw config from DB
            print(f"\n{'='*80}")
            print(f"🔍 [ROUTER CONFIG DATA] Raw data from agentes table:")
            print(f"   config['sistema_prompt'] = {config.get('sistema_prompt', 'KEY NOT FOUND')!r}")
            print(f"   config['system_prompt'] = {config.get('system_prompt', 'KEY NOT FOUND')!r}")
            print(f"   config['prompt_sistema'] = {config.get('prompt_sistema', 'KEY NOT FOUND')!r}")
            print(f"   All keys: {list(config.keys())}")
            print(f"{'='*80}\n")

            logger.info(
                f"agentes row fetched for client_id={client_id}: keys={list(config.keys())}"
            )

            # Map column names to internal keys (handle both Spanish and English naming)
            if "system_prompt" in config and config["system_prompt"]:
                print(f"✅ Found 'system_prompt' in config (EN), length={len(config['system_prompt'])}")
                config["system_prompt"] = config["system_prompt"]
            elif "prompt_sistema" in config and config["prompt_sistema"]:
                print(f"✅ Found 'prompt_sistema' in config (ES), length={len(config['prompt_sistema'])}")
                config["system_prompt"] = config["prompt_sistema"]
            elif "sistema_prompt" in config and config["sistema_prompt"]:
                print(f"✅ Found 'sistema_prompt' in config (ES alt), length={len(config['sistema_prompt'])}")
                config["system_prompt"] = config["sistema_prompt"]
            else:
                print(f"❌ NO system_prompt found in config! Available keys: {list(config.keys())}")

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

            # 🔍 DIAGNOSTIC: Log final merged config
            print(f"\n{'='*80}")
            print(f"🔍 [ROUTER MERGED CONFIG] Final config after merge:")
            print(f"   system_prompt source: {'DB (agentes)' if system_prompt != defaults['system_prompt'] else 'DEFAULT'}")
            print(f"   system_prompt length: {len(system_prompt)}")
            print(f"   system_prompt first 150 chars: {system_prompt[:150]!r}")
            print(f"   temperature: {merged.get('temperature')}")
            print(f"   max_tokens: {merged.get('max_tokens')}")
            print(f"   active_modules: {merged.get('active_modules')}")
            print(f"{'='*80}\n")

            logger.info(
                f"system_prompt for client_id={client_id} "
                f"({'from agentes' if system_prompt != defaults['system_prompt'] else 'DEFAULT fallback'}): "
                f"{system_prompt[:100]!r}",
                extra={"active_modules": merged.get("active_modules", {})}
            )
            return merged

        except Exception as e:
            print(f"\n❌ [ROUTER EXCEPTION] Error fetching config:")
            print(f"   Exception: {type(e).__name__}: {e}\n")
            import traceback
            traceback.print_exc()

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

        Implements TTL-based cache invalidation: agents are refreshed every 5 minutes
        to pick up config changes (especially system_prompt) from the database.

        Args:
            client_id: Client ID

        Returns:
            AgentEngine instance for this client
        """
        now = time.time()
        cache_age = now - self.agent_cache_timestamps.get(client_id, 0)
        is_cached = client_id in self.agent_instances
        cache_expired = is_cached and cache_age > self.AGENT_CACHE_TTL_SECONDS

        # If cached and still fresh, use it
        if is_cached and not cache_expired:
            print(f"\n{'='*80}")
            print(f"✅ [AGENT CACHE HIT] Returning cached agent for {client_id}")
            print(f"   Cache age: {cache_age:.1f}s (TTL: {self.AGENT_CACHE_TTL_SECONDS}s)")
            print(f"{'='*80}\n")
            return self.agent_instances[client_id]

        # Cache miss or expired: invalidate and recreate
        if cache_expired:
            print(f"\n{'='*80}")
            print(f"⏰ [AGENT CACHE EXPIRED] Invalidating old agent for {client_id}")
            print(f"   Cache age: {cache_age:.1f}s (TTL: {self.AGENT_CACHE_TTL_SECONDS}s)")
            print(f"{'='*80}\n")
            del self.agent_instances[client_id]
            logger.info(f"Agent cache expired for client {client_id} (age: {cache_age:.1f}s)")

        # Fetch fresh client config from database
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
        self.agent_cache_timestamps[client_id] = now

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
                print(f"\n🔍 [IDENTIFY] Direct ID provided: {identifier}")
                return identifier

            elif identifier_type == "phone_number_id":
                # Map WhatsApp phone_number_id to client
                print(f"\n{'='*80}")
                print(f"🔍 [IDENTIFY] Searching for phone_number_id in canales_config:")
                print(f"   phone_number_id: {identifier!r}")
                print(f"{'='*80}\n")

                response = self.supabase.table("canales_config").select(
                    "*"  # Select all to see what fields are available
                ).eq("canal", "whatsapp").eq(
                    "phone_number_id", identifier
                ).single().execute()

                print(f"🔍 [IDENTIFY] Query response:")
                if response.data:
                    print(f"   Found record: {list(response.data.keys())}")
                    client_id = response.data["cliente_id"]
                    print(f"✅ [IDENTIFY] Resolved phone_number_id={identifier} → client_id={client_id!r}")
                    return client_id
                else:
                    print(f"❌ [IDENTIFY] NO MATCH in canales_config")
                    print(f"   Checking all records in canales_config for debugging...")
                    try:
                        all_canales = self.supabase.table("canales_config").select("*").execute()
                        print(f"   Total records in canales_config: {len(all_canales.data or [])}")
                        for i, record in enumerate((all_canales.data or [])[:5]):
                            print(f"      [{i}] canal={record.get('canal')}, phone_id={record.get('phone_number_id')}, cliente_id={record.get('cliente_id')}")
                    except Exception as debug_e:
                        print(f"   Could not fetch debug info: {debug_e}")
                    return None

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
            print(f"\n{'='*80}")
            print(f"🔍 [ROUTE_MESSAGE] Getting or creating agent instance:")
            print(f"   client_id: {client_id!r}")
            print(f"   Checking if already cached... {client_id in self.agent_instances}")
            print(f"{'='*80}\n")

            agent = await self._get_or_create_agent(client_id)

            print(f"\n{'='*80}")
            print(f"🔍 [ROUTE_MESSAGE] Agent obtained:")
            print(f"   Agent.client_id: {agent.client_id!r}")
            print(f"   Agent.system_prompt length: {len(agent.system_prompt)}")
            print(f"   Agent.system_prompt preview: {agent.system_prompt[:150]!r}")
            print(f"{'='*80}\n")

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
        if client_id in self.agent_cache_timestamps:
            del self.agent_cache_timestamps[client_id]
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
