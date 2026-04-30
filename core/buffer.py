"""
Buffer module: message debouncing with Redis.

Debounces rapid messages (WhatsApp/Instagram/Facebook) to avoid flooding.
Email is not buffered (immediate delivery).

Delay: 4 seconds for social channels, no delay for email.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class MessageBuffer:
    """Manages message debouncing for social channels using Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize message buffer.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.buffer_delay = 4  # seconds for social channels
        self.email_delay = 0  # no delay for email
        self.max_buffer_size = 3  # Max messages before immediate send
        self.max_message_length = 1000  # Max chars per message before splitting

    async def initialize(self) -> None:
        """Connect to Redis."""
        self.redis = await redis.from_url(self.redis_url)
        logger.info("message_buffer_initialized", redis_url=self.redis_url)

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("message_buffer_closed")

    async def add_to_buffer(
        self,
        conversation_id: str,
        message_text: str,
        sender_id: str = "agent",
    ) -> None:
        """
        Add message to buffer for deferred sending.

        Messages are grouped per conversation; multiple rapid messages are sent together.

        Args:
            conversation_id: ID of conversation
            message_text: Message content
            sender_id: Who sent it (default: "agent")
        """
        if not self.redis:
            raise RuntimeError("Buffer not initialized")

        buffer_key = f"buffer:{conversation_id}"
        timestamp = datetime.utcnow().isoformat()

        message_data = {
            "text": message_text,
            "sender_id": sender_id,
            "timestamp": timestamp,
        }

        # Add to Redis list
        await self.redis.rpush(
            buffer_key,
            json.dumps(message_data),
        )

        # Set expiration (30 seconds)
        await self.redis.expire(buffer_key, 30)

        logger.info(
            "message_added_to_buffer",
            conversation_id=conversation_id,
            message_length=len(message_text),
        )

    async def flush_buffer(
        self,
        conversation_id: str,
        channel: str,
        send_callback,
    ) -> None:
        """
        Flush all buffered messages for a conversation.

        Groups them together and applies human-like timing.

        Args:
            conversation_id: ID of conversation to flush
            channel: Channel to send on
            send_callback: Async function to call to send messages
        """
        if not self.redis:
            raise RuntimeError("Buffer not initialized")

        buffer_key = f"buffer:{conversation_id}"

        # Get all buffered messages
        buffered = await self.redis.lrange(buffer_key, 0, -1)
        if not buffered:
            return

        # Parse messages
        messages = []
        for msg_bytes in buffered:
            try:
                msg = json.loads(msg_bytes.decode())
                messages.append(msg)
            except json.JSONDecodeError:
                logger.error("failed_to_parse_buffered_message", buffer_key=buffer_key)

        if not messages:
            return

        # Group messages by content
        combined_text = "\n".join([m["text"] for m in messages])

        # Calculate realistic delay based on message length
        delay = self._calculate_delay(combined_text)

        # Add random jitter (50-200ms)
        jitter = random.uniform(0.05, 0.2)
        total_delay = delay + jitter

        logger.info(
            "flushing_buffer",
            conversation_id=conversation_id,
            message_count=len(messages),
            total_length=len(combined_text),
            delay_seconds=total_delay,
        )

        # Send typing indicator
        await send_callback(
            conversation_id=conversation_id,
            channel=channel,
            typing_indicator=True,
        )

        # Wait before sending
        await asyncio.sleep(total_delay)

        # Split message if too long
        message_chunks = self._split_message(combined_text)

        # Send each chunk with small delay between them
        for i, chunk in enumerate(message_chunks):
            await send_callback(
                conversation_id=conversation_id,
                channel=channel,
                message_text=chunk,
                typing_indicator=False,
            )

            # Small delay between messages (0.5-1.5 seconds)
            if i < len(message_chunks) - 1:
                await asyncio.sleep(random.uniform(0.5, 1.5))

        # Clear buffer
        await self.redis.delete(buffer_key)

        logger.info(
            "buffer_flushed",
            conversation_id=conversation_id,
            chunks_sent=len(message_chunks),
        )

    def _calculate_delay(self, message_text: str) -> float:
        """
        Calculate realistic response delay based on message length.

        Simulates typing time: ~50ms per character + base delay.

        Args:
            message_text: Message to calculate delay for

        Returns:
            Delay in seconds
        """
        # Base delay (user thinking time)
        base_delay = random.uniform(0.5, 1.5)

        # Typing speed: 50-100ms per character
        char_delay = len(message_text) * random.uniform(0.05, 0.1)

        # But cap it at 5 seconds (don't make user wait too long)
        total = min(base_delay + char_delay, 5.0)

        return max(total, 0.5)  # Minimum 0.5 seconds

    def _split_message(self, text: str) -> list[str]:
        """
        Split long message into multiple shorter ones.

        WhatsApp/Meta APIs have message length limits, and humans don't send
        multi-paragraph messages in one go.

        Args:
            text: Full message text

        Returns:
            List of message chunks
        """
        if len(text) <= self.max_message_length:
            return [text]

        chunks = []
        sentences = text.split(". ")

        current_chunk = ""
        for sentence in sentences:
            test_chunk = current_chunk + sentence + ". "

            if len(test_chunk) <= self.max_message_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.rstrip(". "))
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.rstrip(". "))

        return chunks

    async def should_buffer(
        self,
        conversation_id: str,
    ) -> bool:
        """
        Check if a conversation should have its messages buffered.

        Returns True if there are already pending messages.

        Args:
            conversation_id: ID of conversation

        Returns:
            True if buffering should occur
        """
        if not self.redis:
            return False

        buffer_key = f"buffer:{conversation_id}"
        count = await self.redis.llen(buffer_key)
        return count > 0

    async def get_buffer_size(self, conversation_id: str) -> int:
        """
        Get number of messages in buffer for a conversation.

        Args:
            conversation_id: ID of conversation

        Returns:
            Number of buffered messages
        """
        if not self.redis:
            return 0

        buffer_key = f"buffer:{conversation_id}"
        return await self.redis.llen(buffer_key)
