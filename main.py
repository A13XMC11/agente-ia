"""
FastAPI application entrypoint for Agente-IA multi-tenant conversational AI platform.

Handles routing, middleware setup, webhook validation, and API endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from billing.payphone import PayphoneBilling
import app_state as state  # shared mutable service instances


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

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("ENVIRONMENT", "development"),
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))


async def _sync_all_catalogs(sync_module: Any) -> None:
    """APScheduler job: sync all clients with sheets/webhook catalog sources."""
    try:
        await sync_module.sync_all_auto_clients()
    except Exception as e:
        logger.error(f"Error in catalog sync job: {e}", exc_info=True)


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

    startup_ok = False

    try:
        # 1. Initialize Supabase (CRITICAL)
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_KEY", "").strip()
        supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "").strip()

        missing = [k for k, v in {
            "SUPABASE_URL": supabase_url,
            "SUPABASE_KEY": supabase_key,
            "SUPABASE_SERVICE_KEY": supabase_service_key,
            "JWT_SECRET_KEY": jwt_secret_key,
        }.items() if not v]
        if missing:
            logger.error("startup_error", error=f"Missing required env vars: {missing}")
            raise ValueError(f"Missing required environment variables: {missing}")

        state.supabase_client = create_client(supabase_url, supabase_key)
        # Service client bypasses RLS — used only for internal server-side writes
        state.supabase_service_client = create_client(supabase_url, supabase_service_key)
        logger.info("supabase_initialized")

        # 2. Initialize core services
        try:
            state.rate_limiter = RateLimiter(
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
                supabase_client=state.supabase_client,
            )
            await state.rate_limiter.initialize()
            logger.info("rate_limiter_initialized")
        except Exception as e:
            logger.error("rate_limiter_init_error", error=str(e))
            state.rate_limiter = None

        try:
            state.message_router = MessageRouter(
                supabase_client=state.supabase_client,
                supabase_service_client=state.supabase_service_client,
                rate_limiter=state.rate_limiter,
            )
            logger.info("message_router_created")
        except Exception as e:
            logger.error("message_router_init_error", error=str(e))
            state.message_router = None

        try:
            state.auth_manager = AuthManager(
                supabase_client=state.supabase_client,
                jwt_secret=os.getenv("JWT_SECRET_KEY", ""),
                rate_limiter=state.rate_limiter,
            )
            logger.info("auth_manager_initialized")
        except Exception as e:
            logger.error("auth_manager_init_error", error=str(e))
            state.auth_manager = None

        # 3. Initialize message processing components
        try:
            state.normalizer = MessageNormalizer()
            logger.info("message_normalizer_created")
        except Exception as e:
            logger.error("normalizer_init_error", error=str(e))
            state.normalizer = None

        try:
            state.buffer = MessageBuffer(
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
            )
            await state.buffer.initialize()
            logger.info("message_buffer_initialized")
        except Exception as e:
            logger.error("buffer_init_error", error=str(e))
            state.buffer = None

        try:
            state.memory = MemoryManager(supabase_client=state.supabase_service_client)
            logger.info("memory_manager_created")
        except Exception as e:
            logger.error("memory_init_error", error=str(e))
            state.memory = None

        try:
            state.validator = WebhookValidator()
            logger.info("webhook_validator_created")
        except Exception as e:
            logger.error("validator_init_error", error=str(e))
            state.validator = None

        # 4. Initialize message router
        try:
            if state.message_router:
                await state.message_router.initialize()
                logger.info("message_router_initialized")
        except Exception as e:
            logger.error("message_router_initialize_error", error=str(e))

        # 5. Initialize channel handlers
        # Log degraded state before attempting — helps diagnose startup failures
        _service_status = {
            "message_router": state.message_router is not None,
            "normalizer": state.normalizer is not None,
            "buffer": state.buffer is not None,
            "memory": state.memory is not None,
            "supabase": state.supabase_client is not None,
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
            if state.message_router and state.normalizer:
                try:
                    state.whatsapp_handler = WhatsAppHandler(
                        verify_token=meta_verify_token,
                        app_secret=meta_app_secret,
                        supabase_client=state.supabase_client,
                        router=state.message_router,
                        normalizer=state.normalizer,
                        buffer=state.buffer,
                        memory=state.memory,
                    )
                    logger.info("whatsapp_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("whatsapp_handler_init_error", error=str(e))
                    state.whatsapp_handler = None

                try:
                    state.instagram_handler = InstagramHandler(
                        verify_token=meta_verify_token,
                        app_secret=meta_app_secret,
                        supabase_client=state.supabase_client,
                        router=state.message_router,
                        normalizer=state.normalizer,
                        buffer=state.buffer,
                        memory=state.memory,
                    )
                    logger.info("instagram_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("instagram_handler_init_error", error=str(e))
                    state.instagram_handler = None

                try:
                    state.facebook_handler = FacebookHandler(
                        verify_token=meta_verify_token,
                        app_secret=meta_app_secret,
                        supabase_client=state.supabase_client,
                        router=state.message_router,
                        normalizer=state.normalizer,
                        buffer=state.buffer,
                        memory=state.memory,
                    )
                    logger.info("facebook_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("facebook_handler_init_error", error=str(e))
                    state.facebook_handler = None

                try:
                    state.email_handler = EmailHandler(
                        sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
                        supabase_client=state.supabase_client,
                        router=state.message_router,
                        normalizer=state.normalizer,
                        buffer=state.buffer,
                        memory=state.memory,
                    )
                    logger.info("email_handler_created", degraded=bool(_missing))
                except Exception as e:
                    logger.error("email_handler_init_error", error=str(e))
                    state.email_handler = None

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
            if state.whatsapp_handler and state.message_router:
                from modulos.cobros import CobrosModule
                from openai import AsyncOpenAI

                # Create cobros module instance
                redis_client = getattr(state.buffer, 'redis', None) if state.buffer else None
                cobros_module = CobrosModule(
                    supabase_client=state.supabase_service_client,
                    openai_client=AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "")),
                    redis_client=redis_client,
                    whatsapp_handler=state.whatsapp_handler,
                )
                logger.info("cobros_created", cobros_id=id(cobros_module))

                # Inject into WhatsApp handler for owner approval processing
                state.whatsapp_handler.cobros_module = cobros_module

                # Inject into all agent instances in the router for cobros tool access
                for agent in state.message_router.agent_instances.values():
                    agent.set_cobros_module(cobros_module)
                    agent.set_whatsapp_handler(state.whatsapp_handler)
                    if state.buffer:
                        agent.set_redis_client(getattr(state.buffer, 'redis', None))

                logger.info("cobros_module_injected")
        except Exception as e:
            logger.error("cobros_module_injection_error", error=str(e))

        # 7. Initialize Alerts Module and Scheduler for daily summaries
        try:
            from modulos.alertas import AlertasModule
            from modulos.seguimiento import SeguimientoModule

            state.alertas_module = AlertasModule(
                supabase_client=state.supabase_service_client
            )
            logger.info("alertas_module_initialized")

            # Initialize SeguimientoModule for automatic follow-ups
            state.seguimiento_module = SeguimientoModule(
                supabase_client=state.supabase_service_client
            )
            logger.info("seguimiento_module_initialized")

            # Initialize catalog sync module
            from modulos.catalog_sync import CatalogSyncModule
            state.catalog_sync_module = CatalogSyncModule(state.supabase_service_client)
            logger.info("catalog_sync_module_initialized")

            # Initialize AsyncIO scheduler for cron jobs (UTC timezone)
            state.scheduler = AsyncIOScheduler(timezone="UTC")
            state.scheduler.add_job(
                _send_daily_summaries,
                "cron",
                hour=20,
                minute=0,
                args=(state.alertas_module, state.supabase_service_client),
                id="daily_summary_job",
                misfire_grace_time=300,
            )

            # Add job for automatic follow-ups every 30 minutes
            state.scheduler.add_job(
                _verificar_todos_los_seguimientos,
                "interval",
                minutes=30,
                args=(state.seguimiento_module, state.supabase_service_client),
                id="seguimientos_automaticos_job",
                misfire_grace_time=60,
            )

            # Add job for catalog sync every 60 minutes
            state.scheduler.add_job(
                _sync_all_catalogs,
                "interval",
                minutes=60,
                args=(state.catalog_sync_module,),
                id="catalog_sync_job",
                misfire_grace_time=120,
            )

            state.scheduler.start()
            logger.info("scheduler_started", jobs=["daily_summary_at_8pm", "seguimientos_automaticos_job", "catalog_sync_job"])
        except Exception as e:
            logger.error("alertas_scheduler_init_error", error=str(e), exc_info=True)
            state.alertas_module = None
            state.scheduler = None

        # 8. Initialize Payphone billing
        try:
            payphone_token = os.getenv("PAYPHONE_TOKEN", "")
            if payphone_token:
                state.payphone_billing = PayphoneBilling(
                    payphone_token=payphone_token,
                    supabase_client=state.supabase_service_client,
                    response_url=os.getenv(
                        "PAYPHONE_RESPONSE_URL",
                        "https://api.lanlabsec.com/webhooks/payphone",
                    ),
                    store_id=os.getenv("PAYPHONE_STORE_ID") or None,
                )
                logger.info("payphone_billing_initialized")
            else:
                logger.warning("payphone_billing_skipped", reason="PAYPHONE_TOKEN not set")
        except Exception as e:
            logger.error("payphone_billing_init_error", error=str(e))
            state.payphone_billing = None

        startup_ok = True
        logger.info("application_startup_complete")

    except Exception as e:
        logger.error("critical_startup_error", error=str(e), exc_info=True)
        # Don't re-raise; continue with degraded functionality

    yield

    # Shutdown
    logger.info("application_shutdown", startup_ok=startup_ok)
    try:
        if state.scheduler:
            try:
                state.scheduler.shutdown(wait=False)
                logger.info("scheduler_shutdown")
            except Exception as e:
                logger.error("scheduler_shutdown_error", error=str(e))

        if state.payphone_billing:
            try:
                await state.payphone_billing.close()
                logger.info("payphone_billing_closed")
            except Exception as e:
                logger.error("payphone_billing_close_error", error=str(e))

        if state.seguimiento_module:
            try:
                await state.seguimiento_module.close()
                logger.info("seguimiento_module_closed")
            except Exception as e:
                logger.error("seguimiento_module_close_error", error=str(e))

        if state.message_router:
            try:
                await state.message_router.close()
            except Exception as e:
                logger.error("message_router_close_error", error=str(e))

        if state.rate_limiter:
            try:
                await state.rate_limiter.close()
            except Exception as e:
                logger.error("rate_limiter_close_error", error=str(e))

        if state.buffer:
            try:
                await state.buffer.close()
            except Exception as e:
                logger.error("buffer_close_error", error=str(e))

        if state.whatsapp_handler:
            try:
                await state.whatsapp_handler.close()
            except Exception as e:
                logger.error("whatsapp_handler_close_error", error=str(e))

        if state.instagram_handler:
            try:
                await state.instagram_handler.close()
            except Exception as e:
                logger.error("instagram_handler_close_error", error=str(e))

        if state.facebook_handler:
            try:
                await state.facebook_handler.close()
            except Exception as e:
                logger.error("facebook_handler_close_error", error=str(e))

        if state.email_handler:
            try:
                await state.email_handler.close()
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

# Register routers
from routers import webhooks, auth_routes, billing_routes, api_routes
app.include_router(webhooks.router)
app.include_router(auth_routes.router)
app.include_router(billing_routes.router)
app.include_router(api_routes.router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
    ],
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
        state.message_router is not None
        and state.auth_manager is not None
        and state.rate_limiter is not None
    )

    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Services not ready",
        )

    return {"ready": True}



# Endpoints are registered via routers in: routers/webhooks.py, routers/auth_routes.py,
# routers/billing_routes.py, routers/api_routes.py

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
