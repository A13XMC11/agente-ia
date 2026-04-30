"""
WhatsApp channel: Meta Cloud API webhook handler.

Handles inbound messages, media, and status updates.
Sends responses with typing indicators and message spacing.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    """Handles WhatsApp Cloud API webhooks and message sending."""

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
        Initialize WhatsApp handler.

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
            x_hub_signature: X-Hub-Signature header (sha1=...)

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
        Handle WhatsApp webhook payload.

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
                "WhatsApp webhook received",
                extra={"object": payload.get("object")},
            )

            if payload.get("object") == "whatsapp_business_account":
                entries = payload.get("entry", [])
                for entry in entries:
                    await self._process_entry(entry)

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return {"error": str(e)}

    async def _process_entry(self, entry: dict[str, Any]) -> None:
        """
        Process webhook entry (contains messages, statuses, etc).

        Args:
            entry: Entry from webhook payload
        """
        try:
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id")

                if not phone_number_id:
                    logger.warning("Missing phone_number_id in webhook")
                    continue

                client_id = await self.router.identify_client(
                    phone_number_id,
                    "phone_number_id",
                )

                if not client_id:
                    logger.warning(f"Could not identify client for {phone_number_id}")
                    continue

                messages = value.get("messages", [])
                for message in messages:
                    await self._handle_message(client_id, phone_number_id, message)

                statuses = value.get("statuses", [])
                for status in statuses:
                    await self._handle_status(client_id, status)

        except Exception as e:
            logger.error(f"Error processing entry: {e}", exc_info=True)

    async def _handle_message(
        self,
        client_id: str,
        phone_number_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Handle inbound message from WhatsApp.

        Args:
            client_id: Client ID
            phone_number_id: WhatsApp phone number ID
            message: Message object from webhook
        """
        try:
            sender_id = message.get("from", "")
            timestamp = message.get("timestamp", "")

            logger.info(
                f"Processing WhatsApp message from {sender_id}",
                extra={"client_id": client_id},
            )

            normalized = await self.normalizer.normalize_and_validate(
                {
                    "entry": [
                        {
                            "changes": [
                                {
                                    "value": {
                                        "messages": [message],
                                        "metadata": {
                                            "phone_number_id": phone_number_id,
                                        },
                                    }
                                }
                            ]
                        }
                    ]
                },
                "whatsapp",
            )

            if not normalized:
                logger.warning("Failed to normalize message")
                return

            conversation = await self.memory.get_or_create_conversation(
                client_id,
                sender_id,
                "whatsapp",
            )

            await self.memory.save_message(
                client_id,
                conversation["id"],
                sender_id,
                "user",
                normalized["text"],
                "whatsapp",
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
                    "channel": "whatsapp",
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
                phone_number_id,
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
                "whatsapp",
            )

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _handle_status(
        self,
        client_id: str,
        status: dict[str, Any],
    ) -> None:
        """
        Handle message status update (delivered, read, etc).

        Args:
            client_id: Client ID
            status: Status object from webhook
        """
        try:
            message_id = status.get("id", "")
            status_type = status.get("status", "")

            logger.info(
                f"Message status update: {message_id} -> {status_type}",
                extra={"client_id": client_id},
            )

        except Exception as e:
            logger.error(f"Error handling status: {e}")

    async def send_message(
        self,
        phone_number_id: str,
        recipient_phone: str,
        text: str,
        client_id: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> bool:
        """
        Send message via WhatsApp Cloud API.

        Args:
            phone_number_id: Sender's phone number ID
            recipient_phone: Recipient's phone number
            text: Message text
            client_id: Client ID
            media_url: Optional media URL
            media_type: Optional media type

        Returns:
            True if sent successfully
        """
        try:
            credentials = await self._get_client_credentials(client_id, "whatsapp")

            if not credentials:
                logger.error(f"No WhatsApp credentials for client {client_id}")
                return False

            access_token = credentials.get("access_token")

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "text",
                "text": {"body": text},
            }

            if media_url and media_type:
                payload["type"] = "image" if media_type == "image" else "document"
                payload[media_type] = {
                    "link": media_url,
                }

            url = f"{self.api_base_url}/{phone_number_id}/messages"
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
                result = response.json()
                message_id = result.get("messages", [{}])[0].get("id", "")
                logger.info(
                    f"Message sent: {message_id}",
                    extra={"client_id": client_id},
                )
                return True
            else:
                logger.error(
                    f"Failed to send message: {response.status_code} {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            return False

    async def send_typing_indicator(
        self,
        phone_number_id: str,
        recipient_phone: str,
        client_id: str,
    ) -> bool:
        """
        Send typing indicator.

        Args:
            phone_number_id: Sender's phone number ID
            recipient_phone: Recipient's phone number
            client_id: Client ID

        Returns:
            True if sent successfully
        """
        try:
            credentials = await self._get_client_credentials(client_id, "whatsapp")

            if not credentials:
                return False

            access_token = credentials.get("access_token")

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "typing",
            }

            url = f"{self.api_base_url}/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = await self.http_client.post(
                url,
                json=payload,
                headers=headers,
            )

            return response.status_code in (200, 201)

        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
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
            response = self.supabase.table("client_channels").select(
                "channel_credentials"
            ).eq("client_id", client_id).eq("channel_type", channel).single().execute()

            if response.data:
                return response.data.get("channel_credentials", {})

            logger.warning(f"No credentials found for {client_id} on {channel}")
            return None

        except Exception as e:
            logger.error(f"Error fetching credentials: {e}")
            return None

    async def send_template(
        self,
        phone_number_id: str,
        recipient_phone: str,
        template_name: str,
        template_params: list[str],
        client_id: str,
    ) -> bool:
        """
        Send WhatsApp template message.

        Args:
            phone_number_id: Sender's phone number ID
            recipient_phone: Recipient's phone number
            template_name: Template name
            template_params: Template parameters
            client_id: Client ID

        Returns:
            True if sent successfully
        """
        try:
            credentials = await self._get_client_credentials(client_id, "whatsapp")

            if not credentials:
                return False

            access_token = credentials.get("access_token")

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "es"},
                    "parameters": {"body": {"parameters": template_params}},
                },
            }

            url = f"{self.api_base_url}/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = await self.http_client.post(
                url,
                json=payload,
                headers=headers,
            )

            return response.status_code in (200, 201)

        except Exception as e:
            logger.error(f"Error sending template: {e}")
            return False
