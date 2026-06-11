"""API endpoints — conversations, leads, catalog, and calendar."""
import base64
import hmac
import json as _json
import os
import re as _re
from datetime import datetime as _dt
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
import structlog

import app_state as state

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _require_internal_secret(request: Request) -> None:
    """Reject requests to /internal/* endpoints that lack a valid X-Internal-Secret."""
    internal_secret = os.getenv("INTERNAL_API_SECRET", "")
    provided = request.headers.get("X-Internal-Secret", "")
    if not internal_secret or not provided or not hmac.compare_digest(provided, internal_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")


# ============================================================================
# CONVERSATIONS & LEADS
# ============================================================================

async def _verify_client_access(request: Request, client_id: str) -> dict:
    """
    Verify that the caller is authenticated and authorised to access client_id.

    SUPER_ADMIN (client_id is None in JWT) may access any client.
    ADMIN / OPERADOR must have a matching client_id claim.
    """
    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Auth service not ready")

    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        user = await state.auth_manager.verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    role = user.get("role", "")
    if role != "super_admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return user


@router.get("/api/clients/{client_id}/conversations")
async def get_conversations(client_id: str, request: Request):
    """
    Get all conversations for a client.

    Requires: valid JWT token with matching client_id
    """
    if not state.supabase_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    await _verify_client_access(request, client_id)

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
      - file : CSV (.csv) or Excel (.xlsx/.xls) file, max 10 MB
      - client_id : target client UUID

    Auth: requires Authorization header with super_admin or admin JWT
    that owns the given client_id.

    Returns: { success, total_rows, created, updated, skipped }
    """
    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Auth service not ready")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = await state.auth_manager.verify_token(token)
        caller_role = payload.get("role", "")
        caller_client = payload.get("client_id") or payload.get("cliente_id", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    form = await request.form()
    client_id: str = str(form.get("client_id", "")).strip()
    file: Any = form.get("file")

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id requerido")
    if not file:
        raise HTTPException(status_code=400, detail="file requerido")

    if caller_role != "super_admin" and caller_client != client_id:
        raise HTTPException(status_code=403, detail="No autorizado para este cliente")

    if not state.catalog_sync_module:
        raise HTTPException(status_code=503, detail="Módulo de catálogo no disponible")

    filename: str = getattr(file, "filename", "") or ""
    content: bytes = await file.read()

    # 10 MB hard cap — prevents memory exhaustion via large uploads
    _MAX_UPLOAD_BYTES = 10 * 1024 * 1024
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede el límite de 10 MB")

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
    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Auth service not ready")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = await state.auth_manager.verify_token(token)
        caller_role = payload.get("role", "")
        caller_client = payload.get("client_id") or payload.get("cliente_id", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not state.supabase_service_client:
        raise HTTPException(status_code=503, detail="Database not ready")

    body = await request.json()
    client_id: str = str(body.get("client_id", "")).strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id requerido")
    if caller_role != "super_admin" and caller_client != client_id:
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
    if not state.auth_manager:
        raise HTTPException(status_code=503, detail="Auth service not available")

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        await state.auth_manager.verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

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

_EMAIL_RE = _re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


@router.post("/internal/send-email")
async def internal_send_email(request: Request):
    """
    Internal endpoint for sending transactional emails via SendGrid.
    Called by the Next.js dashboard (e.g. welcome email on client creation).
    Requires X-Internal-Secret header.
    """
    await _require_internal_secret(request)
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    if not sendgrid_api_key:
        raise HTTPException(status_code=503, detail="SendGrid not configured")

    body = await request.json()
    to = str(body.get("to", "")).strip()
    subject = str(body.get("subject", "")).strip()
    text_body = str(body.get("body", "")).strip()

    if not to or not subject or not text_body:
        raise HTTPException(status_code=400, detail="Missing required fields: to, subject, body")

    # Validate recipient email to prevent open-relay abuse
    if not _EMAIL_RE.match(to):
        raise HTTPException(status_code=400, detail="Invalid recipient email address")

    # Hard caps prevent excessively large payloads
    if len(subject) > 200:
        raise HTTPException(status_code=400, detail="subject must be ≤ 200 characters")
    if len(text_body) > 10_000:
        raise HTTPException(status_code=400, detail="body must be ≤ 10 000 characters")

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
    Requires X-Internal-Secret header.
    """
    await _require_internal_secret(request)
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


# generate-prompt calls GPT-4o — limit to 5 requests per IP per minute to
# prevent cost abuse while allowing normal dashboard usage.
_PROMPT_GEN_IP_LIMIT = 5
_PROMPT_GEN_IP_WINDOW = 60

# Maximum length for each free-text field injected into the meta-prompt.
# Keeps token cost bounded and mitigates prompt-injection via long inputs.
_FIELD_LIMITS: dict[str, int] = {
    "empresa": 100,
    "industria": 100,
    "descripcion": 500,
    "servicios": 500,
    "nombre_agente": 50,
    "tono": 50,
    "idioma": 30,
    "publico_objetivo": 200,
    "reglas_especiales": 300,
}


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/internal/generate-prompt")
async def internal_generate_prompt(request: Request):
    """
    Generate an optimized system prompt for a client's AI agent using GPT-4o.
    Called by the Next.js dashboard prompt generator UI.
    Requires X-Internal-Secret header.
    """
    await _require_internal_secret(request)

    # IP rate limiting — each GPT-4o call has a real cost
    if state.rate_limiter:
        ip = _get_request_ip(request)
        allowed, info = await state.rate_limiter.check_ip_rate_limit(
            ip=ip,
            endpoint="generate_prompt",
            limit=_PROMPT_GEN_IP_LIMIT,
            window_seconds=_PROMPT_GEN_IP_WINDOW,
        )
        if not allowed:
            logger.warning(
                "generate_prompt_rate_limit_exceeded",
                ip=ip,
                current=info.get("current"),
            )
            raise HTTPException(
                status_code=429,
                detail="Demasiadas solicitudes. Espera un momento antes de generar otro prompt.",
                headers={"Retry-After": str(_PROMPT_GEN_IP_WINDOW)},
            )

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=503, detail="OpenAI not configured")

    body = await request.json()

    def _sanitize(value: object, key: str) -> str:
        """Truncate and strip a field; remove control characters."""
        text = str(value or "").strip()
        max_len = _FIELD_LIMITS.get(key, 200)
        text = text[:max_len]
        # Strip ASCII control characters (except newline) to prevent injection
        text = _re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
        return text

    empresa = _sanitize(body.get("empresa", ""), "empresa")
    industria = _sanitize(body.get("industria", ""), "industria")
    descripcion = _sanitize(body.get("descripcion", ""), "descripcion")
    servicios = _sanitize(body.get("servicios", ""), "servicios")
    nombre_agente = _sanitize(body.get("nombre_agente", "Asistente"), "nombre_agente")
    tono = _sanitize(body.get("tono", "Amigable"), "tono")
    idioma = _sanitize(body.get("idioma", "Español"), "idioma")
    publico_objetivo = _sanitize(body.get("publico_objetivo", ""), "publico_objetivo")
    reglas_especiales = _sanitize(body.get("reglas_especiales", ""), "reglas_especiales")
    # Only accept known module keys — prevents arbitrary strings in the prompt
    _VALID_MODULOS = frozenset(_FIELD_LIMITS) | {
        "ventas", "agendamiento", "cobros", "links_pago",
        "calificacion", "campanas", "analytics", "alertas", "seguimientos",
    }
    modulos = [m for m in body.get("modulos", []) if isinstance(m, str) and m in _VALID_MODULOS]

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
async def internal_invalidate_cache(client_id: str, request: Request):
    """
    Invalidate the cached agent instance for a client.
    Called by the dashboard after module toggles or config changes
    so the next message picks up the updated settings immediately.
    Requires X-Internal-Secret header.
    """
    await _require_internal_secret(request)
    if not state.message_router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    state.message_router.invalidate_agent_cache(client_id)
    return {"status": "ok", "client_id": client_id}
