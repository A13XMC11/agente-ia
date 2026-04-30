"""
Webhook validation: verify signatures from Meta and SendGrid.

Uses HMAC-SHA256 to validate webhook authenticity.
"""

import hmac
import hashlib
import html
import json
from typing import Any
from urllib.parse import parse_qsl
import structlog


logger = structlog.get_logger(__name__)


class WebhookValidator:
    """Validates webhook signatures from Meta and SendGrid."""

    def __init__(self):
        """Initialize webhook validator."""
        pass

    def validate_meta_signature(
        self,
        payload: bytes,
        signature: str,
        app_secret: str,
    ) -> bool:
        """Validate Meta webhook signature (WhatsApp, Instagram, Facebook)."""
        return validate_webhook_signature(payload, signature, app_secret, "sha256")

    def validate_sendgrid_signature(
        self,
        payload: bytes,
        signature: str,
        api_key: str,
    ) -> bool:
        """Validate SendGrid webhook signature."""
        return validate_webhook_signature(payload, signature, api_key, "sha256")

    def detect_injection(self, text: str) -> bool:
        """Detect prompt injection attempts."""
        return detect_prompt_injection(text)


def validate_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Validate webhook signature.

    Args:
        payload: Raw request body bytes
        signature: Signature header value (e.g., "sha256=abc123...")
        secret: Shared secret key
        algorithm: Hash algorithm (default: sha256)

    Returns:
        True if signature is valid
    """
    try:
        if algorithm == "sha256":
            expected = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            expected_sig = f"{algorithm}={expected}"

            # Constant-time comparison
            return hmac.compare_digest(signature, expected_sig)

        else:
            logger.error("unsupported_algorithm", algorithm=algorithm)
            return False

    except Exception as e:
        logger.error(
            "signature_validation_error",
            error=str(e),
            exc_info=True,
        )
        return False


def detect_prompt_injection(text: str) -> bool:
    """
    Detect potential prompt injection attempts.

    Looks for common prompt injection patterns.

    Args:
        text: User input to check

    Returns:
        True if injection attempt detected
    """
    injection_patterns = [
        "system:",
        "ignore previous",
        "forget previous",
        "disregard",
        "override",
        "administrator",
        "root access",
        "break character",
        "roleplay",
        "prompt:",
    ]

    text_lower = text.lower()

    for pattern in injection_patterns:
        if pattern in text_lower:
            logger.warning("prompt_injection_detected", pattern=pattern)
            return True

    return False


def validate_email(email: str) -> bool:
    """
    Simple email validation.

    Args:
        email: Email address

    Returns:
        True if valid email format
    """
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str, country_code: str = "EC") -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number
        country_code: ISO country code (default: EC for Ecuador)

    Returns:
        True if valid phone format
    """
    try:
        import phonenumbers

        parsed = phonenumbers.parse(phone, country_code)
        return phonenumbers.is_valid_number(parsed)

    except Exception as e:
        logger.error("phone_validation_error", error=str(e))
        return False


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML to prevent XSS.

    Uses html.escape() from stdlib for safe conversion of HTML entities.
    This prevents script injection by converting special characters.

    Args:
        html_content: HTML string

    Returns:
        Escaped HTML safe for rendering as plain text
    """
    return html.escape(html_content)


def validate_twilio_signature(
    payload: str,
    signature: str,
    auth_token: str,
    url: str,
) -> bool:
    """
    Validate Twilio webhook signature.

    Twilio signs requests with HMAC-SHA1 of the URL + sorted POST params.

    Args:
        payload: Request body as URL-encoded string
        signature: X-Twilio-Signature header value
        auth_token: Twilio Auth Token
        url: Full request URL (e.g., https://example.com/webhook)

    Returns:
        True if signature is valid
    """
    try:
        # Parse URL-encoded body into dict
        params = dict(parse_qsl(payload))

        # Build signed content: URL + sorted params
        signed_content = url

        for key in sorted(params.keys()):
            signed_content += key + params[key]

        # Generate expected signature (HMAC-SHA1)
        expected = hmac.new(
            auth_token.encode(),
            signed_content.encode(),
            hashlib.sha1,
        ).digest()

        # Signature from Twilio is base64-encoded
        import base64

        expected_signature = base64.b64encode(expected).decode()

        # Constant-time comparison
        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(
            "twilio_signature_validation_error",
            error=str(e),
            exc_info=True,
        )
        return False
