"""API endpoints — conversations, leads, catalog, and calendar."""
import base64
import json as _json
import os
import re as _re
from datetime import datetime as _dt
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
import structlog

import app_state as state
from seguridad.auth import AuthManager

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# CONVERSATIONS & LEADS
# ============================================================================

@router.get("/api/clients/{client_id}/conversations")
async def get_conversations(client_id: str, request: Request):
    """
    Get all conversations for a client.

    Requires: valid JWT token with matching client_id
    """
    if not state.auth_manager or not state.supabase_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await state.auth_manager.verify_token(token)

    if user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        response = state.supabase_client.table("conversaciones").select(
            "id, user_id, channel, lead_state, lead_score, last_message_at, message_count"
        ).eq("cliente_id", client_id).order(
            "last_message_at", desc=True
        ).limit(50).execute()

        conversations = response.data or []
        logger.info("conversations_fetched", client_id=client_id, count=len(conversations))
        return {"client_id": client_id, "conversations": conversations}
    except Exception as e:
        logger.error("failed_to_fetch_conversations", client_id=client_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")


@router.get("/api/clients/{client_id}/leads")
async def get_leads(client_id: str, request: Request):
    """
    Get all leads for a client with scores.

    Requires: valid JWT token with matching client_id
    """
    if not state.auth_manager or not state.supabase_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await state.auth_manager.verify_token(token)

    if user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        response = state.supabase_client.table("leads").select(
            "id, user_id, conversation_id, lead_score, lead_state, last_activity, channel"
        ).eq("cliente_id", client_id).order(
            "lead_score", desc=True
        ).limit(100).execute()

        leads = response.data or []
        logger.info("leads_fetched", client_id=client_id, count=len(leads))
        return {"client_id": client_id, "leads": leads}
    except Exception as e:
        logger.error("failed_to_fetch_leads", client_id=client_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch leads")


# ============================================================================
# CATALOG
# ============================================================================

@router.post("/api/catalog/import")
async def import_catalog(request: Request):
    """
    Import or update a client's product catalog from a CSV or Excel file.

    Accepts multipart/form-data with:
      - file : CSV (.csv) or Excel (.xlsx/.xls) file
      - client_id : target client UUID

    Auth: requires Authorization header with super_admin or admin JWT
    that owns the given client_id.

    Returns: { success, total_rows, created, updated, skipped }
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        auth_manager_local = AuthManager()
        payload = auth_manager_local.verify_token(token)
        caller_role = payload.get("role", "")
        caller_client = payload.get("cliente_id", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    form = await request.form()
    client_id: str = str(form.get("client_id", "")).strip()
    file: Any = form.get("file")

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id requerido")
    if not file:
        raise HTTPException(status_code=400, detail="file requerido")

    if caller_role not in ("super_admin",) and caller_client != client_id:
        raise HTTPException(status_code=403, detail="No autorizado para este cliente")

    if not state.catalog_sync_module:
        raise HTTPException(status_code=503, detail="Módulo de catálogo no disponible")

    filename: str = getattr(file, "filename", "") or ""
    content: bytes = await file.read()

    if filename.lower().endswith(".csv"):
        result = await state.catalog_sync_module.import_from_csv(
            client_id, content.decode("utf-8", errors="replace")
        )
    elif _re.search(r"\.(xlsx|xls)$", filename.lower()):
        result = await state.catalog_sync_module.import_from_excel(client_id, content)
    else:
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Use .csv, .xlsx o .xls",
        )

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Import failed"))

    logger.info("catalog_imported", client_id=client_id, filename=filename)
    return result


@router.post("/api/catalog/sync-config")
async def upsert_catalog_sync_config(request: Request):
    """
    Save or update the catalog sync configuration for a client.

    Body: { client_id, tipo, sheets_url?, webhook_url?, sync_interval_minutes? }
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        auth_manager_local = AuthManager()
        payload = auth_manager_local.verify_token(token)
        caller_role = payload.get("role", "")
        caller_client = payload.get("cliente_id", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    body = await request.json()
    client_id: str = str(body.get("client_id", "")).strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id requerido")
    if caller_role not in ("super_admin",) and caller_client != client_id:
        raise HTTPException(status_code=403, detail="No autorizado para este cliente")

    tipo = body.get("tipo", "manual")
    if tipo not in ("manual", "sheets", "webhook"):
        raise HTTPException(status_code=400, detail="tipo debe ser manual, sheets o webhook")

    now = _dt.utcnow().isoformat()
    row = {
        "cliente_id": client_id,
        "tipo": tipo,
        "sheets_url": body.get("sheets_url"),
        "webhook_url": body.get("webhook_url"),
        "sync_interval_minutes": int(body.get("sync_interval_minutes", 60)),
        "activo": True,
        "updated_at": now,
    }

    state.supabase_service_client.table("catalog_sync_config").upsert(
        row, on_conflict="cliente_id"
    ).execute()

    return {"success": True, "config": row}


# ============================================================================
# CALENDAR
# ============================================================================

@router.get("/api/calendar/service-account-email")
async def get_calendar_service_account_email(request: Request):
    """Return the Google service account email so clients can share their calendar."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    raw = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
    email = None
    if raw:
        try:
            creds = _json.loads(raw)
        except Exception:
            try:
                creds = _json.loads(base64.b64decode(raw))
            except Exception:
                creds = {}
        email = creds.get("client_email")

    return {"success": True, "email": email}


# ============================================================================
# INTERNAL
# ============================================================================

@router.post("/internal/send-email")
async def internal_send_email(request: Request):
    """
    Internal endpoint for sending transactional emails via SendGrid.
    Called by the Next.js dashboard (e.g. welcome email on client creation).
    """
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    if not sendgrid_api_key:
        raise HTTPException(status_code=503, detail="SendGrid not configured")

    body = await request.json()
    to = body.get("to")
    subject = body.get("subject")
    text_body = body.get("body")

    if not to or not subject or not text_body:
        raise HTTPException(status_code=400, detail="Missing required fields: to, subject, body")

    payload = {
        "personalizations": [{"to": [{"email": to}], "subject": subject}],
        "from": {"email": "noreply@lanlabsec.com", "name": "LanLabs"},
        "content": [{"type": "text/plain", "value": text_body}],
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {sendgrid_api_key}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code not in (200, 201, 202):
        logger.error("sendgrid_error", status_code=response.status_code)
        raise HTTPException(status_code=502, detail="Failed to send email")

    logger.info("email_sent")
    return {"status": "ok"}


@router.post("/internal/catalog/sync-now")
async def internal_catalog_sync_now(request: Request):
    """
    Trigger an immediate catalog sync for a client.
    Called by the Next.js dashboard "Sincronizar ahora" button.
    Body: { client_id: string }
    """
    if not state.catalog_sync_module:
        raise HTTPException(status_code=503, detail="Catalog sync module not ready")
    if not state.supabase_service_client:
        raise HTTPException(status_code=503, detail="Database not ready")

    body = await request.json()
    client_id: str = str(body.get("client_id", "")).strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id requerido")

    try:
        cfg_resp = state.supabase_service_client.table("catalog_sync_config").select("*").eq(
            "cliente_id", client_id
        ).single().execute()
        cfg = cfg_resp.data
    except Exception:
        cfg = None

    if not cfg:
        raise HTTPException(status_code=404, detail="No hay configuración de sincronización para este cliente")

    tipo = cfg.get("tipo", "manual")
    if tipo == "sheets" and cfg.get("sheets_url"):
        result = await state.catalog_sync_module.sync_from_sheets(client_id, cfg["sheets_url"])
    elif tipo == "webhook" and cfg.get("webhook_url"):
        result = await state.catalog_sync_module.sync_from_webhook(client_id, cfg["webhook_url"])
    else:
        raise HTTPException(status_code=400, detail="No hay fuente de sincronización configurada (configura Google Sheets o API externa)")

    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error al sincronizar"))

    logger.info("catalog_synced_manually", client_id=client_id, result=result)
    return result


@router.post("/internal/generate-prompt")
async def internal_generate_prompt(request: Request):
    """
    Generate an optimized system prompt for a client's AI agent using GPT-4o.
    Called by the Next.js dashboard prompt generator UI.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=503, detail="OpenAI not configured")

    body = await request.json()

    empresa = str(body.get("empresa", "")).strip()
    industria = str(body.get("industria", "")).strip()
    descripcion = str(body.get("descripcion", "")).strip()
    servicios = str(body.get("servicios", "")).strip()
    nombre_agente = str(body.get("nombre_agente", "Asistente")).strip()
    tono = str(body.get("tono", "Amigable")).strip()
    idioma = str(body.get("idioma", "Español")).strip()
    publico_objetivo = str(body.get("publico_objetivo", "")).strip()
    reglas_especiales = str(body.get("reglas_especiales", "")).strip()
    modulos = [m for m in body.get("modulos", []) if isinstance(m, str)]

    if not empresa or not industria or not descripcion or not servicios:
        raise HTTPException(status_code=400, detail="Campos requeridos: empresa, industria, descripcion, servicios")

    module_capabilities = {
        "ventas": "gestionar el catálogo de productos, crear cotizaciones personalizadas y manejar objeciones de venta",
        "agendamiento": "reservar y gestionar citas usando Google Calendar, incluyendo verificación de disponibilidad",
        "cobros": "solicitar y verificar comprobantes de pago e imágenes de transferencias bancarias",
        "links_pago": "generar y enviar links de pago por Payphone, MercadoPago o PayPal",
        "calificacion": "evaluar la intención de compra del cliente y asignar un puntaje de 0 a 10",
        "campanas": "participar en campañas de mensajería masiva del negocio",
        "analytics": "proporcionar métricas y reportes de rendimiento del negocio",
        "alertas": "enviar notificaciones urgentes o importantes al dueño del negocio",
        "seguimientos": "hacer seguimiento automático a leads y clientes que no han respondido",
    }

    active_caps = [module_capabilities[m] for m in modulos if m in module_capabilities]

    caps_block = (
        "\n".join(f"- {cap}" for cap in active_caps)
        if active_caps
        else "- Responder preguntas sobre el negocio y sus servicios"
    )

    meta_prompt = f"""Eres un experto en prompt engineering para agentes de IA conversacionales de ventas y atención al cliente en WhatsApp.

Tu tarea es generar el system prompt perfecto para un agente llamado "{nombre_agente}" que atiende a los clientes de "{empresa}".

INFORMACIÓN DEL NEGOCIO:
- Empresa: {empresa}
- Sector: {industria}
- Descripción: {descripcion}
- Productos/Servicios: {servicios}
- Público objetivo: {publico_objetivo or "clientes en general"}

CONFIGURACIÓN DEL AGENTE:
- Nombre: {nombre_agente}
- Tono: {tono}
- Idioma: {idioma}

CAPACIDADES HABILITADAS (incluye instrucciones para usarlas):
{caps_block}

REGLAS ESPECIALES:
{reglas_especiales or "Ninguna especificada"}

INSTRUCCIONES PARA EL SYSTEM PROMPT A GENERAR:
1. Empieza definiendo la identidad: quién es el agente, para qué empresa trabaja y cuál es su rol
2. Establece el tono de comunicación de forma clara y con ejemplos de frases tipo
3. Por cada capacidad habilitada, da instrucciones precisas de cuándo y cómo usarla
4. Define qué NO debe hacer el agente (límites claros)
5. Indica cuándo escalar a un humano y cómo hacerlo
6. Incluye cómo manejar preguntas fuera del alcance del negocio
7. Aplica las reglas especiales del cliente si las hay
8. Escribe el prompt en {idioma}
9. Máximo 700 palabras, conciso y directo

IMPORTANTE: Genera ÚNICAMENTE el system prompt, sin explicaciones previas ni encabezados extra. El prompt debe comenzar directamente con las instrucciones para el agente."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": meta_prompt}],
                "max_tokens": 1500,
                "temperature": 0.7,
            },
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code != 200:
        logger.error("generate_prompt_openai_error", status_code=response.status_code)
        raise HTTPException(status_code=502, detail="Error al generar el prompt")

    result = response.json()
    generated_prompt = result["choices"][0]["message"]["content"].strip()

    logger.info("prompt_generated", empresa=empresa, modulos=modulos)
    return {"status": "ok", "prompt": generated_prompt}


@router.post("/internal/invalidate-cache/{client_id}")
async def internal_invalidate_cache(client_id: str):
    """
    Invalidate the cached agent instance for a client.
    Called by the dashboard after module toggles or config changes
    so the next message picks up the updated settings immediately.
    """
    if not state.message_router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    state.message_router.invalidate_agent_cache(client_id)
    return {"status": "ok", "client_id": client_id}
