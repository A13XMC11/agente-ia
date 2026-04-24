"""
Webhook validation: verify signatures from Meta and SendGrid.

Uses HMAC-SHA256 to validate webhook authenticity.
"""

import hmac
import hashlib
import json
from typing import Any
import structlog


logger = structlog.get_logger(__name__)


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

    Args:
        html_content: HTML string

    Returns:
        Sanitized HTML
    """
    # TODO: Use nh3 or bleach for production
    # For now, just escape dangerous tags
    dangerous_tags = ["<script", "<iframe", "onerror=", "onload="]

    result = html_content
    for tag in dangerous_tags:
        result = result.replace(tag, "")

    return result
