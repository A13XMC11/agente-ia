"""
Conversation memory: manages conversation history and context.

Stores in Supabase with Row-Level Security for multi-tenancy.
Fetches last N messages for context window, with token awareness.
Identifies cross-channel users.
"""

from datetime import datetime
from typing import Optional, Any
import structlog
from supabase import create_client, Client

from config.modelos import (
    ChannelTypeEnum,
    ConversationStatusEnum,
    LeadStateEnum,
    Message,
)


logger = structlog.get_logger(__name__)


class ConversationMemory:
    """
    Manages conversation history and context in Supabase.

    Features:
    - Full message history per user per client
    - Cross-channel user identification
    - Token-aware context truncation
    - Lead state and scoring
    - Metadata and session tracking
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
    ):
        """
        Initialize conversation memory with Supabase client.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase public key (with RLS)
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("conversation_memory_initialized")

    async def get_or_create_conversation(
        self,
        client_id: str,
        user_id: str,
        channel: ChannelTypeEnum,
    ) -> dict[str, Any]:
        """
        Get existing conversation or create new one.

        Args:
            client_id: Business customer ID
            user_id: End user ID from channel
            channel: Communication channel

        Returns:
            Conversation dict with ID and metadata
        """
        try:
            # Check if conversation exists for this user+channel+client
            response = self.supabase.table("conversations").select("*").eq(
                "client_id", client_id
            ).eq("user_id", user_id).eq("channel", channel.value).execute()

            if response.data:
                conversation = response.data[0]
                logger.info(
                    "conversation_retrieved",
                    conversation_id=conversation["id"],
                    client_id=client_id,
                )
                return conversation

            # Create new conversation
            new_conversation = {
                "client_id": client_id,
                "user_id": user_id,
                "channel": channel.value,
                "status": ConversationStatusEnum.ACTIVE.value,
                "lead_state": LeadStateEnum.CURIOSO.value,
                "lead_score": 0.0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = self.supabase.table("conversations").insert(
                new_conversation
            ).execute()

            conversation = response.data[0] if response.data else new_conversation

            logger.info(
                "conversation_created",
                conversation_id=conversation["id"],
                client_id=client_id,
                channel=channel.value,
            )

            return conversation

        except Exception as e:
            logger.error(
                "conversation_creation_error",
                client_id=client_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def add_message(
        self,
        conversation_id: str,
        sender_id: str,
        sender_type: str,
        message_text: str,
        channel: ChannelTypeEnum,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
        function_calls: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Add message to conversation history.

        Args:
            conversation_id: ID of conversation
            sender_id: Who sent the message
            sender_type: "user" or "agent"
            message_text: Message content
            channel: Channel type
            media_url: URL of attachment if any
            media_type: Type of media (image, video, document)
            function_calls: List of function calls made by agent
            metadata: Additional metadata

        Returns:
            Message ID
        """
        try:
            message = {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "sender_type": sender_type,
                "message_text": message_text,
                "channel": channel.value,
                "media_url": media_url,
                "media_type": media_type,
                "function_calls": function_calls or [],
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            response = self.supabase.table("messages").insert(message).execute()

            message_id = response.data[0]["id"] if response.data else None

            logger.info(
                "message_stored",
                conversation_id=conversation_id,
                message_id=message_id,
                sender_type=sender_type,
            )

            return message_id or ""

        except Exception as e:
            logger.error(
                "message_storage_error",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_context(
        self,
        conversation_id: str,
        max_messages: int = 10,
        max_tokens: int = 4000,
    ) -> list[Message]:
        """
        Get conversation context for agent.

        Fetches last N messages, with token-aware truncation to fit in context window.

        Args:
            conversation_id: ID of conversation
            max_messages: Maximum number of messages to fetch
            max_tokens: Maximum tokens for context (approximate)

        Returns:
            List of Message objects for context
        """
        try:
            # Fetch messages in reverse chronological order (newest first)
            response = self.supabase.table("messages").select("*").eq(
                "conversation_id", conversation_id
            ).order("created_at", desc=True).limit(max_messages).execute()

            if not response.data:
                logger.info(
                    "no_messages_found",
                    conversation_id=conversation_id,
                )
                return []

            # Reverse to chronological order (oldest first)
            messages = list(reversed(response.data))

            # Token-aware truncation (rough estimate: 1 token ≈ 4 characters)
            token_count = 0
            context_messages = []

            for message in messages:
                msg_tokens = len(message["message_text"]) // 4
                if token_count + msg_tokens > max_tokens:
                    break

                context_messages.append(
                    Message(
                        id=message["id"],
                        conversation_id=message["conversation_id"],
                        sender_id=message["sender_id"],
                        sender_type=message["sender_type"],
                        message_text=message["message_text"],
                        channel=ChannelTypeEnum(message["channel"]),
                        media_url=message.get("media_url"),
                        media_type=message.get("media_type"),
                        created_at=datetime.fromisoformat(message["created_at"]),
                        function_calls=message.get("function_calls"),
                        metadata=message.get("metadata"),
                    )
                )

                token_count += msg_tokens

            logger.info(
                "context_retrieved",
                conversation_id=conversation_id,
                message_count=len(context_messages),
                token_count=token_count,
            )

            return context_messages

        except Exception as e:
            logger.error(
                "context_retrieval_error",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True,
            )
            return []

    async def update_lead_score(
        self,
        conversation_id: str,
        score: float,
        state: Optional[LeadStateEnum] = None,
    ) -> None:
        """
        Update lead score and state for a conversation.

        Args:
            conversation_id: ID of conversation
            score: Lead score (0-10)
            state: Lead state (optional)
        """
        try:
            update_data = {
                "lead_score": score,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if state:
                update_data["lead_state"] = state.value

            self.supabase.table("conversations").update(update_data).eq(
                "id", conversation_id
            ).execute()

            logger.info(
                "lead_score_updated",
                conversation_id=conversation_id,
                score=score,
                state=state.value if state else None,
            )

        except Exception as e:
            logger.error(
                "lead_score_update_error",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True,
            )

    async def update_conversation_status(
        self,
        conversation_id: str,
        status: ConversationStatusEnum,
    ) -> None:
        """
        Update conversation status.

        Args:
            conversation_id: ID of conversation
            status: New status
        """
        try:
            self.supabase.table("conversations").update({
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", conversation_id).execute()

            logger.info(
                "conversation_status_updated",
                conversation_id=conversation_id,
                status=status.value,
            )

        except Exception as e:
            logger.error(
                "status_update_error",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True,
            )

    async def find_user_by_cross_channel(
        self,
        client_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[str]:
        """
        Find user ID across different channels using email or phone.

        Helps consolidate conversations when same user reaches out on multiple channels.

        Args:
            client_id: Business customer ID
            email: User email if available
            phone: User phone if available

        Returns:
            User ID if found, None otherwise
        """
        try:
            # Search for user with matching email or phone
            query = self.supabase.table("users").select("id").eq(
                "client_id", client_id
            )

            if email:
                query = query.eq("email", email)
            elif phone:
                query = query.eq("phone", phone)
            else:
                return None

            response = query.execute()

            if response.data:
                user_id = response.data[0]["id"]
                logger.info(
                    "user_found_cross_channel",
                    user_id=user_id,
                    client_id=client_id,
                )
                return user_id

            return None

        except Exception as e:
            logger.error(
                "cross_channel_search_error",
                client_id=client_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_user_profile(
        self,
        client_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Get user profile including name, contact info, history summary.

        Args:
            client_id: Business customer ID
            user_id: End user ID

        Returns:
            User profile dictionary
        """
        try:
            response = self.supabase.table("users").select("*").eq(
                "id", user_id
            ).eq("client_id", client_id).execute()

            if not response.data:
                return {}

            profile = response.data[0]

            # Get summary stats
            conv_response = self.supabase.table("conversations").select(
                "id, created_at"
            ).eq("user_id", user_id).eq("client_id", client_id).execute()

            profile["conversation_count"] = len(conv_response.data or [])
            profile["first_contact"] = (
                conv_response.data[0]["created_at"] if conv_response.data else None
            )

            logger.info(
                "user_profile_retrieved",
                user_id=user_id,
                client_id=client_id,
            )

            return profile

        except Exception as e:
            logger.error(
                "profile_retrieval_error",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return {}
