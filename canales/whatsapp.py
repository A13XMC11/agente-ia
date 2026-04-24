"""
WhatsApp channel handler: processes messages from Meta Cloud API.

Handles:
- Inbound message webhooks
- Delivery confirmations
- Message status updates
- Webhook signature validation
"""

import os
import hmac
import hashlib
from typing import Any, Optional
import structlog
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from config.modelos import ChannelTypeEnum, WebhookEvent
from seguridad.validator import validate_webhook_signature


logger = structlog.get_logger(__name__)


class WhatsAppHandler:
    """
    Handles WhatsApp messages from Meta Cloud API.

    Validates webhook signatures, processes events, routes to agent.
    """

    def __init__(self):
        """Initialize WhatsApp handler."""
        self.channel = ChannelTypeEnum.WHATSAPP
        self.meta_verify_token = os.getenv("META_VERIFY_TOKEN", "")
        self.meta_api_version = os.getenv("META_API_VERSION", "v18.0")

    async def handle_webhook(
        self,
        body: dict[str, Any],
        request: Request,
    ) -> JSONResponse:
        """
        Main webhook handler for WhatsApp events.

        Validates signature, processes event, returns 200 to Meta immediately.

        Args:
            body: Request JSON body
            request: FastAPI request object

        Returns:
            JSON response (immediately returned to Meta)
        """
        logger.info("whatsapp_webhook_received")

        # Validate signature (if not in development)
        skip_validation = os.getenv("SKIP_WEBHOOK_VALIDATION", "false").lower() == "true"
        if not skip_validation:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not self._validate_signature(body, signature):
                logger.warning("invalid_webhook_signature")
                raise HTTPException(status_code=403, detail="Invalid signature")

        # Return 200 to Meta immediately (process async)
        asyncio_task = self._process_webhook(body)

        return JSONResponse(
            status_code=200,
            content={"result": "accepted"},
        )

    async def _process_webhook(self, body: dict[str, Any]) -> None:
        """
        Process webhook asynchronously (don't block Meta timeout).

        Args:
            body: Request JSON body
        """
        try:
            entries = body.get("entry", [])
            for entry in entries:
                await self._process_entry(entry)
        except Exception as e:
            logger.error("webhook_processing_error", error=str(e), exc_info=True)

    async def _process_entry(self, entry: dict[str, Any]) -> None:
        """
        Process a single entry (webhook may have multiple).

        Args:
            entry: Entry dict from webhook
        """
        try:
            phone_number_id = entry.get("id")
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})

                # Handle messages
                messages = value.get("messages", [])
                for message in messages:
                    await self._handle_message(phone_number_id, message, value)

                # Handle delivery/read status
                statuses = value.get("statuses", [])
                for status in statuses:
                    await self._handle_status(phone_number_id, status)

        except Exception as e:
            logger.error("entry_processing_error", error=str(e), exc_info=True)

    async def _handle_message(
        self,
        phone_number_id: str,
        message: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """
        Handle incoming message.

        Args:
            phone_number_id: Phone number ID receiving the message
            message: Message dict from Meta
            metadata: Metadata including contacts info
        """
        try:
            sender_id = message.get("from")
            message_id = message.get("id")
            timestamp = int(message.get("timestamp", 0))

            logger.info(
                "whatsapp_message_received",
                phone_number_id=phone_number_id,
                sender_id=sender_id,
                message_id=message_id,
            )

            # TODO: Route to message processor
            # - Normalize message
            # - Identify client
            # - Fetch conversation
            # - Call agent
            # - Send response via WhatsApp API

        except Exception as e:
            logger.error(
                "message_handling_error",
                error=str(e),
                exc_info=True,
            )

    async def _handle_status(
        self,
        phone_number_id: str,
        status: dict[str, Any],
    ) -> None:
        """
        Handle message status update (delivered, read, failed).

        Args:
            phone_number_id: Phone number ID
            status: Status dict from Meta
        """
        try:
            message_id = status.get("id")
            status_type = status.get("status")  # sent, delivered, read, failed

            logger.info(
                "whatsapp_status_update",
                message_id=message_id,
                status=status_type,
            )

            # TODO: Update message status in database

        except Exception as e:
            logger.error(
                "status_handling_error",
                error=str(e),
                exc_info=True,
            )

    def _validate_signature(self, body: dict[str, Any], signature: str) -> bool:
        """
        Validate webhook signature from Meta.

        Meta sends: X-Hub-Signature-256: sha256=<hex_digest>

        Args:
            body: Request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        try:
            import json

            body_string = json.dumps(body, separators=(",", ":"), sort_keys=True)
            secret = os.getenv("META_ACCESS_TOKEN", "").encode()

            computed_hash = hmac.new(
                secret,
                body_string.encode(),
                hashlib.sha256,
            ).hexdigest()

            expected_signature = f"sha256={computed_hash}"

            # Constant-time comparison
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error("signature_validation_error", error=str(e), exc_info=True)
            return False

    async def send_message(
        self,
        phone_number_id: str,
        recipient_id: str,
        message_text: str,
        message_type: str = "text",
    ) -> Optional[str]:
        """
        Send message via WhatsApp API.

        Args:
            phone_number_id: Sender phone number ID
            recipient_id: Recipient phone number
            message_text: Message content
            message_type: Type of message (text, image, document, etc.)

        Returns:
            Message ID if sent successfully, None otherwise
        """
        # TODO: Implement WhatsApp API call
        # POST to /v{api_version}/{phone_number_id}/messages
        # with message payload

        logger.info(
            "sending_whatsapp_message",
            phone_number_id=phone_number_id,
            recipient_id=recipient_id,
        )

        return None


# Global instance
whatsapp_router = WhatsAppHandler()


# Handle imports that might fail
try:
    import asyncio
except ImportError:
    asyncio = None  # type: ignore
