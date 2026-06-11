"""Webhook endpoints for WhatsApp, Instagram, Facebook, Email, and Payphone."""
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
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

    raw_body = await request.body()
    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature-256", "")
    response = await state.instagram_handler.handle_webhook(body, x_hub_signature, raw_body=raw_body)
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

    raw_body = await request.body()
    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature-256", "")
    response = await state.facebook_handler.handle_webhook(body, x_hub_signature, raw_body=raw_body)
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
    Payphone API Sale responseUrl callback (GET).

    Delegates to PayphoneBilling.handle_callback() which calls Payphone's
    /button/V2/Confirm API to verify the transaction before activating.

    Params: id (transactionId), clientTransactionId
    """
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    params = dict(request.query_params)
    transaction_id = params.get("id") or params.get("transactionId")
    client_transaction_id = params.get("clientTransactionID") or params.get("clientTransactionId")

    if not transaction_id or not client_transaction_id:
        logger.warning("payphone_callback_missing_params", params=list(params.keys()))
        return JSONResponse({"status": "error", "message": "Missing id or clientTransactionId"})

    result = await state.payphone_billing.handle_callback({
        "id": transaction_id,
        "clientTransactionID": client_transaction_id,
    })

    logger.info("payphone_callback_get", result=result.get("status"))
    return JSONResponse(result)


@router.post("/webhooks/payphone")
async def payphone_notificacion_externa(request: Request):
    """
    Payphone Notificación Externa — POST automático tras pago aprobado.

    Payphone envía esto al webhook configurado cuando un pago se aprueba.
    Solo se notifican transacciones aprobadas (StatusCode 3).
    No requiere llamar a /button/V2/Confirm — Payphone ya trae el estado completo.

    Respuesta requerida por Payphone:
      {"Response": true,  "ErrorCode": "000"}  → recepción correcta
      {"Response": false, "ErrorCode": "XXX"}  → error
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"Response": False, "ErrorCode": "111"})

    print(f"[PAYPHONE] Notificación externa recibida: {body}")

    transaction_id = (
        body.get("TransactionId")
        or body.get("transactionId")
        or body.get("TransactionID")
    )
    client_transaction_id = (
        body.get("ClientTransactionId")
        or body.get("clientTransactionId")
        or body.get("ClientTransactionID")
        or body.get("clientTransactionID")
    )
    status_code = body.get("StatusCode") if body.get("StatusCode") is not None else body.get("statusCode")
    transaction_status = body.get("TransactionStatus", "") or body.get("transactionStatus", "")

    if not transaction_id or not client_transaction_id or status_code is None:
        print(f"[PAYPHONE] Notificación externa: campos requeridos faltantes en {list(body.keys())}")
        return JSONResponse({"Response": False, "ErrorCode": "444"})

    if not state.payphone_billing:
        return JSONResponse({"Response": False, "ErrorCode": "222"})

    supabase = state.payphone_billing.supabase

    sub_resp = supabase.table("subscription").select("cliente_id").eq(
        "payphone_client_transaction_id", str(client_transaction_id)
    ).execute()

    if not sub_resp.data:
        print(f"[PAYPHONE] Notificación externa: suscripción no encontrada para clientTransactionId={client_transaction_id}")
        return JSONResponse({"Response": False, "ErrorCode": "333"})

    client_id = sub_resp.data[0]["cliente_id"]
    now = datetime.utcnow().isoformat()

    if status_code == 3 or transaction_status == "Approved":
        # Idempotency: skip if this exact transaction_id was already recorded
        supabase.table("subscription").update({
            "status": "active",
            "payphone_transaction_id": str(transaction_id),
            "last_payment_date": now,
            "payment_failed_count": 0,
        }).eq("payphone_client_transaction_id", str(client_transaction_id)).neq(
            "payphone_transaction_id", str(transaction_id)
        ).execute()

        supabase.table("clientes").update({"estado": "activo"}).eq(
            "id", client_id
        ).eq("estado", "pausado").execute()

        print(f"[PAYPHONE] Suscripción activada para cliente {client_id}")

    elif status_code == 2 or transaction_status == "Canceled":
        supabase.table("subscription").update({
            "status": "cancelled",
            "cancelled_date": now,
        }).eq("payphone_client_transaction_id", str(client_transaction_id)).execute()

        print(f"[PAYPHONE] Pago cancelado para cliente {client_id}")

    logger.info("payphone_notificacion_externa", client_id=client_id, status_code=status_code)
    return JSONResponse({"Response": True, "ErrorCode": "000"})
