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
import os
import random
from io import BytesIO
from typing import Any, Optional
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

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
        cobros_module: Any = None,
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
            cobros_module: CobrosModule instance for payment approval processing
        """
        self.verify_token = verify_token
        self.app_secret = app_secret
        self.supabase = supabase_client
        self.router = router
        self.normalizer = normalizer
        self.buffer = buffer
        self.memory = memory
        self.cobros_module = cobros_module
        self.api_base_url = "https://graph.facebook.com/v21.0"
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._pending_tasks: dict[str, asyncio.Task] = {}
        self._debounce_delay: float = 10.0

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
            body: Raw request body bytes
            x_hub_signature: X-Hub-Signature-256 header value (sha256=...)

        Returns:
            True if signature is valid or verification is skipped
        """
        if not self.app_secret or self.app_secret in ("", "pendiente", "your_app_secret"):
            logger.warning("meta_app_secret_not_configured_skipping_signature_check")
            return True

        try:
            logger.info(f"verifying_signature: {x_hub_signature[:20] if x_hub_signature else 'missing'}")

            if not x_hub_signature or "=" not in x_hub_signature:
                logger.warning("invalid_x_hub_signature_format", header=x_hub_signature)
                return False

            _, provided_hash = x_hub_signature.split("=", 1)

            expected_hash = hmac.new(
                self.app_secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(provided_hash, expected_hash):
                logger.warning("signature_mismatch")
                return False

            logger.info("webhook_signature_verified")
            return True

        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    async def handle_webhook(
        self,
        payload: dict[str, Any],
        x_hub_signature: Optional[str] = None,
        raw_body: bytes = b"",
    ) -> dict[str, Any]:
        """
        Handle WhatsApp webhook payload.

        Args:
            payload: Webhook payload from Meta
            x_hub_signature: X-Hub-Signature-256 header for verification
            raw_body: Original raw request bytes (required for correct HMAC)

        Returns:
            Response dict
        """
        try:
            if not self.verify_webhook_signature(raw_body, x_hub_signature or ""):
                logger.error("webhook_signature_verification_failed")
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
            waba_id = entry.get("id")  # WABA-level ID, used as fallback
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id")

                if not phone_number_id:
                    logger.warning("Missing phone_number_id in webhook")
                    print("\n❌ DEBUG: Missing phone_number_id in webhook metadata")
                    continue

                print(f"\n📱 DEBUG: Webhook received with phone_number_id = {phone_number_id}, waba_id = {waba_id}")
                logger.info(f"[WEBHOOK_DEBUG] phone_number_id = {phone_number_id}, waba_id = {waba_id}")

                client_id = await self.router.identify_client(
                    phone_number_id,
                    "phone_number_id",
                    waba_id=waba_id,
                )

                if not client_id:
                    logger.warning(f"Could not identify client for phone_number_id={phone_number_id} waba_id={waba_id}")
                    print(f"\n❌ DEBUG: No client found for phone_number_id={phone_number_id} waba_id={waba_id}")
                    continue

                print(f"✅ DEBUG: Client identified = {client_id}")

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
            print(f"\n\n>>> WHATSAPP MESSAGE RECEIVED <<<")
            sender_id = message.get("from", "")
            print(f">>> sender_id={sender_id}, client_id={client_id}")

            logger.info(
                f"Processing WhatsApp message from {sender_id}",
                extra={"client_id": client_id},
            )

            # Handle audio messages: download and transcribe immediately before buffering
            if message.get("type") == "audio":
                media_id = message.get("audio", {}).get("id")
                if media_id:
                    credentials = await self._get_client_credentials(client_id, "whatsapp")
                    access_token = credentials.get("access_token") if credentials else None

                    if not access_token:
                        access_token = os.getenv("META_ACCESS_TOKEN")

                    if access_token:
                        audio_bytes = await self._download_audio(media_id, client_id, access_token)
                        if audio_bytes:
                            transcription = await self._transcribe_audio(audio_bytes, client_id)
                            if transcription:
                                message["transcription"] = transcription
                            else:
                                await self.send_message(
                                    phone_number_id,
                                    sender_id,
                                    "No pude entender el audio. ¿Puedes escribir tu mensaje por favor? 🙏",
                                    client_id,
                                )
                                return
                        else:
                            await self.send_message(
                                phone_number_id,
                                sender_id,
                                "No pude descargar el audio. ¿Puedes intentar de nuevo? 🙏",
                                client_id,
                            )
                            return
                    else:
                        logger.error(f"No access token for audio download, client {client_id}")
                        await self.send_message(
                            phone_number_id,
                            sender_id,
                            "Disculpa, no puedo procesar audios en este momento. 🙏",
                            client_id,
                        )
                        return
                else:
                    logger.warning("Audio message without media_id")
                    return

            # EARLY EXIT: owner approval/rejection commands bypass debounce entirely
            if message.get("type") == "text" and self.cobros_module:
                msg_text = message.get("text", {}).get("body", "").strip()
                is_owner = await self._is_owner(client_id, sender_id)
                if is_owner and msg_text:
                    handled = await self.cobros_module.procesar_respuesta_propietario(
                        client_id=client_id,
                        phone_number_id=phone_number_id,
                        owner_phone=sender_id,
                        text=msg_text,
                    )
                    if handled:
                        logger.info(
                            f"Owner approval/rejection processed for client {client_id}",
                            extra={"client_id": client_id},
                        )
                        return

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

            # Accumulate message in Redis and (re)start the debounce timer.
            # Token is stored in Redis so cancellation works across multiple workers.
            debounce_key = f"{client_id}:{sender_id}"
            await self.buffer.add_inbound_message(
                debounce_key,
                normalized["text"],
                media_url=normalized.get("media_url"),
                media_type=normalized.get("media_type"),
            )

            token = str(uuid4())
            await self.buffer.set_debounce_token(debounce_key, token)

            existing = self._pending_tasks.pop(debounce_key, None)
            if existing and not existing.done():
                existing.cancel()

            task = asyncio.create_task(
                self._debounced_process(client_id, phone_number_id, sender_id, debounce_key, token)
            )
            self._pending_tasks[debounce_key] = task
            print(f">>> debounce task scheduled for {sender_id} (delay={self._debounce_delay}s)")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _debounced_process(
        self,
        client_id: str,
        phone_number_id: str,
        sender_id: str,
        debounce_key: str,
        token: str,
    ) -> None:
        """
        Called after the debounce delay expires.

        Collects all messages accumulated since the last keystroke, combines
        them into a single input, and calls the agent once.
        Uses a Redis token to ensure only one worker processes the batch even
        when multiple uvicorn workers receive messages for the same conversation.
        """
        try:
            await asyncio.sleep(self._debounce_delay)
            self._pending_tasks.pop(debounce_key, None)

            if not await self.buffer.claim_debounce(debounce_key, token):
                print(f">>> debounce superseded for {sender_id}, skipping")
                return

            inbound = await self.buffer.get_and_clear_inbound(debounce_key)
            if not inbound:
                return

            parts = []
            for m in inbound:
                text = m["text"].strip()
                if text and text[-1] not in ".!?¡¿,;:":
                    text += "."
                parts.append(text)
            combined_text = " ".join(parts)
            first_media = next((m for m in inbound if m.get("media_url")), {})
            media_url = first_media.get("media_url")
            media_type = first_media.get("media_type")

            print(f"\n>>> DEBOUNCE FIRED for {sender_id}: {len(inbound)} message(s) combined")

            conversation_id = None
            memory_context: list = []

            if self.memory:
                try:
                    conversation = await self.memory.get_or_create_conversation(
                        client_id,
                        sender_id,
                        "whatsapp",
                        usuario_telefono=sender_id,
                    )
                    conversation_id = conversation["id"]

                    # Fetch history BEFORE saving the current message to avoid duplicating
                    # it in the context (process_message appends it again as the final turn).
                    memory_context = await self.memory.get_context_for_agent(
                        client_id,
                        conversation_id,
                    )

                    await self.memory.save_message(
                        client_id,
                        conversation_id,
                        sender_id,
                        "user",
                        combined_text,
                        "whatsapp",
                        media_url=media_url,
                        media_type=media_type,
                    )
                except Exception as mem_err:
                    logger.warning(
                        f"memory_unavailable_degraded_mode: {mem_err} client_id={client_id} sender_id={sender_id}"
                    )
                    memory_context = []
            else:
                logger.warning(
                    f"memory_not_initialized_degraded_mode client_id={client_id} sender_id={sender_id}"
                )

            print(f"\n>>> CALLING router.route_message for {sender_id}")
            agent_response = await self.router.route_message(
                client_id,
                {
                    "text": combined_text,
                    "sender_id": sender_id,
                    "channel": "whatsapp",
                    "media_url": media_url,
                    "media_type": media_type,
                    "conversation_id": conversation_id,
                },
                memory_context,
            )

            if agent_response.get("escalated"):
                logger.warning(f"Message escalated for {client_id}")
                return

            response_text = agent_response.get("response_text") or ""
            if not response_text.strip():
                logger.warning(
                    f"Agent returned empty response_text for client={client_id} sender={sender_id}; using fallback"
                )
                response_text = "Disculpa, hubo un problema. ¿Puedes repetir tu pregunta?"

            chunks = self._split_response(response_text)
            for i, chunk in enumerate(chunks):
                await self.send_typing_indicator(phone_number_id, sender_id, client_id)
                typing_delay = min(max(len(chunk) * 0.04, 0.8), 3.5) + random.uniform(0.2, 0.6)
                await asyncio.sleep(typing_delay)
                await self.send_message(phone_number_id, sender_id, chunk, client_id)
                if i < len(chunks) - 1:
                    await asyncio.sleep(random.uniform(0.4, 1.0))

            if self.memory and conversation_id:
                try:
                    await self.memory.save_message(
                        client_id,
                        conversation_id,
                        "agent",
                        "agent",
                        response_text,
                        "whatsapp",
                    )
                except Exception as mem_err:
                    logger.warning(
                        f"memory_save_response_failed: {mem_err} client_id={client_id}"
                    )

        except asyncio.CancelledError:
            pass  # A newer message arrived and reset the timer — nothing to do
        except Exception as e:
            logger.error(f"Error in debounced process: {e}", exc_info=True)

    async def _download_audio(
        self,
        media_id: str,
        client_id: str,
        access_token: str,
    ) -> Optional[bytes]:
        """
        Download audio file from Meta Cloud API.

        Args:
            media_id: Media ID from WhatsApp message
            client_id: Client ID
            access_token: Meta API access token

        Returns:
            Audio file bytes or None if download failed
        """
        try:
            url = f"{self.api_base_url}/{media_id}"
            headers = {"Authorization": f"Bearer {access_token}"}

            response = await self.http_client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get audio URL: {response.status_code}")
                return None

            data = response.json()
            media_url = data.get("url")
            if not media_url:
                logger.error("No URL in audio metadata response")
                return None

            audio_response = await self.http_client.get(media_url, headers=headers)
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: {audio_response.status_code}")
                return None

            logger.info(f"Audio downloaded successfully for client {client_id}")
            return audio_response.content

        except Exception as e:
            logger.error(f"Error downloading audio: {e}", exc_info=True)
            return None

    async def _transcribe_audio(
        self,
        audio_bytes: bytes,
        client_id: str,
    ) -> Optional[str]:
        """
        Transcribe audio to text using OpenAI Whisper.

        Args:
            audio_bytes: Audio file bytes
            client_id: Client ID

        Returns:
            Transcribed text or None if transcription failed
        """
        try:
            audio_file = BytesIO(audio_bytes)
            audio_file.name = "audio.ogg"

            response = await self.openai_client.audio.transcriptions.create(
                model=os.getenv("OPENAI_AUDIO_MODEL", "whisper-1"),
                file=audio_file,
                language="es",
            )

            transcription = response.text.strip()
            logger.info(
                f"Audio transcribed successfully for client {client_id}: {len(transcription)} chars"
            )
            return transcription if transcription else None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return None

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

    @staticmethod
    def _split_response(text: str) -> list[str]:
        """Split agent response at paragraph breaks for natural multi-message delivery."""
        max_chunk = 500
        max_chunks = 2
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks: list[str] = []
        for para in paragraphs:
            if len(para) <= max_chunk:
                chunks.append(para)
            else:
                sentences = para.split(". ")
                current = ""
                for sentence in sentences:
                    candidate = current + sentence + ". "
                    if len(candidate) <= max_chunk:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current.rstrip())
                        current = sentence + ". "
                if current:
                    chunks.append(current.rstrip())

        if not chunks:
            return [text]

        # Merge excess chunks beyond max_chunks into the last allowed chunk
        if len(chunks) > max_chunks:
            merged_tail = " ".join(chunks[max_chunks - 1:])
            chunks = chunks[: max_chunks - 1] + [merged_tail]

        return chunks

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
            if not text or not text.strip():
                logger.error(
                    f"send_message called with empty text for client={client_id} recipient={recipient_phone}"
                )
                text = "Disculpa, hubo un problema. ¿Puedes repetir tu pregunta?"

            credentials = await self._get_client_credentials(client_id, "whatsapp")
            access_token = credentials.get("access_token") if credentials else None

            if not access_token:
                access_token = os.getenv("META_ACCESS_TOKEN")

            if not access_token:
                logger.error(f"No WhatsApp access token for client {client_id}")
                return False

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

            logger.info(f"[WA_DEBUG] URL: {url}")
            logger.info(f"[WA_DEBUG] token_prefix: {access_token[:20] if access_token else 'MISSING'}")
            logger.info(f"[WA_DEBUG] payload: {payload}")

            response = await self.http_client.post(
                url,
                json=payload,
                headers=headers,
            )

            logger.info(f"[WA_DEBUG] response_status: {response.status_code} body: {response.text[:200]}")

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
            access_token = credentials.get("access_token") if credentials else None

            if not access_token:
                access_token = os.getenv("META_ACCESS_TOKEN")

            if not access_token:
                return False

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

    async def _is_owner(self, client_id: str, phone: str) -> bool:
        """
        Check if a phone number belongs to the client owner.

        Args:
            client_id: Client ID
            phone: Phone number to check

        Returns:
            True if phone matches owner's whatsapp_dueño
        """
        try:
            resp = (
                self.supabase.table("clientes")
                .select("whatsapp_dueño")
                .eq("id", client_id)
                .single()
                .execute()
            )
            if resp.data:
                return resp.data.get("whatsapp_dueño") == phone
        except Exception as e:
            logger.error(f"Error checking owner: {e}")
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
                "token, phone_number_id, waba_id"
            ).eq("cliente_id", client_id).eq("canal", channel).limit(1).execute()

            if response.data:
                row = response.data[0]
                return {
                    "access_token": row.get("token"),
                    "phone_number_id": row.get("phone_number_id"),
                    "waba_id": row.get("waba_id"),
                }

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
            access_token = credentials.get("access_token") if credentials else None

            if not access_token:
                access_token = os.getenv("META_ACCESS_TOKEN")

            if not access_token:
                return False

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
