"""Webhook endpoints for WhatsApp, Instagram, Facebook, Email, and Stripe."""
import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
import structlog

import app_state as state

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# WHATSAPP
# ============================================================================

@router.get("/webhooks/whatsapp/messages")
async def whatsapp_verify_messages(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """WhatsApp webhook verification endpoint."""
    meta_verify_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == meta_verify_token:
        logger.info("whatsapp_webhook_verified")
        return PlainTextResponse(challenge)
    logger.warning("whatsapp_webhook_verification_failed", token=token)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/whatsapp/messages")
async def whatsapp_webhook(request: Request):
    """WhatsApp Cloud API webhook endpoint."""
    if not state.whatsapp_handler:
        _missing = {
            "message_router": state.message_router is None,
            "normalizer": state.normalizer is None,
            "buffer": state.buffer is None,
            "memory": state.memory is None,
            "supabase": state.supabase_client is None,
        }
        logger.error(
            "whatsapp_webhook_handler_unavailable",
            missing_services={k for k, v in _missing.items() if v},
        )
        raise HTTPException(status_code=503, detail="Service not ready")

    raw_body = await request.body()
    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature-256", "")
    logger.info("whatsapp_webhook_incoming", has_signature=bool(x_hub_signature))

    response = await state.whatsapp_handler.handle_webhook(body, x_hub_signature, raw_body=raw_body)
    logger.info("whatsapp_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))
    return response


@router.get("/webhooks/whatsapp/verify")
async def whatsapp_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """WhatsApp webhook verification endpoint (alternate path)."""
    expected_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == expected_token:
        logger.info("whatsapp_webhook_verified")
        return PlainTextResponse(content=challenge)
    logger.warning("whatsapp_webhook_verification_failed", token=token)
    raise HTTPException(status_code=403, detail="Verification failed")


# ============================================================================
# INSTAGRAM
# ============================================================================

@router.get("/webhooks/instagram/messages")
async def instagram_verify_messages(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Instagram webhook verification (GET on the same path Meta posts events to)."""
    expected_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == expected_token:
        logger.info("instagram_webhook_verified")
        return PlainTextResponse(content=challenge)
    logger.warning("instagram_webhook_verification_failed", token=token)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/instagram/messages")
async def instagram_webhook(request: Request):
    """Instagram webhook endpoint (via Meta Graph API)."""
    if not state.instagram_handler:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature", "")
    response = await state.instagram_handler.handle_webhook(body, x_hub_signature)
    logger.info("instagram_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))
    return response


@router.get("/webhooks/instagram/verify")
async def instagram_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Instagram webhook verification endpoint."""
    expected_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == expected_token:
        logger.info("instagram_webhook_verified")
        return PlainTextResponse(content=challenge)
    logger.warning("instagram_webhook_verification_failed", token=token)
    raise HTTPException(status_code=403, detail="Verification failed")


# ============================================================================
# FACEBOOK
# ============================================================================

@router.get("/webhooks/facebook/messages")
async def facebook_verify_messages(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Facebook webhook verification (GET on the same path Meta posts events to)."""
    expected_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == expected_token:
        logger.info("facebook_webhook_verified")
        return PlainTextResponse(content=challenge)
    logger.warning("facebook_webhook_verification_failed", token=token)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/facebook/messages")
async def facebook_webhook(request: Request):
    """Facebook webhook endpoint (via Meta Graph API)."""
    if not state.facebook_handler:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature", "")
    response = await state.facebook_handler.handle_webhook(body, x_hub_signature)
    logger.info("facebook_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))
    return response


@router.get("/webhooks/facebook/verify")
async def facebook_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Facebook webhook verification endpoint."""
    expected_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == expected_token:
        logger.info("facebook_webhook_verified")
        return PlainTextResponse(content=challenge)
    logger.warning("facebook_webhook_verification_failed", token=token)
    raise HTTPException(status_code=403, detail="Verification failed")


# ============================================================================
# EMAIL
# ============================================================================

@router.post("/webhooks/email/inbound")
async def email_webhook(request: Request):
    """SendGrid inbound email webhook."""
    if not state.email_handler:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()
    response = await state.email_handler.handle_webhook(body)
    logger.info("email_webhook_processed")
    return response


# ============================================================================
# STRIPE
# ============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint."""
    if not state.stripe_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    raw_body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    if not state.stripe_billing.verify_webhook_signature(raw_body, signature):
        logger.warning("stripe_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    result = await state.stripe_billing.handle_webhook(event)
    logger.info("stripe_webhook_processed", event_type=event.get("type"))
    return result
