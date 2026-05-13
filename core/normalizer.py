"""
Normalizer module: unifies message format across all channels.

Converts channel-specific payloads (Meta, Email, etc) to internal schema.
Extracts: text, media, sender_id, channel_type, timestamp, metadata.
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MessageNormalizer:
    """Normalizes messages from all channels to internal format."""

    # Internal message schema keys
    REQUIRED_FIELDS = {"text", "sender_id", "channel", "timestamp"}
    OPTIONAL_FIELDS = {"media_url", "media_type", "message_type", "metadata"}

    async def normalize(
        self,
        raw_message: dict[str, Any],
        channel_type: str,
    ) -> Optional[dict[str, Any]]:
        """
        Normalize channel-specific message to internal format.

        Args:
            raw_message: Channel-specific payload
            channel_type: Channel (whatsapp, instagram, facebook, email, telegram)

        Returns:
            Normalized message or None if invalid
        """
        try:
            if channel_type == "whatsapp":
                return await self._normalize_whatsapp(raw_message)
            elif channel_type == "instagram":
                return await self._normalize_instagram(raw_message)
            elif channel_type == "facebook":
                return await self._normalize_facebook(raw_message)
            elif channel_type == "email":
                return await self._normalize_email(raw_message)
            else:
                logger.warning(f"Unknown channel type: {channel_type}")
                return None

        except Exception as e:
            logger.error(
                f"Error normalizing message from {channel_type}: {e}",
                exc_info=True,
            )
            return None

    async def _normalize_whatsapp(
        self,
        message: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Normalize WhatsApp Cloud API message.

        Meta Cloud API format:
        {
          "entry": [{
            "changes": [{
              "value": {
                "messages": [{
                  "from": "1234567890",
                  "id": "msg_id",
                  "timestamp": "1234567890",
                  "type": "text|image|document|video|audio",
                  "text": {"body": "..."},
                  "image": {"mime_type": "...", "id": "..."},
                  ...
                }]
              }
            }]
          }]
        }
        """
        try:
            # Extract message from nested structure
            entry = message.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                logger.warning("No messages in WhatsApp payload")
                return None

            msg = messages[0]
            sender_id = msg.get("from", "")
            timestamp = msg.get("timestamp", "")
            message_type = msg.get("type", "text")

            if not sender_id:
                logger.warning("Missing sender_id in WhatsApp message")
                return None

            # Extract text based on type
            text = ""
            media_url = None
            media_type = None

            if message_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif message_type == "image":
                text = msg.get("image", {}).get("caption", "")
                media_type = "image"
                media_url = msg.get("image", {}).get("id")
            elif message_type == "document":
                text = msg.get("document", {}).get("caption", "")
                media_type = "document"
                media_url = msg.get("document", {}).get("id")
            elif message_type == "video":
                text = msg.get("video", {}).get("caption", "")
                media_type = "video"
                media_url = msg.get("video", {}).get("id")
            elif message_type == "audio":
                media_type = "audio"
                media_url = msg.get("audio", {}).get("id")
                text = msg.get("transcription", "")
            elif message_type == "location":
                location = msg.get("location", {})
                text = f"Ubicación: {location.get('latitude')}, {location.get('longitude')}"
                media_type = "location"
            else:
                text = f"[{message_type}]"

            metadata = {
                "message_id": msg.get("id"),
                "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            }

            # Add transcription metadata if audio was transcribed
            if message_type == "audio" and msg.get("transcription"):
                metadata["tipo_original"] = "audio"
                metadata["transcription_method"] = "whisper"

            return {
                "text": text,
                "sender_id": sender_id,
                "channel": "whatsapp",
                "timestamp": timestamp,
                "message_type": message_type,
                "media_url": media_url,
                "media_type": media_type,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error normalizing WhatsApp message: {e}")
            return None

    async def _normalize_instagram(
        self,
        message: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Normalize Instagram Graph API message.

        Similar to WhatsApp (both use Meta Cloud API).
        """
        try:
            entry = message.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                logger.warning("No messages in Instagram payload")
                return None

            msg = messages[0]
            sender_id = msg.get("from", "")
            timestamp = msg.get("timestamp", "")
            message_type = msg.get("type", "text")

            if not sender_id:
                logger.warning("Missing sender_id in Instagram message")
                return None

            text = ""
            media_url = None
            media_type = None

            if message_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif message_type == "image":
                text = msg.get("image", {}).get("caption", "")
                media_type = "image"
                media_url = msg.get("image", {}).get("id")
            elif message_type == "video":
                text = msg.get("video", {}).get("caption", "")
                media_type = "video"
                media_url = msg.get("video", {}).get("id")
            elif message_type == "story_mention":
                text = "[Story mention]"
            else:
                text = f"[{message_type}]"

            return {
                "text": text,
                "sender_id": sender_id,
                "channel": "instagram",
                "timestamp": timestamp,
                "message_type": message_type,
                "media_url": media_url,
                "media_type": media_type,
                "metadata": {
                    "message_id": msg.get("id"),
                    "page_id": value.get("metadata", {}).get("page_id"),
                },
            }

        except Exception as e:
            logger.error(f"Error normalizing Instagram message: {e}")
            return None

    async def _normalize_facebook(
        self,
        message: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Normalize Facebook Graph API message.

        Similar to Instagram/WhatsApp (all use Meta APIs).
        """
        try:
            entry = message.get("entry", [{}])[0]
            messaging = entry.get("messaging", [])

            if not messaging:
                logger.warning("No messaging in Facebook payload")
                return None

            msg = messaging[0]
            sender_id = msg.get("sender", {}).get("id", "")
            timestamp = msg.get("timestamp", "")
            message_data = msg.get("message", {})

            if not sender_id:
                logger.warning("Missing sender_id in Facebook message")
                return None

            text = message_data.get("text", "")
            media_url = None
            media_type = None

            # Check for attachments (images, videos, files)
            attachments = message_data.get("attachments", [])
            if attachments:
                attachment = attachments[0]
                payload = attachment.get("payload", {})
                attachment_type = attachment.get("type", "")

                if attachment_type == "image":
                    media_type = "image"
                    media_url = payload.get("url")
                elif attachment_type == "video":
                    media_type = "video"
                    media_url = payload.get("url")
                elif attachment_type == "file":
                    media_type = "document"
                    media_url = payload.get("url")
                elif attachment_type == "location":
                    coords = payload.get("coordinates", {})
                    text = f"Ubicación: {coords.get('lat')}, {coords.get('long')}"
                    media_type = "location"

            # Fallback if no text
            if not text and media_type:
                text = f"[{media_type}]"

            return {
                "text": text,
                "sender_id": sender_id,
                "channel": "facebook",
                "timestamp": timestamp,
                "message_type": "attachment" if attachments else "text",
                "media_url": media_url,
                "media_type": media_type,
                "metadata": {
                    "message_id": message_data.get("mid"),
                    "page_id": msg.get("recipient", {}).get("id"),
                },
            }

        except Exception as e:
            logger.error(f"Error normalizing Facebook message: {e}")
            return None

    async def _normalize_email(
        self,
        message: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Normalize SendGrid Inbound Parse webhook.

        SendGrid Inbound Parse format:
        {
          "from": "sender@example.com",
          "to": "myservice@example.com",
          "subject": "...",
          "text": "...",
          "html": "...",
          "attachments": "...",
          "email": "sender@example.com",
          "charsets": "...",
          "SPF": "..."
        }
        """
        try:
            sender_email = message.get("from", "")
            subject = message.get("subject", "")
            text = message.get("text", "")

            if not sender_email:
                logger.warning("Missing from email in message")
                return None

            # Use email as sender_id
            sender_id = sender_email

            # Combine subject and text for full message
            full_text = text
            if subject:
                full_text = f"{subject}\n{text}" if text else subject

            # Check for attachments
            attachments = message.get("attachments", "")
            media_url = None
            media_type = None

            if attachments:
                # attachments is a string count; actual files would be in raw POST
                # For now, we note that attachments exist
                media_type = "attachment"
                full_text = f"{full_text}\n[Tiene {attachments} archivo(s) adjunto(s)]"

            return {
                "text": full_text,
                "sender_id": sender_id,
                "channel": "email",
                "timestamp": message.get("timestamp", ""),
                "message_type": "email",
                "media_url": media_url,
                "media_type": media_type,
                "metadata": {
                    "subject": subject,
                    "email": sender_email,
                    "to": message.get("to", ""),
                    "html": message.get("html"),
                    "attachments_count": attachments,
                },
            }

        except Exception as e:
            logger.error(f"Error normalizing email message: {e}")
            return None

    def validate(self, normalized: dict[str, Any]) -> bool:
        """
        Validate normalized message has all required fields.

        Args:
            normalized: Normalized message dict

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(normalized, dict):
            return False

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in normalized or normalized[field] is None:
                logger.warning(f"Missing required field: {field}")
                return False

        # Validate has either text or media (allows image-only messages for receipt uploads)
        has_text = bool(normalized.get("text", "").strip())
        has_media = bool(normalized.get("media_url"))
        if not has_text and not has_media:
            logger.warning("Message has neither text nor media")
            return False

        # Validate channel is known
        valid_channels = {"whatsapp", "instagram", "facebook", "email"}
        if normalized.get("channel") not in valid_channels:
            logger.warning(f"Invalid channel: {normalized.get('channel')}")
            return False

        return True

    async def normalize_and_validate(
        self,
        raw_message: dict[str, Any],
        channel_type: str,
    ) -> Optional[dict[str, Any]]:
        """
        Normalize message and validate result.

        Args:
            raw_message: Channel-specific payload
            channel_type: Channel type

        Returns:
            Validated normalized message or None
        """
        normalized = await self.normalize(raw_message, channel_type)

        if not normalized:
            return None

        if not self.validate(normalized):
            logger.warning(f"Validation failed for {channel_type} message")
            return None

        logger.info(
            f"Message normalized successfully",
            extra={
                "channel": channel_type,
                "sender_id": normalized.get("sender_id"),
                "message_type": normalized.get("message_type"),
            },
        )

        return normalized
