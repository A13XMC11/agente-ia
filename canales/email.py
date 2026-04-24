"""
Email channel handler: processes inbound emails from SendGrid.

Handles:
- Inbound email parsing
- Attachment extraction
- Reply routing
"""

import os
from datetime import datetime
from typing import Any, Optional
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from config.modelos import ChannelTypeEnum


logger = structlog.get_logger(__name__)


class EmailHandler:
    """
    Handles inbound emails from SendGrid.

    Processes email parsing webhook, extracts sender, subject, body, attachments.
    """

    def __init__(self):
        """Initialize email handler."""
        self.channel = ChannelTypeEnum.EMAIL
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")

    async def handle_inbound(
        self,
        body: dict[str, Any],
        request: Request,
    ) -> JSONResponse:
        """
        Handle inbound email from SendGrid webhook.

        SendGrid sends parsed email data as form data, not JSON.

        Args:
            body: Parsed request body
            request: FastAPI request

        Returns:
            JSON response
        """
        logger.info("email_webhook_received")

        try:
            # Extract email data from SendGrid webhook
            email_data = await self._parse_sendgrid_webhook(body)

            if not email_data:
                logger.warning("failed_to_parse_email")
                return JSONResponse(status_code=400, content={"error": "Invalid email"})

            # Process email asynchronously
            await self._process_email(email_data)

            return JSONResponse(status_code=200, content={"result": "accepted"})

        except Exception as e:
            logger.error("email_handling_error", error=str(e), exc_info=True)
            return JSONResponse(status_code=500, content={"error": str(e)})

    async def _parse_sendgrid_webhook(
        self,
        body: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Parse SendGrid inbound email webhook.

        SendGrid sends via POST with form data (not JSON).

        Args:
            body: Parsed form data

        Returns:
            Parsed email dict
        """
        try:
            sender = body.get("from", "")
            to = body.get("to", "")
            subject = body.get("subject", "")
            text = body.get("text", "")
            html = body.get("html", "")
            message_id = body.get("message-id", "")

            # Parse attachments
            attachments = []
            for key in body:
                if key.startswith("attachment"):
                    # SendGrid puts attachments as files in multipart
                    # (we'd need to handle multipart/form-data differently)
                    pass

            if not sender or not subject:
                return None

            return {
                "sender": sender,
                "to": to,
                "subject": subject,
                "text": text,
                "html": html,
                "message_id": message_id,
                "attachments": attachments,
                "received_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("email_parsing_error", error=str(e), exc_info=True)
            return None

    async def _process_email(self, email_data: dict[str, Any]) -> None:
        """
        Process parsed email.

        Args:
            email_data: Parsed email dict
        """
        try:
            logger.info(
                "processing_email",
                sender=email_data.get("sender"),
                subject=email_data.get("subject"),
            )

            # TODO: Route to message processor
            # - Identify client from "to" address
            # - Normalize message using MessageNormalizer
            # - Create/fetch conversation
            # - Call agent
            # - Send email response via SendGrid

        except Exception as e:
            logger.error(
                "email_processing_error",
                error=str(e),
                exc_info=True,
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send email via SendGrid.

        Args:
            to_email: Recipient email
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)

        Returns:
            Message ID if sent successfully
        """
        # TODO: Implement SendGrid API call
        # Use SendGrid Python SDK to send email

        logger.info(
            "sending_email",
            to=to_email,
            subject=subject,
        )

        return None


# Global instance
email_router = EmailHandler()
