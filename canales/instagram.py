"""
Instagram channel handler: processes messages from Meta Graph API.

Handles:
- Inbound message webhooks
- Direct message routing
"""

import os
from typing import Any, Optional
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from config.modelos import ChannelTypeEnum


logger = structlog.get_logger(__name__)


class InstagramHandler:
    """Handles Instagram messages from Meta Graph API."""

    def __init__(self):
        """Initialize Instagram handler."""
        self.channel = ChannelTypeEnum.INSTAGRAM
        self.meta_api_version = os.getenv("META_API_VERSION", "v18.0")

    async def handle_webhook(
        self,
        body: dict[str, Any],
        request: Request,
    ) -> JSONResponse:
        """
        Handle Instagram webhook.

        Args:
            body: Request JSON body
            request: FastAPI request object

        Returns:
            JSON response
        """
        logger.info("instagram_webhook_received")

        # TODO: Process Instagram messages
        return JSONResponse(status_code=200, content={"result": "accepted"})

    async def send_message(
        self,
        page_id: str,
        recipient_id: str,
        message_text: str,
    ) -> Optional[str]:
        """
        Send message via Instagram.

        Args:
            page_id: Instagram page ID
            recipient_id: Recipient user ID
            message_text: Message content

        Returns:
            Message ID if sent
        """
        logger.info(
            "sending_instagram_message",
            page_id=page_id,
            recipient_id=recipient_id,
        )
        return None


instagram_router = InstagramHandler()
