"""
Facebook channel: Meta Graph API webhook handler.

Handles Messenger messages and sends responses.
"""

import hashlib
import hmac
import json
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class FacebookHandler:
    """Handles Facebook Messenger messages via Meta Graph API."""

    def __init__(
        self,
        verify_token: str,
        app_secret: str,
        supabase_client: Any,
        router: Any,
        normalizer: Any,
        buffer: Any,
        memory: Any,
    ):
        """
        Initialize Facebook handler.

        Args:
            verify_token: Verification token for webhook validation
            app_secret: Meta app secret for signature validation
            supabase_client: Supabase client for credentials
            router: MessageRouter instance
            normalizer: MessageNormalizer instance
            buffer: MessageBuffer instance
            memory: MemoryManager instance
        """
        self.verify_token = verify_token
        self.app_secret = app_secret
        self.supabase = supabase_client
        self.router = router
        self.normalizer = normalizer
        self.buffer = buffer
        self.memory = memory
        self.api_base_url = "https://graph.instagram.com/v18.0"
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    def verify_webhook_signature(
        self,
        body: bytes,
        x_hub_signature: str,
    ) -> bool:
        """
        Verify Meta webhook signature (HMAC-SHA256).

        Args:
            body: Request body bytes
            x_hub_signature: X-Hub-Signature header

        Returns:
            True if signature is valid
        """
        try:
            if not x_hub_signature or "=" not in x_hub_signature:
                logger.warning("Invalid X-Hub-Signature format")
                return False

            _, provided_hash = x_hub_signature.split("=", 1)

            expected_hash = hmac.new(
                self.app_secret.encode(),
                body,
                hashlib.sha1,
            ).hexdigest()

            if not hmac.compare_digest(provided_hash, expected_hash):
                logger.warning("Signature validation failed")
                return False

            logger.info("Webhook signature verified")
            return True

        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    async def handle_webhook(
        self,
        payload: dict[str, Any],
        x_hub_signature: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Handle Facebook webhook payload.

        Args:
            payload: Webhook payload from Meta
            x_hub_signature: X-Hub-Signature header for verification

        Returns:
            Response dict
        """
        try:
            if x_hub_signature:
                body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
                if not self.verify_webhook_signature(body_str.encode(), x_hub_signature):
                    logger.error("Webhook signature verification failed")
                    return {"error": "Signature verification failed"}

            logger.info(
                "Facebook webhook received",
                extra={"object": payload.get("object")},
            )

            if payload.get("object") == "page":
                entries = payload.get("entry", [])
                for entry in entries:
                    await self._process_entry(entry)

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return {"error": str(e)}

    async def _process_entry(self, entry: dict[str, Any]) -> None:
        """
        Process webhook entry (contains messages, etc).

        Args:
            entry: Entry from webhook payload
        """
        try:
            page_id = entry.get("id")

            if not page_id:
                logger.warning("Missing page_id in webhook")
                return

            client_id = await self.router.identify_client(
                page_id,
                "page_id",
            )

            if not client_id:
                logger.warning(f"Could not identify client for {page_id}")
                return

            messaging_events = entry.get("messaging", [])
            for event in messaging_events:
                if "message" in event:
                    await self._handle_message(client_id, page_id, event)

        except Exception as e:
            logger.error(f"Error processing entry: {e}", exc_info=True)

    async def _handle_message(
        self,
        client_id: str,
        page_id: str,
        event: dict[str, Any],
    ) -> None:
        """
        Handle inbound message from Facebook.

        Args:
            client_id: Client ID
            page_id: Facebook page ID
            event: Messaging event from webhook
        """
        try:
            sender_id = event.get("sender", {}).get("id", "")
            message_data = event.get("message", {})
            timestamp = event.get("timestamp", "")

            logger.info(
                f"Processing Facebook message from {sender_id}",
                extra={"client_id": client_id},
            )

            normalized = await self.normalizer.normalize_and_validate(
                {
                    "entry": [
                        {
                            "messaging": [event],
                            "id": page_id,
                        }
                    ]
                },
                "facebook",
            )

            if not normalized:
                logger.warning("Failed to normalize message")
                return

            conversation = await self.memory.get_or_create_conversation(
                client_id,
                sender_id,
                "facebook",
            )

            await self.memory.save_message(
                client_id,
                conversation["id"],
                sender_id,
                "user",
                normalized["text"],
                "facebook",
                media_url=normalized.get("media_url"),
                media_type=normalized.get("media_type"),
            )

            memory_context = await self.memory.get_context_for_agent(
                client_id,
                conversation["id"],
            )

            agent_response = await self.router.route_message(
                client_id,
                {
                    "text": normalized["text"],
                    "sender_id": sender_id,
                    "channel": "facebook",
                    "media_url": normalized.get("media_url"),
                    "media_type": normalized.get("media_type"),
                },
                memory_context,
            )

            if agent_response.get("escalated"):
                logger.warning(f"Message escalated for {client_id}")
                return

            response_text = agent_response.get("response_text", "")
            await self.send_message(
                page_id,
                sender_id,
                response_text,
                client_id,
            )

            await self.memory.save_message(
                client_id,
                conversation["id"],
                "agent",
                "agent",
                response_text,
                "facebook",
            )

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def send_message(
        self,
        page_id: str,
        recipient_id: str,
        text: str,
        client_id: str,
        media_url: Optional[str] = None,
    ) -> bool:
        """
        Send message via Facebook Messenger API.

        Args:
            page_id: Facebook page ID
            recipient_id: Recipient user ID
            text: Message text
            client_id: Client ID
            media_url: Optional media URL

        Returns:
            True if sent successfully
        """
        try:
            credentials = await self._get_client_credentials(client_id, "facebook")

            if not credentials:
                logger.error(f"No Facebook credentials for client {client_id}")
                return False

            access_token = credentials.get("access_token")

            payload = {
                "messaging_type": "RESPONSE",
                "recipient": {"id": recipient_id},
                "message": {
                    "text": text,
                },
            }

            if media_url:
                payload["message"] = {
                    "attachment": {
                        "type": "image",
                        "payload": {"url": media_url},
                    }
                }

            url = f"{self.api_base_url}/{page_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = await self.http_client.post(
                url,
                json=payload,
                headers=headers,
            )

            if response.status_code in (200, 201):
                logger.info(
                    f"Facebook message sent to {recipient_id}",
                    extra={"client_id": client_id},
                )
                return True
            else:
                logger.error(
                    f"Failed to send Facebook message: {response.status_code} {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            return False

    async def _get_client_credentials(
        self,
        client_id: str,
        channel: str,
    ) -> Optional[dict[str, str]]:
        """
        Get client's API credentials from Supabase.

        Args:
            client_id: Client ID
            channel: Channel type

        Returns:
            Credentials dict or None
        """
        try:
            response = self.supabase.table("canales_config").select(
                "channel_credentials"
            ).eq("client_id", client_id).eq("channel_type", channel).single().execute()

            if response.data:
                return response.data.get("channel_credentials", {})

            logger.warning(f"No credentials found for {client_id} on {channel}")
            return None

        except Exception as e:
            logger.error(f"Error fetching credentials: {e}")
            return None
