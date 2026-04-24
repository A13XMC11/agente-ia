"""
Message router: identifies client and routes messages to correct agent.

Routes normalized messages to the appropriate agent based on:
- Phone number ID (WhatsApp)
- Page ID (Instagram/Facebook)
- Email address (Email)
"""

import os
from typing import Optional, Any
import structlog
from supabase import create_client, Client

from config.modelos import ChannelTypeEnum, WebhookEvent
from core.normalizer import MessageNormalizer
from core.memory import ConversationMemory
from core.buffer import MessageBuffer


logger = structlog.get_logger(__name__)


class MessageRouter:
    """
    Routes incoming messages to correct agent based on channel and client.

    Responsibilities:
    - Map channel identifiers (phone number ID, page ID, email) to client
    - Fetch client configuration
    - Delegate to appropriate channel handler
    - Track message flow
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        redis_url: str | None = None,
    ):
        """
        Initialize message router.

        Args:
            supabase_url: Supabase URL (from env if not provided)
            supabase_key: Supabase key (from env if not provided)
            redis_url: Redis URL (from env if not provided)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY", "")
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.memory: Optional[ConversationMemory] = None
        self.buffer: Optional[MessageBuffer] = None
        self.normalizer = MessageNormalizer()

    async def initialize(self) -> None:
        """Initialize sub-components (memory, buffer)."""
        self.memory = ConversationMemory(self.supabase_url, self.supabase_key)
        self.buffer = MessageBuffer(self.redis_url)
        await self.buffer.initialize()

        logger.info("message_router_initialized")

    async def close(self) -> None:
        """Close connections."""
        if self.buffer:
            await self.buffer.close()

        logger.info("message_router_closed")

    async def identify_client(
        self,
        channel: ChannelTypeEnum,
        channel_identifier: str,
    ) -> Optional[str]:
        """
        Map channel identifier to client ID.

        Different channels use different IDs:
        - WhatsApp: phone_number_id
        - Instagram/Facebook: page_id
        - Email: incoming email address

        Args:
            channel: Channel type
            channel_identifier: Channel-specific identifier

        Returns:
            Client ID if found, None otherwise
        """
        try:
            if channel == ChannelTypeEnum.WHATSAPP:
                # Look up phone number ID in channel_credentials
                response = self.supabase.table("channel_credentials").select(
                    "client_id"
                ).eq("channel", "whatsapp").eq("phone_number_id", channel_identifier).execute()

            elif channel == ChannelTypeEnum.INSTAGRAM:
                response = self.supabase.table("channel_credentials").select(
                    "client_id"
                ).eq("channel", "instagram").eq("page_id", channel_identifier).execute()

            elif channel == ChannelTypeEnum.FACEBOOK:
                response = self.supabase.table("channel_credentials").select(
                    "client_id"
                ).eq("channel", "facebook").eq("page_id", channel_identifier).execute()

            elif channel == ChannelTypeEnum.EMAIL:
                response = self.supabase.table("channel_credentials").select(
                    "client_id"
                ).eq("channel", "email").eq("email_address", channel_identifier).execute()

            else:
                logger.warning("unknown_channel", channel=channel.value)
                return None

            if response.data:
                client_id = response.data[0]["client_id"]
                logger.info(
                    "client_identified",
                    channel=channel.value,
                    client_id=client_id,
                )
                return client_id

            logger.warning(
                "client_not_found_for_channel",
                channel=channel.value,
                identifier=channel_identifier,
            )
            return None

        except Exception as e:
            logger.error(
                "client_identification_error",
                channel=channel.value,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_client_config(
        self,
        client_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Fetch client configuration.

        Args:
            client_id: Client ID

        Returns:
            Config dict with agent settings, active modules, etc.
        """
        try:
            response = self.supabase.table("agent_config").select("*").eq(
                "client_id", client_id
            ).execute()

            if response.data:
                config = response.data[0]
                logger.info("client_config_fetched", client_id=client_id)
                return config

            logger.warning("client_config_not_found", client_id=client_id)
            return None

        except Exception as e:
            logger.error(
                "config_fetch_error",
                client_id=client_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def route_message(
        self,
        channel: ChannelTypeEnum,
        channel_identifier: str,
        webhook_data: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Main routing entry point.

        Normalizes message, identifies client, fetches config, returns routing info.

        Args:
            channel: Channel type
            channel_identifier: Channel-specific identifier
            webhook_data: Raw webhook payload

        Returns:
            Routing dict with client_id, config, normalized_event; or None on error
        """
        logger.info(
            "routing_message",
            channel=channel.value,
            identifier=channel_identifier,
        )

        # Normalize message
        normalized_event = self.normalizer.normalize(channel, webhook_data)
        if not normalized_event:
            logger.warning("message_normalization_failed")
            return None

        # Identify client
        client_id = await self.identify_client(channel, channel_identifier)
        if not client_id:
            logger.warning("client_identification_failed")
            return None

        # Fetch client config
        config = await self.get_client_config(client_id)
        if not config:
            logger.warning("client_config_unavailable")
            return None

        # Check if client is active
        # (You would add client status check here)

        return {
            "client_id": client_id,
            "channel": channel,
            "normalized_event": normalized_event,
            "config": config,
        }

    async def get_conversation_context(
        self,
        client_id: str,
        user_id: str,
        channel: ChannelTypeEnum,
        max_messages: int = 10,
    ) -> dict[str, Any]:
        """
        Get conversation context for agent processing.

        Retrieves or creates conversation, fetches message history.

        Args:
            client_id: Client ID
            user_id: End user ID
            channel: Channel type
            max_messages: Max messages to fetch for context

        Returns:
            Context dict with conversation and messages
        """
        if not self.memory:
            raise RuntimeError("Router not initialized")

        try:
            # Get or create conversation
            conversation = await self.memory.get_or_create_conversation(
                client_id=client_id,
                user_id=user_id,
                channel=channel,
            )

            # Fetch context messages
            messages = await self.memory.get_context(
                conversation_id=conversation["id"],
                max_messages=max_messages,
            )

            # Fetch user profile
            user_profile = await self.memory.get_user_profile(client_id, user_id)

            return {
                "conversation_id": conversation["id"],
                "messages": messages,
                "user_profile": user_profile,
                "lead_score": conversation.get("lead_score", 0.0),
                "lead_state": conversation.get("lead_state", "curioso"),
            }

        except Exception as e:
            logger.error(
                "context_fetch_error",
                client_id=client_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return {}
