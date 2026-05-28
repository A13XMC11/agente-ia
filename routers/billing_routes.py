"""Billing endpoints — Stripe subscription management."""
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


@router.post("/api/billing/create-subscription")
async def create_subscription(request: Request):
    """
    Create a Stripe subscription for a client.

    Body: { client_id, monthly_amount, customer_email }
    Accepts JWT (super_admin) or X-Internal-Secret (dashboard server).
    """
    if not state.stripe_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    user = await _resolve_caller(request)
    body = await request.json()

    monthly_amount = body.get("monthly_amount")
    customer_email = body.get("customer_email")

    if user.get("role") == "super_admin":
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    if not client_id or not monthly_amount or not customer_email:
        raise HTTPException(status_code=400, detail="client_id, monthly_amount and customer_email are required")

    result = await state.stripe_billing.create_subscription(
        client_id=client_id,
        monthly_amount=float(monthly_amount),
        customer_email=customer_email,
    )

    if not result:
        raise HTTPException(status_code=502, detail="Failed to create subscription in Stripe")

    logger.info("subscription_created", client_id=client_id)
    return {"status": "ok", "subscription_id": result.get("id")}


@router.post("/api/billing/cancel-subscription")
async def cancel_subscription(request: Request):
    """
    Cancel a client's Stripe subscription.

    Accepts JWT (super_admin) or X-Internal-Secret (dashboard server).
    Body (super_admin / internal): { client_id }
    """
    if not state.stripe_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    user = await _resolve_caller(request)

    if user.get("role") == "super_admin":
        body = await request.json()
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id could not be determined")

    success = await state.stripe_billing.cancel_subscription(client_id)

    if not success:
        raise HTTPException(status_code=502, detail="Failed to cancel subscription")

    logger.info("subscription_cancelled", client_id=client_id)
    return {"status": "ok"}


@router.post("/api/billing/customer-portal")
async def customer_portal(request: Request):
    """
    Create a Stripe Billing Portal session for a client.

    Body: { client_id, return_url }
    Accepts JWT or X-Internal-Secret.
    Returns: { portal_url }
    """
    if not state.stripe_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    user = await _resolve_caller(request)
    body = await request.json()

    if user.get("role") == "super_admin":
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    return_url = body.get("return_url", "")
    if not client_id or not return_url:
        raise HTTPException(status_code=400, detail="client_id and return_url are required")

    portal_url = await state.stripe_billing.create_customer_portal_session(
        client_id=client_id,
        return_url=return_url,
    )

    if not portal_url:
        raise HTTPException(status_code=502, detail="Failed to create portal session. Ensure Stripe Billing Portal is configured.")

    logger.info("customer_portal_session_created", client_id=client_id)
    return {"portal_url": portal_url}
