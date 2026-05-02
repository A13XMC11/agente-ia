"""
Email channel: SendGrid inbound/outbound handler.

Handles inbound email parsing via webhook.
Sends outgoing emails via SendGrid API.
"""

import base64
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class EmailHandler:
    """Handles email messages via SendGrid."""

    def __init__(
        self,
        sendgrid_api_key: str,
        supabase_client: Any,
        router: Any,
        normalizer: Any,
        buffer: Any,
        memory: Any,
    ):
        """
        Initialize email handler.

        Args:
            sendgrid_api_key: SendGrid API key
            supabase_client: Supabase client for credentials
            router: MessageRouter instance
            normalizer: MessageNormalizer instance
            buffer: MessageBuffer instance
            memory: MemoryManager instance
        """
        self.sendgrid_api_key = sendgrid_api_key
        self.supabase = supabase_client
        self.router = router
        self.normalizer = normalizer
        self.buffer = buffer
        self.memory = memory
        self.sendgrid_api_url = "https://api.sendgrid.com/v3/mail/send"
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    async def handle_webhook(
        self,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle SendGrid inbound email webhook.

        SendGrid sends parsed email data as form data.

        Args:
            body: Parsed form data from SendGrid

        Returns:
            Response dict
        """
        try:
            logger.info("Email webhook received")

            email_data = await self._parse_sendgrid_webhook(body)

            if not email_data:
                logger.warning("Failed to parse email")
                return {"error": "Invalid email"}

            await self._process_email(email_data)

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return {"error": str(e)}

    async def _parse_sendgrid_webhook(
        self,
        body: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Parse SendGrid inbound email webhook.

        Args:
            body: Parsed form data from SendGrid

        Returns:
            Parsed email dict or None
        """
        try:
            sender = body.get("from", "")
            to = body.get("to", "")
            subject = body.get("subject", "")
            text = body.get("text", "")
            html = body.get("html", "")
            message_id = body.get("message-id", "")

            # Parse attachments (SendGrid sends as "attachmentX" fields)
            attachments = []
            for i in range(1, 10):  # Support up to 10 attachments
                attachment_key = f"attachment{i}" if i > 1 else "attachment"
                if attachment_key in body:
                    # Note: actual file data would be in file uploads
                    attachments.append({
                        "filename": body.get(f"{attachment_key}-filename", ""),
                    })

            if not sender:
                logger.warning("Missing sender in email")
                return None

            return {
                "from": sender,
                "to": to,
                "subject": subject,
                "text": text,
                "html": html,
                "message_id": message_id,
                "attachments": attachments,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None

    async def _process_email(self, email_data: dict[str, Any]) -> None:
        """
        Process parsed email.

        Args:
            email_data: Parsed email dict
        """
        try:
            sender_email = email_data.get("from", "")
            to_email = email_data.get("to", "")
            subject = email_data.get("subject", "")
            text = email_data.get("text", "")
            timestamp = email_data.get("timestamp", "")

            logger.info(
                f"Processing email from {sender_email}",
                extra={"subject": subject},
            )

            # Identify client from "to" address
            client_id = await self.router.identify_client(
                sender_email,
                "sender_email",
            )

            if not client_id:
                logger.warning(f"Could not identify client for {sender_email}")
                return

            # Normalize message
            normalized = await self.normalizer.normalize_and_validate(
                {
                    "from": sender_email,
                    "to": to_email,
                    "subject": subject,
                    "text": text,
                    "html": email_data.get("html"),
                    "attachments": str(len(email_data.get("attachments", []))),
                    "timestamp": timestamp,
                },
                "email",
            )

            if not normalized:
                logger.warning("Failed to normalize email")
                return

            # Create/fetch conversation
            conversation = await self.memory.get_or_create_conversation(
                client_id,
                sender_email,
                "email",
            )

            # Save message
            await self.memory.save_message(
                client_id,
                conversation["id"],
                sender_email,
                "user",
                normalized["text"],
                "email",
                media_url=normalized.get("media_url"),
                media_type=normalized.get("media_type"),
            )

            # Get context for agent
            memory_context = await self.memory.get_context_for_agent(
                client_id,
                conversation["id"],
            )

            # Route to agent
            agent_response = await self.router.route_message(
                client_id,
                {
                    "text": normalized["text"],
                    "sender_id": sender_email,
                    "channel": "email",
                    "media_url": normalized.get("media_url"),
                    "media_type": normalized.get("media_type"),
                },
                memory_context,
            )

            if agent_response.get("escalated"):
                logger.warning(f"Email escalated for {client_id}")
                return

            response_text = agent_response.get("response_text", "")
            await self.send_email(
                sender_email,
                f"Re: {subject}",
                response_text,
                client_id,
            )

            # Save agent response
            await self.memory.save_message(
                client_id,
                conversation["id"],
                "agent",
                "agent",
                response_text,
                "email",
            )

        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        client_id: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send email via SendGrid API.

        Args:
            to_email: Recipient email
            subject: Email subject
            body_text: Plain text body
            client_id: Client ID
            body_html: Optional HTML body
            from_email: Optional sender email (defaults to client's email)

        Returns:
            True if sent successfully
        """
        try:
            # Get client's email address if not provided
            if not from_email:
                from_email = await self._get_client_email(client_id)

            if not from_email:
                logger.error(f"No email address for client {client_id}")
                return False

            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}],
                        "subject": subject,
                    }
                ],
                "from": {
                    "email": from_email,
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": body_text,
                    }
                ],
            }

            # Add HTML content if provided
            if body_html:
                payload["content"].append({
                    "type": "text/html",
                    "value": body_html,
                })

            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json",
            }

            response = await self.http_client.post(
                self.sendgrid_api_url,
                json=payload,
                headers=headers,
            )

            if response.status_code in (200, 201, 202):
                logger.info(
                    f"Email sent to {to_email}",
                    extra={"client_id": client_id},
                )
                return True
            else:
                logger.error(
                    f"Failed to send email: {response.status_code} {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return False

    async def _get_client_email(self, client_id: str) -> Optional[str]:
        """
        Get client's email address from Supabase.

        Args:
            client_id: Client ID

        Returns:
            Email address or None
        """
        try:
            response = self.supabase.table("clientes").select(
                "email"
            ).eq("id", client_id).single().execute()

            if response.data:
                return response.data.get("email")

            logger.warning(f"No email found for client {client_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching client email: {e}")
            return None
