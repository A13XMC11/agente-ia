"""Webhook endpoints for WhatsApp, Instagram, Facebook, Email, and Payphone."""
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
# PAYPHONE
# ============================================================================

@router.get("/webhooks/payphone")
async def payphone_callback_get(request: Request):
    """
    Payphone payment callback (GET redirect after user pays).

    Payphone redirects the user here with query params:
      transactionId, clientTransactionId, transactionStatus
    We confirm with the Payphone API to validate before updating state.
    """
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    params = dict(request.query_params)
    result = await state.payphone_billing.handle_callback(params)
    logger.info("payphone_callback_processed", result_status=result.get("status"))
    return result


@router.post("/webhooks/payphone")
async def payphone_callback_post(request: Request):
    """
    Payphone payment callback (POST — server-to-server notification).

    Same logic as GET but reads params from JSON body.
    """
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    try:
        params = await request.json()
    except Exception:
        params = dict(request.query_params)

    result = await state.payphone_billing.handle_callback(params)
    logger.info("payphone_callback_post_processed", result_status=result.get("status"))
    return result
