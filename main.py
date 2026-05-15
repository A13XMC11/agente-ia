"""
FastAPI application entrypoint for Agente-IA multi-tenant conversational AI platform.

Handles routing, middleware setup, webhook validation, and API endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, HTTPException, Query, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer
import structlog
from supabase import create_client

from core.router import MessageRouter
from core.buffer import MessageBuffer
from core.memory import MemoryManager
from core.normalizer import MessageNormalizer
from canales.whatsapp import WhatsAppHandler
from canales.instagram import InstagramHandler
from canales.facebook import FacebookHandler
from canales.email import EmailHandler
from seguridad.auth import AuthManager
from seguridad.rate_limiter import RateLimiter
from seguridad.validator import WebhookValidator
from config.modelos import UserLogin, TokenResponse


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Initialize core services
message_router: MessageRouter | None = None
auth_manager: AuthManager | None = None
rate_limiter: RateLimiter | None = None
supabase_client = None
normalizer: MessageNormalizer | None = None
buffer: MessageBuffer | None = None
memory: MemoryManager | None = None
validator: WebhookValidator | None = None

# Channel handlers
whatsapp_handler: WhatsAppHandler | None = None
instagram_handler: InstagramHandler | None = None
facebook_handler: FacebookHandler | None = None
email_handler: EmailHandler | None = None

# Alerts, follow-ups, and scheduler
alertas_module: Any | None = None
seguimiento_module: Any | None = None
scheduler: AsyncIOScheduler | None = None


async def _verificar_todos_los_seguimientos(
    seg_module: Any,
    supabase_client: Any,
) -> None:
    """
    Check and send all pending follow-ups for all active clients.

    Called every 30 minutes by scheduler.
    """
    try:
        response = supabase_client.table("clientes").select("id").eq("estado", "activo").execute()
        clients = response.data or []

        logger.info(f"Checking follow-ups for {len(clients)} active clients")

        for client in clients:
            try:
                client_id = client.get("id")
                result = await seg_module.verificar_seguimientos_pendientes(client_id)
                total = sum(result.values())
                if total > 0:
                    logger.info(f"Sent {total} follow-ups to client {client_id}", extra={
                        "cliente_id": client_id,
                        "resumen": result,
                    })
            except Exception as e:
                logger.error(f"Error checking follow-ups for client {client.get('id')}: {e}")

    except Exception as e:
        logger.error(f"Error in seguimientos job: {e}", exc_info=True)


async def _send_daily_summaries(alertas_module: Any, supabase_client: Any) -> None:
    """
    Send daily summary to all business owners at 8 PM.

    Fetches all active clients and sends them their daily metrics.
    """
    try:
        if not alertas_module or not supabase_client:
            logger.warning("alertas_module or supabase_client not available for daily summaries")
            return

        # Get all active clients
        response = supabase_client.table("clientes").select("id").eq("estado", "activo").execute()
        clients = response.data or []

        logger.info(f"Sending daily summaries to {len(clients)} active clients")

        # Send summary to each client
        for client in clients:
            try:
                client_id = client.get("id")
                result = await alertas_module.enviar_resumen_diario(client_id)
                if result.get("success"):
                    logger.info(f"Daily summary sent to client {client_id}", extra={"client_id": client_id})
                else:
                    logger.warning(f"Failed to send daily summary to client {client_id}", extra={"client_id": client_id})
            except Exception as e:
                logger.error(f"Error sending daily summary to client {client['id']}: {e}")

    except Exception as e:
        logger.error(f"Error in _send_daily_summaries: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events: startup and shutdown.

    Startup: Initialize connections and services.
    Only fails on critical errors; non-critical failures are logged.
    """
    logger.info("application_startup", environment=ENVIRONMENT)

    global message_router, auth_manager, rate_limiter, supabase_client
    global normalizer, buffer, memory, validator
    global whatsapp_handler, instagram_handler, facebook_handler, email_handler
    global alertas_module, seguimiento_module, scheduler

    startup_ok = False

    try:
        # 1. Initialize Supabase (CRITICAL)
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_KEY", "").strip()
        supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

        if not supabase_url or not supabase_key:
            logger.error("startup_error", error="SUPABASE_URL or SUPABASE_KEY not set")
            raise ValueError("Missing required Supabase credentials")

        supabase_client = create_client(supabase_url, supabase_key)
        # Service client bypasses RLS — used only for internal server-side reads
        supabase_service_client = create_client(
            supabase_url, supabase_service_key or supabase_key
        )
        logger.info("supabase_initialized")

        # 2. Initialize core services
        try:
            message_router = MessageRouter(
                supabase_client=supabase_client,
                supabase_service_client=supabase_service_client
            )
            logger.info("message_router_created")
        except Exception as e:
            logger.error("message_router_init_error", error=str(e))
            message_router = None

        try:
            rate_limiter = RateLimiter(
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
                supabase_client=supabase_client,
            )
            await rate_limiter.initialize()
            logger.info("rate_limiter_initialized")
        except Exception as e:
            logger.error("rate_limiter_init_error", error=str(e))
            rate_limiter = None

        try:
            auth_manager = AuthManager(
                supabase_client=supabase_client,
                jwt_secret=os.getenv("JWT_SECRET_KEY", ""),
                rate_limiter=rate_limiter,
            )
            logger.info("auth_manager_initialized")
        except Exception as e:
            logger.error("auth_manager_init_error", error=str(e))
            auth_manager = None

        # 3. Initialize message processing components
        try:
            normalizer = MessageNormalizer()
            logger.info("message_normalizer_created")
        except Exception as e:
            logger.error("normalizer_init_error", error=str(e))
            normalizer = None

        try:
            buffer = MessageBuffer(
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
            )
            await buffer.initialize()
            logger.info("message_buffer_initialized")
        except Exception as e:
            logger.error("buffer_init_error", error=str(e))
            buffer = None

        try:
            memory = MemoryManager(supabase_client=supabase_client)
            logger.info("memory_manager_created")
        except Exception as e:
            logger.error("memory_init_error", error=str(e))
            memory = None

        try:
            validator = WebhookValidator()
            logger.info("webhook_validator_created")
        except Exception as e:
            logger.error("validator_init_error", error=str(e))
            validator = None

        # 4. Initialize message router
        try:
            if message_router:
                await message_router.initialize()
                logger.info("message_router_initialized")
        except Exception as e:
            logger.error("message_router_initialize_error", error=str(e))

        # 5. Initialize channel handlers
        # Log degraded state before attempting — helps diagnose startup failures
        _service_status = {
            "message_router": message_router is not None,
            "normalizer": normalizer is not None,
            "buffer": buffer is not None,
            "memory": memory is not None,
            "supabase": supabase_client is not None,
        }
        _missing = [k for k, v in _service_status.items() if not v]
        if _missing:
            logger.warning(
                "channel_handlers_degraded_mode",
                missing_services=_missing,
                available_services=[k for k, v in _service_status.items() if v],
            )

        try:
            meta_verify_token = os.getenv("META_VERIFY_TOKEN", "")
            meta_app_secret = os.getenv("META_APP_SECRET", "")

            # Create handlers whenever the core router and normalizer are available.
            # buffer and memory may be None (Redis/Supabase degraded) — handlers
            # perform None-safe checks internally and process messages best-effort.
            if message_router and normalizer:
                try:
                    whatsapp_handler = WhatsAppHandler(
                        verify_token=meta_verify_token,
                        app_secret=meta_app_secret,
                        supabase_client=supabase_client,
                        router=message_router,
                        normalizer=normalizer,
                        buffer=buffer,
                        memory=memory,
                    )
                    logger.info("whatsapp_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("whatsapp_handler_init_error", error=str(e))
                    whatsapp_handler = None

                try:
                    instagram_handler = InstagramHandler(
                        verify_token=meta_verify_token,
                        app_secret=meta_app_secret,
                        supabase_client=supabase_client,
                        router=message_router,
                        normalizer=normalizer,
                        buffer=buffer,
                        memory=memory,
                    )
                    logger.info("instagram_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("instagram_handler_init_error", error=str(e))
                    instagram_handler = None

                try:
                    facebook_handler = FacebookHandler(
                        verify_token=meta_verify_token,
                        app_secret=meta_app_secret,
                        supabase_client=supabase_client,
                        router=message_router,
                        normalizer=normalizer,
                        buffer=buffer,
                        memory=memory,
                    )
                    logger.info("facebook_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("facebook_handler_init_error", error=str(e))
                    facebook_handler = None

                try:
                    email_handler = EmailHandler(
                        sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
                        supabase_client=supabase_client,
                        router=message_router,
                        normalizer=normalizer,
                        buffer=buffer,
                        memory=memory,
                    )
                    logger.info("email_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("email_handler_init_error", error=str(e))
                    email_handler = None

                logger.info("channel_handlers_initialized", missing_services=_missing)
            else:
                logger.error(
                    "channel_handlers_skipped_critical_missing",
                    missing_services=_missing,
                    reason="message_router and normalizer are required",
                )
        except Exception as e:
            logger.error("channel_handlers_init_error", error=str(e))

        # 6. Inject cobros_module dependencies into handlers and agents
        # This allows payment verification and owner approval processing
        try:
            if whatsapp_handler and message_router:
                from modulos.cobros import CobrosModule
                from openai import AsyncOpenAI

                # Create cobros module instance
                cobros_module = CobrosModule(
                    supabase_client=supabase_service_client,
                    openai_client=AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "")),
                    redis_client=buffer._redis if buffer else None,
                    whatsapp_handler=whatsapp_handler,
                )

                # Inject into WhatsApp handler for owner approval processing
                whatsapp_handler.cobros_module = cobros_module

                # Inject into all agent instances in the router for cobros tool access
                for agent in message_router.agent_instances.values():
                    agent.set_whatsapp_handler(whatsapp_handler)
                    if buffer:
                        agent.set_redis_client(buffer._redis)

                logger.info("cobros_module_injected")
        except Exception as e:
            logger.error("cobros_module_injection_error", error=str(e))

        # 7. Initialize Alerts Module and Scheduler for daily summaries
        try:
            from modulos.alertas import AlertasModule
            from modulos.seguimiento import SeguimientoModule

            alertas_module = AlertasModule(
                supabase_client=supabase_service_client
            )
            logger.info("alertas_module_initialized")

            # Initialize SeguimientoModule for automatic follow-ups
            seguimiento_module = SeguimientoModule(
                supabase_client=supabase_service_client
            )
            logger.info("seguimiento_module_initialized")

            # Initialize AsyncIO scheduler for cron jobs (UTC timezone)
            scheduler = AsyncIOScheduler(timezone="UTC")
            scheduler.add_job(
                _send_daily_summaries,
                "cron",
                hour=20,
                minute=0,
                args=(alertas_module, supabase_service_client),
                id="daily_summary_job",
                misfire_grace_time=300,
            )

            # Add job for automatic follow-ups every 30 minutes
            scheduler.add_job(
                _verificar_todos_los_seguimientos,
                "interval",
                minutes=30,
                args=(seguimiento_module, supabase_service_client),
                id="seguimientos_automaticos_job",
                misfire_grace_time=60,
            )

            scheduler.start()
            logger.info("scheduler_started", jobs=["daily_summary_at_8pm", "seguimientos_automaticos_job"])
        except Exception as e:
            logger.error("alertas_scheduler_init_error", error=str(e), exc_info=True)
            alertas_module = None
            scheduler = None

        startup_ok = True
        logger.info("application_startup_complete")

    except Exception as e:
        logger.error("critical_startup_error", error=str(e), exc_info=True)
        # Don't re-raise; continue with degraded functionality

    yield

    # Shutdown
    logger.info("application_shutdown", startup_ok=startup_ok)
    try:
        if scheduler:
            try:
                scheduler.shutdown(wait=False)
                logger.info("scheduler_shutdown")
            except Exception as e:
                logger.error("scheduler_shutdown_error", error=str(e))

        if seguimiento_module:
            try:
                await seguimiento_module.close()
                logger.info("seguimiento_module_closed")
            except Exception as e:
                logger.error("seguimiento_module_close_error", error=str(e))

        if message_router:
            try:
                await message_router.close()
            except Exception as e:
                logger.error("message_router_close_error", error=str(e))

        if rate_limiter:
            try:
                await rate_limiter.close()
            except Exception as e:
                logger.error("rate_limiter_close_error", error=str(e))

        if buffer:
            try:
                await buffer.close()
            except Exception as e:
                logger.error("buffer_close_error", error=str(e))

        if whatsapp_handler:
            try:
                await whatsapp_handler.close()
            except Exception as e:
                logger.error("whatsapp_handler_close_error", error=str(e))

        if instagram_handler:
            try:
                await instagram_handler.close()
            except Exception as e:
                logger.error("instagram_handler_close_error", error=str(e))

        if facebook_handler:
            try:
                await facebook_handler.close()
            except Exception as e:
                logger.error("facebook_handler_close_error", error=str(e))

        if email_handler:
            try:
                await email_handler.close()
            except Exception as e:
                logger.error("email_handler_close_error", error=str(e))

        logger.info("application_shutdown_complete")
    except Exception as e:
        logger.error("shutdown_error", error=str(e), exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="Agente-IA",
    description="Multi-tenant conversational AI agent platform",
    version="0.1.0",
    docs_url="/api/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if ENVIRONMENT == "development" else None,
    openapi_url="/api/openapi.json" if ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else [os.getenv("ALLOWED_ORIGINS", "")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MIDDLEWARE: Request logging and context
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with structured logging."""
    request_id = request.headers.get("X-Request-ID", "unknown")

    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
    )

    try:
        response = await call_next(request)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            request_id=request_id,
        )
        return response
    except Exception as e:
        logger.error(
            "request_error",
            method=request.method,
            path=request.url.path,
            error=str(e),
            request_id=request_id,
            exc_info=True,
        )
        raise


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns: {"status": "healthy", "environment": "development"}
    """
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "version": "0.1.0",
    }


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check: confirms all services are initialized.

    Returns: {"ready": true/false}
    """
    ready = (
        message_router is not None
        and auth_manager is not None
        and rate_limiter is not None
    )

    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Services not ready",
        )

    return {"ready": True}


# ============================================================================
# WEBHOOK ENDPOINTS: Message routing from channels
# ============================================================================

@app.get("/webhooks/whatsapp/messages")
async def whatsapp_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """
    WhatsApp webhook verification endpoint.

    Called by Meta to verify webhook URL ownership during setup.
    """
    meta_verify_token = os.getenv("META_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == meta_verify_token:
        logger.info("whatsapp_webhook_verified")
        return PlainTextResponse(challenge)
    logger.warning("whatsapp_webhook_verification_failed", extra={"token": token})
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/whatsapp/messages")
async def whatsapp_webhook(request: Request):
    """
    WhatsApp Cloud API webhook endpoint.

    Receives messages from Meta Cloud API and routes to agent.
    Handles: incoming messages, delivery confirmations, read receipts.
    """
    if not whatsapp_handler:
        _missing = {
            "message_router": message_router is None,
            "normalizer": normalizer is None,
            "buffer": buffer is None,
            "memory": memory is None,
            "supabase": supabase_client is None,
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

    # Route to WhatsApp handler
    response = await whatsapp_handler.handle_webhook(body, x_hub_signature, raw_body=raw_body)

    logger.info("whatsapp_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))

    return response


@app.post("/webhooks/instagram/messages")
async def instagram_webhook(request: Request):
    """
    Instagram webhook endpoint (via Meta Graph API).

    Receives messages from Instagram and routes to agent.
    """
    if not instagram_handler:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature", "")

    # Route to Instagram handler
    response = await instagram_handler.handle_webhook(body, x_hub_signature)

    logger.info("instagram_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))

    return response


@app.get("/webhooks/instagram/verify")
async def instagram_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """
    Instagram webhook verification endpoint.

    Called by Meta to verify webhook URL ownership during setup.
    """
    expected_token = os.getenv("META_VERIFY_TOKEN", "")

    if mode == "subscribe" and token == expected_token:
        logger.info("instagram_webhook_verified")
        return PlainTextResponse(content=challenge)
    else:
        logger.warning("instagram_webhook_verification_failed", token=token)
        raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/facebook/messages")
async def facebook_webhook(request: Request):
    """
    Facebook webhook endpoint (via Meta Graph API).

    Receives messages from Facebook and routes to agent.
    """
    if not facebook_handler:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()
    x_hub_signature = request.headers.get("X-Hub-Signature", "")

    # Route to Facebook handler
    response = await facebook_handler.handle_webhook(body, x_hub_signature)

    logger.info("facebook_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))

    return response


@app.get("/webhooks/facebook/verify")
async def facebook_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """
    Facebook webhook verification endpoint.

    Called by Meta to verify webhook URL ownership during setup.
    """
    expected_token = os.getenv("META_VERIFY_TOKEN", "")

    if mode == "subscribe" and token == expected_token:
        logger.info("facebook_webhook_verified")
        return PlainTextResponse(content=challenge)
    else:
        logger.warning("facebook_webhook_verification_failed", token=token)
        raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/email/inbound")
async def email_webhook(request: Request):
    """
    SendGrid inbound email webhook.

    Receives incoming emails and routes to agent.
    """
    if not email_handler:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()

    # Route to email handler
    response = await email_handler.handle_webhook(body)

    logger.info("email_webhook_processed")

    return response


@app.get("/webhooks/whatsapp/verify")
async def whatsapp_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """
    WhatsApp webhook verification endpoint.

    Called by Meta to verify webhook URL ownership during setup.
    """
    expected_token = os.getenv("META_VERIFY_TOKEN", "")

    if mode == "subscribe" and token == expected_token:
        logger.info("whatsapp_webhook_verified")
        return PlainTextResponse(content=challenge)
    else:
        logger.warning("whatsapp_webhook_verification_failed", token=token)
        raise HTTPException(status_code=403, detail="Verification failed")


# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/auth/login")
async def login(credentials: UserLogin):
    """
    User login endpoint.

    Args:
        credentials: UserLogin with email and password

    Returns:
        TokenResponse with JWT access token
    """
    if not auth_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    user = await auth_manager.authenticate_user(
        email=credentials.email,
        password=credentials.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = auth_manager.create_access_token(
        user_id=user["id"],
        client_id=user.get("client_id", ""),
        role=user.get("role", ""),
        email=user.get("email", ""),
    )

    logger.info("user_login_successful", user_id=user["id"])

    return TokenResponse(access_token=token, token_type="bearer")


# ============================================================================
# API ENDPOINTS: Management and queries
# ============================================================================

@app.get("/api/clients/{client_id}/conversations")
async def get_conversations(client_id: str, request: Request):
    """
    Get all conversations for a client.

    Requires: valid JWT token with matching client_id
    """
    if not auth_manager or not supabase_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    # Verify JWT and client_id match
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await auth_manager.verify_token(token)

    if user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch conversations from Supabase
    try:
        response = supabase_client.table("conversaciones").select(
            "id, user_id, channel, lead_state, lead_score, last_message_at, message_count"
        ).eq("cliente_id", client_id).order(
            "last_message_at", desc=True
        ).limit(50).execute()

        conversations = response.data or []

        logger.info(
            "conversations_fetched",
            client_id=client_id,
            count=len(conversations),
        )

        return {
            "client_id": client_id,
            "conversations": conversations,
        }
    except Exception as e:
        logger.error(
            "failed_to_fetch_conversations",
            client_id=client_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")


@app.get("/api/clients/{client_id}/leads")
async def get_leads(client_id: str, request: Request):
    """
    Get all leads for a client with scores.

    Requires: valid JWT token with matching client_id
    """
    if not auth_manager or not supabase_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await auth_manager.verify_token(token)

    if user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch leads from Supabase
    try:
        response = supabase_client.table("leads").select(
            "id, user_id, conversation_id, lead_score, lead_state, last_activity, channel"
        ).eq("cliente_id", client_id).order(
            "lead_score", desc=True
        ).limit(100).execute()

        leads = response.data or []

        logger.info(
            "leads_fetched",
            client_id=client_id,
            count=len(leads),
        )

        return {
            "client_id": client_id,
            "leads": leads,
        }
    except Exception as e:
        logger.error(
            "failed_to_fetch_leads",
            client_id=client_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to fetch leads")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging."""
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with structured logging."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    if ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level=LOG_LEVEL.lower(),
    )
