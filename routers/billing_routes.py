"""Billing endpoints — Payphone subscription management."""
import hmac
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
import structlog

import app_state as state

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _resolve_caller(request: Request) -> dict[str, Any]:
    """
    Resolve caller identity from JWT or X-Internal-Secret header.

    Returns a user dict with at least 'role' and 'client_id'.
    Internal callers (dashboard server) are granted super_admin privileges.
    """
    internal_secret = os.getenv("INTERNAL_API_SECRET", "")
    provided_secret = request.headers.get("X-Internal-Secret", "")

    if internal_secret and provided_secret and hmac.compare_digest(provided_secret, internal_secret):
        return {"role": "super_admin", "client_id": None, "_internal": True}

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization required")

    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Auth service not available")

    try:
        return await state.auth_manager.verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/api/billing/create-payment-link")
async def create_payment_link(request: Request):
    """
    Initiate a Payphone sale request for a client's monthly subscription.

    Sends a push notification to the client's Payphone app. The client
    approves or rejects within 5 minutes. Payphone then calls our webhook.

    Body: { client_id, monthly_amount, phone_number, country_code? }
    Accepts JWT (super_admin) or X-Internal-Secret (dashboard server).
    Returns: { transaction_id, client_transaction_id }
    """
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    user = await _resolve_caller(request)
    body = await request.json()

    monthly_amount = body.get("monthly_amount")
    phone_number = body.get("phone_number")
    country_code = body.get("country_code", "593")

    if user.get("role") == "super_admin":
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    if not client_id or not monthly_amount or not phone_number:
        raise HTTPException(
            status_code=400,
            detail="client_id, monthly_amount and phone_number are required",
        )

    result = await state.payphone_billing.create_sale(
        client_id=client_id,
        monthly_amount=float(monthly_amount),
        phone_number=str(phone_number),
        country_code=str(country_code),
    )

    if not result:
        raise HTTPException(status_code=502, detail="Failed to create sale in Payphone")

    logger.info("payphone_sale_created", client_id=client_id)
    return {
        "status": "ok",
        "transaction_id": result["transaction_id"],
        "client_transaction_id": result["client_transaction_id"],
    }


@router.post("/api/billing/confirm-payment")
async def confirm_payment(request: Request):
    """
    Manually confirm a Payphone payment by transaction IDs.

    Body: { payphone_transaction_id, client_transaction_id }
    Accepts JWT (super_admin) or X-Internal-Secret.
    """
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    await _resolve_caller(request)
    body = await request.json()

    payphone_transaction_id = body.get("payphone_transaction_id")
    client_transaction_id = body.get("client_transaction_id")

    if not payphone_transaction_id or not client_transaction_id:
        raise HTTPException(
            status_code=400,
            detail="payphone_transaction_id and client_transaction_id are required",
        )

    result = await state.payphone_billing.confirm_payment(
        payphone_transaction_id=int(payphone_transaction_id),
        client_transaction_id=str(client_transaction_id),
    )

    logger.info("payment_confirmed", result_status=result.get("status"))
    return {"status": "ok", "result": result}


@router.post("/api/billing/cancel-subscription")
async def cancel_subscription(request: Request):
    """
    Cancel a client's subscription.

    Accepts JWT (super_admin) or X-Internal-Secret (dashboard server).
    Body (super_admin / internal): { client_id }
    """
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    user = await _resolve_caller(request)

    if user.get("role") == "super_admin":
        body = await request.json()
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id could not be determined")

    success = await state.payphone_billing.cancel_subscription(client_id)

    if not success:
        raise HTTPException(status_code=502, detail="Failed to cancel subscription")

    logger.info("subscription_cancelled", client_id=client_id)
    return {"status": "ok"}
