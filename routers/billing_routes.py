"""Billing endpoints — Payphone subscription management and manual methods."""
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
    Create a subscription. Routes to Payphone or manual billing based on payment_method.

    Body (Payphone):    { client_id, monthly_amount, phone_number, country_code?, payment_method='payphone' }
    Body (transferencia/efectivo): { client_id, monthly_amount, payment_method }
    Accepts JWT (super_admin) or X-Internal-Secret.
    """
    user = await _resolve_caller(request)
    body = await request.json()

    monthly_amount = body.get("monthly_amount")
    payment_method = body.get("payment_method", "payphone")

    if user.get("role") == "super_admin":
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    if not client_id or not monthly_amount:
        raise HTTPException(status_code=400, detail="client_id and monthly_amount are required")

    if payment_method in ("transferencia", "efectivo"):
        if not state.manual_billing:
            raise HTTPException(status_code=503, detail="Manual billing service not configured")

        result = state.manual_billing.create_subscription(
            client_id=str(client_id),
            monthly_amount=float(monthly_amount),
            payment_method=payment_method,
        )
        if not result:
            raise HTTPException(status_code=502, detail="Failed to create manual subscription")

        logger.info("manual_subscription_created", client_id=client_id, method=payment_method)
        return {"status": "ok", "payment_method": payment_method}

    # Default: Payphone
    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    phone_number = body.get("phone_number")
    country_code = body.get("country_code", "593")

    if not phone_number:
        raise HTTPException(status_code=400, detail="phone_number is required for Payphone")

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
        "payment_method": "payphone",
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


@router.post("/api/billing/manual-activate")
async def manual_activate_subscription(request: Request):
    """
    Manually mark a subscription as active (super_admin only).

    Interim endpoint while Payphone Notificación Externa authorization is pending.
    Super_admin verifies payment in Payphone dashboard and calls this to activate in DB.

    Body: { client_id }
    """
    from datetime import datetime

    user = await _resolve_caller(request)
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can manually activate subscriptions")

    body = await request.json()
    client_id = body.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    if not state.payphone_billing:
        raise HTTPException(status_code=503, detail="Billing service not configured")

    supabase = state.payphone_billing.supabase

    sub_resp = supabase.table("subscription").select("id, status").eq(
        "cliente_id", client_id
    ).order("created_at", desc=True).limit(1).execute()

    if not sub_resp.data:
        raise HTTPException(status_code=404, detail="No subscription found for this client")

    now = datetime.utcnow().isoformat()
    supabase.table("subscription").update({
        "status": "active",
        "last_payment_date": now,
        "payment_failed_count": 0,
    }).eq("cliente_id", client_id).execute()

    supabase.table("clientes").update({"estado": "activo"}).eq(
        "id", client_id
    ).eq("estado", "pausado").execute()

    logger.info("subscription_manually_activated", client_id=client_id)
    return {"status": "ok", "message": "Subscription activated manually"}


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


@router.post("/api/billing/submit-proof")
async def submit_proof(request: Request):
    """
    Record that a client uploaded a bank transfer proof.

    Body: { client_id, proof_url }
    Accepts JWT (any role) or X-Internal-Secret.
    """
    if not state.manual_billing:
        raise HTTPException(status_code=503, detail="Manual billing service not configured")

    user = await _resolve_caller(request)
    body = await request.json()

    if user.get("role") == "super_admin" or user.get("_internal"):
        client_id = body.get("client_id") or user.get("client_id")
    else:
        client_id = user.get("client_id")

    proof_url = body.get("proof_url")

    if not client_id or not proof_url:
        raise HTTPException(status_code=400, detail="client_id and proof_url are required")

    success = state.manual_billing.submit_proof(
        client_id=str(client_id),
        proof_url=str(proof_url),
    )

    if not success:
        raise HTTPException(status_code=502, detail="Failed to record proof submission")

    logger.info("transfer_proof_submitted", client_id=client_id)
    return {"status": "ok"}


@router.post("/api/billing/verify-manual")
async def verify_manual_payment(request: Request):
    """
    Admin approves or rejects a manual payment proof.

    Body: { client_id, approve: bool, notes?: str }
    Accepts JWT (super_admin) or X-Internal-Secret.
    """
    if not state.manual_billing:
        raise HTTPException(status_code=503, detail="Manual billing service not configured")

    user = await _resolve_caller(request)
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can verify payments")

    body = await request.json()
    client_id = body.get("client_id")
    approve = body.get("approve")
    notes = body.get("notes")

    if not client_id or approve is None:
        raise HTTPException(status_code=400, detail="client_id and approve are required")

    verified_by = user.get("email") or user.get("sub") or "admin"

    success = state.manual_billing.verify_payment(
        client_id=str(client_id),
        approve=bool(approve),
        verified_by=str(verified_by),
        notes=str(notes) if notes else None,
    )

    if not success:
        raise HTTPException(status_code=502, detail="Failed to verify payment")

    action = "approved" if approve else "rejected"
    logger.info("manual_payment_verified", client_id=client_id, action=action)
    return {"status": "ok", "action": action}


@router.post("/api/billing/renew-manual")
async def renew_manual_subscription(request: Request):
    """
    Roll a manual subscription forward one month (admin action).

    Body: { client_id }
    Accepts JWT (super_admin) or X-Internal-Secret.
    """
    if not state.manual_billing:
        raise HTTPException(status_code=503, detail="Manual billing service not configured")

    user = await _resolve_caller(request)
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can renew subscriptions")

    body = await request.json()
    client_id = body.get("client_id")

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    verified_by = user.get("email") or user.get("sub") or "admin"

    success = state.manual_billing.renew(
        client_id=str(client_id),
        verified_by=str(verified_by),
    )

    if not success:
        raise HTTPException(status_code=502, detail="Failed to renew subscription")

    logger.info("manual_subscription_renewed", client_id=client_id)
    return {"status": "ok"}


@router.get("/api/billing/due-manual")
async def get_due_manual_subscriptions(request: Request):
    """
    List manual subscriptions due or overdue within the next 3 days.

    Accepts JWT (super_admin) or X-Internal-Secret.
    """
    if not state.manual_billing:
        raise HTTPException(status_code=503, detail="Manual billing service not configured")

    user = await _resolve_caller(request)
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can view due subscriptions")

    due = state.manual_billing.get_due_subscriptions()
    return {"status": "ok", "data": due}
