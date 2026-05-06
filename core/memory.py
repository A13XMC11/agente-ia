"""
Conversation memory: manages conversation history and context.

Stores in Supabase with Row-Level Security for multi-tenancy.
Fetches last N messages for context window, with token awareness.
Identifies cross-channel users and consolidates conversations.
"""

import logging
from datetime import datetime
from typing import Optional, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages conversation history and context in Supabase.

    Features:
    - Full message history per user per client
    - Cross-channel user identification and consolidation
    - Token-aware context truncation for GPT-4o
    - Lead state and scoring per conversation
    - Metadata and session tracking
    """

    def __init__(self, supabase_client: Any):
        """
        Initialize memory manager.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.max_context_turns = 10
        self.max_tokens_context = 3000

    async def get_or_create_conversation(
        self,
        client_id: str,
        user_id: str,
        channel: str,
    ) -> dict[str, Any]:
        """
        Get existing conversation or create new one.

        Args:
            client_id: Client ID
            user_id: User ID
            channel: Channel (whatsapp, email, etc)

        Returns:
            Conversation dict with ID and metadata
        """
        try:
            # Check if conversation exists for this user+channel+client
            response = self.supabase.table("conversaciones").select("*").eq(
                "cliente_id", client_id
            ).eq("usuario_id", user_id).eq("canal", channel).eq(
                "estado", "activa"
            ).order("fecha_inicio", desc=True).limit(1).execute()

            if response.data:
                logger.debug(
                    f"Found existing conversation",
                    extra={"client_id": client_id, "user_id": user_id},
                )
                return response.data[0]

            # Create new conversation
            conversation = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "usuario_id": user_id,
                "canal": channel,
                "estado": "activa",
                "lead_state": "curioso",
                "lead_score": 0.0,
                "fecha_inicio": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "fecha_ultimo_mensaje": None,
            }

            self.supabase.table("conversaciones").insert(conversation).execute()

            logger.info(
                f"Conversation created: {conversation['id']}",
                extra={"client_id": client_id, "user_id": user_id},
            )

            return conversation

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise

    async def save_message(
        self,
        client_id: str,
        conversation_id: str,
        sender_id: str,
        sender_type: str,
        message_text: str,
        channel: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
        function_calls: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Save a message to conversation history.

        Args:
            client_id: Client ID
            conversation_id: Conversation ID
            sender_id: User ID or "agent"
            sender_type: "user" or "agent"
            message_text: Message content
            channel: Channel (whatsapp, email, etc)
            media_url: Optional URL to media
            media_type: Optional media type (image, video, document)
            function_calls: Optional list of function calls made
            metadata: Optional additional metadata

        Returns:
            Message object with ID and timestamp
        """
        try:
            message = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "sender_type": sender_type,
                "message_text": message_text,
                "channel": channel,
                "media_url": media_url,
                "media_type": media_type,
                "function_calls": function_calls or [],
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("mensajes").insert(message).execute()

            # Update conversation's fecha_ultimo_mensaje
            self.supabase.table("conversaciones").update(
                {"fecha_ultimo_mensaje": message["created_at"]}
            ).eq("id", conversation_id).execute()

            logger.debug(
                f"Message saved: {message['id']}",
                extra={"client_id": client_id, "conversation_id": conversation_id},
            )

            return message

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return {"error": str(e)}

    async def get_context_for_agent(
        self,
        client_id: str,
        conversation_id: str,
    ) -> list[dict[str, str]]:
        """
        Get conversation context formatted for GPT-4o.

        Returns messages as role/content pairs for chat API.
        Optimizes token count by keeping most recent relevant messages.

        Args:
            client_id: Client ID
            conversation_id: Conversation ID

        Returns:
            List of {"role": "user|assistant", "content": str}
        """
        try:
            # Fetch full conversation
            response = self.supabase.table("mensajes").select("*").eq(
                "cliente_id", client_id
            ).eq("conversacion_id", conversation_id).order(
                "created_at", desc=True
            ).limit(20).execute()

            messages = list(reversed(response.data or []))

            # Convert to chat format
            context = []
            token_estimate = 0

            for msg in messages:
                sender_type = msg.get("sender_type", "user")
                role = "user" if sender_type == "user" else "assistant"
                content = msg.get("message_text", "")

                # Estimate tokens (rough: 1 token per 4 chars)
                tokens = len(content) // 4

                # Stop if adding this would exceed token limit
                if token_estimate + tokens > self.max_tokens_context:
                    break

                context.append({"role": role, "content": content})
                token_estimate += tokens

            logger.debug(
                f"Context optimized: {len(context)} messages, ~{token_estimate} tokens",
                extra={"client_id": client_id},
            )

            return context

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    async def update_conversation_state(
        self,
        conversation_id: str,
        lead_state: Optional[str] = None,
        lead_score: Optional[float] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update conversation state (lead score, status, etc).

        Args:
            conversation_id: Conversation ID
            lead_state: New lead state
            lead_score: New lead score
            status: New conversation status

        Returns:
            Updated conversation
        """
        try:
            update_data = {"updated_at": datetime.utcnow().isoformat()}

            if lead_state is not None:
                update_data["lead_state"] = lead_state

            if lead_score is not None:
                update_data["lead_score"] = lead_score

            if status is not None:
                update_data["estado"] = status

            response = self.supabase.table("conversaciones").update(
                update_data
            ).eq("id", conversation_id).execute()

            logger.debug(f"Conversation state updated: {conversation_id}")

            return response.data[0] if response.data else {}

        except Exception as e:
            logger.error(f"Error updating conversation state: {e}")
            return {"error": str(e)}

    async def get_conversation_history(
        self,
        client_id: str,
        conversation_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Fetch conversation history.

        Args:
            client_id: Client ID
            conversation_id: Conversation ID
            limit: Max messages to return (default 10)

        Returns:
            List of messages in chronological order
        """
        try:
            response = self.supabase.table("mensajes").select("*").eq(
                "cliente_id", client_id
            ).eq("conversacion_id", conversation_id).order(
                "created_at", desc=False
            ).limit(limit).execute()

            messages = response.data or []

            logger.debug(
                f"Fetched {len(messages)} messages",
                extra={"client_id": client_id, "conversation_id": conversation_id},
            )

            return messages

        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            return []

    async def get_user_profile(
        self,
        client_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Get user profile with conversation summary.

        Includes lead score, state, total messages, etc.

        Args:
            client_id: Client ID
            user_id: User ID

        Returns:
            User profile with metadata
        """
        try:
            # Get latest conversation
            conv_response = self.supabase.table("conversaciones").select(
                "*"
            ).eq("cliente_id", client_id).eq("usuario_id", user_id).order(
                "fecha_inicio", desc=True
            ).limit(1).execute()

            latest_conversation = conv_response.data[0] if conv_response.data else None

            # Count messages
            messages_response = self.supabase.table("mensajes").select(
                "id", count="exact"
            ).eq("cliente_id", client_id).eq("sender_id", user_id).execute()

            message_count = messages_response.count or 0

            profile = {
                "user_id": user_id,
                "message_count": message_count,
                "lead_score": latest_conversation.get("lead_score", 0)
                if latest_conversation
                else 0,
                "lead_state": latest_conversation.get("lead_state", "curioso")
                if latest_conversation
                else "curioso",
                "last_interaction": latest_conversation.get("fecha_ultimo_mensaje")
                if latest_conversation
                else None,
            }

            return profile

        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {"error": str(e)}
