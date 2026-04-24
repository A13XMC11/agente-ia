"""
Message normalizer: converts channel-specific formats to unified internal schema.

Handles: WhatsApp, Instagram, Facebook, Email
Extracts: text, media, sender_id, timestamp, attachments
"""

import json
from datetime import datetime
from typing import Any, Optional
import structlog

from config.modelos import ChannelTypeEnum, WebhookEvent


logger = structlog.get_logger(__name__)


class MessageNormalizer:
    """
    Converts messages from different channels into a unified format.

    Each channel has different payload structures; this class abstracts them away.
    """

    @staticmethod
    def normalize_whatsapp(webhook_data: dict[str, Any]) -> Optional[WebhookEvent]:
        """
        Normalize WhatsApp message from Meta Cloud API.

        WhatsApp payload structure:
        {
            "entry": [{
                "id": "phone_number_id",
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "id": "msg_id",
                            "timestamp": "1234567890",
                            "type": "text|image|document|etc",
                            "text": {"body": "message text"},
                            "image": {"mime_type": "...", "sha256": "...", "id": "..."},
                            ...
                        }],
                        "statuses": [...],
                        "contacts": [{...}]
                    }
                }]
            }]
        }
        """
        try:
            entries = webhook_data.get("entry", [])
            if not entries:
                return None

            entry = entries[0]
            changes = entry.get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])

            if not messages:
                # Could be delivery confirmation or status update
                statuses = value.get("statuses", [])
                if statuses:
                    status = statuses[0]
                    return WebhookEvent(
                        channel=ChannelTypeEnum.WHATSAPP,
                        event_type="status_update",
                        sender_id=value.get("metadata", {}).get("phone_number_id", ""),
                        message_id=status.get("id"),
                        timestamp=datetime.fromtimestamp(int(status.get("timestamp", 0))),
                        raw_data=webhook_data,
                    )
                return None

            message = messages[0]
            sender_id = message.get("from")
            message_id = message.get("id")
            timestamp = datetime.fromtimestamp(int(message.get("timestamp", 0)))
            message_type = message.get("type")

            # Extract message content based on type
            message_text: Optional[str] = None
            media_url: Optional[str] = None
            media_type: Optional[str] = None

            if message_type == "text":
                message_text = message.get("text", {}).get("body", "")

            elif message_type == "image":
                media_type = "image"
                media_data = message.get("image", {})
                media_url = media_data.get("id")  # Image ID from Meta
                message_text = media_data.get("caption", "")

            elif message_type == "video":
                media_type = "video"
                media_data = message.get("video", {})
                media_url = media_data.get("id")
                message_text = media_data.get("caption", "")

            elif message_type == "document":
                media_type = "document"
                media_data = message.get("document", {})
                media_url = media_data.get("id")
                message_text = media_data.get("caption", "")

            elif message_type == "location":
                media_type = "location"
                location = message.get("location", {})
                message_text = f"Location: {location.get('latitude')},{location.get('longitude')}"

            elif message_type == "button":
                button_data = message.get("button", {})
                message_text = button_data.get("text", "")

            elif message_type == "interactive":
                interactive = message.get("interactive", {})
                if "button_reply" in interactive:
                    message_text = interactive["button_reply"].get("title", "")
                elif "list_reply" in interactive:
                    message_text = interactive["list_reply"].get("title", "")

            return WebhookEvent(
                channel=ChannelTypeEnum.WHATSAPP,
                event_type="message",
                sender_id=sender_id,
                message_id=message_id,
                message_text=message_text or "",
                media_url=media_url,
                media_type=media_type,
                timestamp=timestamp,
                raw_data=webhook_data,
            )

        except Exception as e:
            logger.error("whatsapp_normalization_error", error=str(e), exc_info=True)
            return None

    @staticmethod
    def normalize_instagram(webhook_data: dict[str, Any]) -> Optional[WebhookEvent]:
        """
        Normalize Instagram message from Meta Graph API.

        Similar to WhatsApp but uses different field names.
        """
        try:
            entries = webhook_data.get("entry", [])
            if not entries:
                return None

            entry = entries[0]
            changes = entry.get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            message = messages[0]
            sender_id = message.get("from", {}).get("id", "")
            message_id = message.get("id")
            timestamp = datetime.fromtimestamp(int(message.get("timestamp", 0)))

            message_text = ""
            media_url: Optional[str] = None
            media_type: Optional[str] = None

            if "text" in message:
                message_text = message["text"].get("body", "")

            elif "image" in message:
                media_type = "image"
                media_url = message["image"].get("id")

            elif "video" in message:
                media_type = "video"
                media_url = message["video"].get("id")

            return WebhookEvent(
                channel=ChannelTypeEnum.INSTAGRAM,
                event_type="message",
                sender_id=sender_id,
                message_id=message_id,
                message_text=message_text,
                media_url=media_url,
                media_type=media_type,
                timestamp=timestamp,
                raw_data=webhook_data,
            )

        except Exception as e:
            logger.error("instagram_normalization_error", error=str(e), exc_info=True)
            return None

    @staticmethod
    def normalize_facebook(webhook_data: dict[str, Any]) -> Optional[WebhookEvent]:
        """
        Normalize Facebook Messenger message from Meta Graph API.
        """
        try:
            entries = webhook_data.get("entry", [])
            if not entries:
                return None

            entry = entries[0]
            messaging = entry.get("messaging", [])

            if not messaging:
                return None

            event = messaging[0]
            sender_id = event.get("sender", {}).get("id", "")
            timestamp = datetime.fromtimestamp(int(event.get("timestamp", 0)) / 1000)

            message_text = ""
            media_url: Optional[str] = None
            media_type: Optional[str] = None
            message_id: Optional[str] = None

            if "message" in event:
                msg = event["message"]
                message_id = msg.get("mid")
                message_text = msg.get("text", "")

                if "attachments" in msg:
                    attachment = msg["attachments"][0]
                    attachment_type = attachment.get("type")  # image, video, file, etc.

                    if attachment_type in ["image", "video", "file"]:
                        media_type = attachment_type
                        payload = attachment.get("payload", {})
                        media_url = payload.get("url")

            return WebhookEvent(
                channel=ChannelTypeEnum.FACEBOOK,
                event_type="message",
                sender_id=sender_id,
                message_id=message_id,
                message_text=message_text,
                media_url=media_url,
                media_type=media_type,
                timestamp=timestamp,
                raw_data=webhook_data,
            )

        except Exception as e:
            logger.error("facebook_normalization_error", error=str(e), exc_info=True)
            return None

    @staticmethod
    def normalize_email(
        sender_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[list[dict[str, Any]]] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> WebhookEvent:
        """
        Normalize email from SendGrid inbound parsing.

        Emails arrive as separate fields, not nested JSON.
        """
        if not timestamp:
            timestamp = datetime.utcnow()

        message_text = f"Subject: {subject}\n\n{body_text}"

        # If there are attachments, note them
        media_url: Optional[str] = None
        media_type: Optional[str] = None

        if attachments and len(attachments) > 0:
            # For simplicity, just note the first attachment
            # In production, you'd handle multiple attachments
            first_attachment = attachments[0]
            media_type = "attachment"
            media_url = first_attachment.get("url") or first_attachment.get("filename")

        return WebhookEvent(
            channel=ChannelTypeEnum.EMAIL,
            event_type="message",
            sender_id=sender_email,
            message_id=message_id,
            message_text=message_text,
            media_url=media_url,
            media_type=media_type,
            timestamp=timestamp,
            raw_data={
                "sender": sender_email,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,
                "attachments": attachments or [],
            },
        )

    @classmethod
    def normalize(
        cls,
        channel: ChannelTypeEnum,
        webhook_data: dict[str, Any],
    ) -> Optional[WebhookEvent]:
        """
        Main normalization entry point.

        Routes to correct channel-specific normalizer.
        """
        logger.info("normalizing_message", channel=channel.value)

        if channel == ChannelTypeEnum.WHATSAPP:
            return cls.normalize_whatsapp(webhook_data)
        elif channel == ChannelTypeEnum.INSTAGRAM:
            return cls.normalize_instagram(webhook_data)
        elif channel == ChannelTypeEnum.FACEBOOK:
            return cls.normalize_facebook(webhook_data)
        else:
            logger.error("unknown_channel", channel=channel.value)
            return None
