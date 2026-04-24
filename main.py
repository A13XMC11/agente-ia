"""
FastAPI application entrypoint for Agente-IA multi-tenant conversational AI platform.

Handles routing, middleware setup, webhook validation, and API endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from core.router import MessageRouter
from canales.whatsapp import whatsapp_router
from canales.email import email_router
from seguridad.auth import AuthManager
from seguridad.rate_limiter import RateLimiter


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events: startup and shutdown.

    Startup: Initialize connections and services
    Shutdown: Close connections gracefully
    """
    logger.info("application_startup", environment=ENVIRONMENT)

    global message_router, auth_manager, rate_limiter
    try:
        message_router = MessageRouter()
        auth_manager = AuthManager()
        rate_limiter = RateLimiter()
        await message_router.initialize()
        logger.info("core_services_initialized")
    except Exception as e:
        logger.error("startup_error", error=str(e), exc_info=True)
        raise

    yield

    logger.info("application_shutdown")
    try:
        if message_router:
            await message_router.close()
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

@app.post("/webhooks/whatsapp/messages")
async def whatsapp_webhook(request: Request):
    """
    WhatsApp Cloud API webhook endpoint.

    Receives messages from Meta Cloud API and routes to agent.
    Handles: incoming messages, delivery confirmations, read receipts.
    """
    if not message_router:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()

    # Route to WhatsApp handler
    response = await whatsapp_router.handle_webhook(body, request)

    logger.info("whatsapp_webhook_processed", entry_id=body.get("entry", [{}])[0].get("id"))

    return response


@app.post("/webhooks/email/inbound")
async def email_webhook(request: Request):
    """
    SendGrid inbound email webhook.

    Receives incoming emails and routes to agent.
    """
    if not message_router:
        raise HTTPException(status_code=503, detail="Service not ready")

    body = await request.json()

    # Route to email handler
    response = await email_router.handle_inbound(body, request)

    logger.info("email_webhook_processed")

    return response


@app.get("/webhooks/whatsapp/verify")
async def whatsapp_verify(
    mode: str | None = None,
    token: str | None = None,
    challenge: str | None = None,
):
    """
    WhatsApp webhook verification endpoint.

    Called by Meta to verify webhook URL ownership during setup.
    """
    expected_token = os.getenv("META_VERIFY_TOKEN", "")

    if mode == "subscribe" and token == expected_token:
        logger.info("whatsapp_webhook_verified")
        return challenge
    else:
        logger.warning("whatsapp_webhook_verification_failed", token=token)
        raise HTTPException(status_code=403, detail="Verification failed")


# ============================================================================
# API ENDPOINTS: Management and queries
# ============================================================================

@app.get("/api/clients/{client_id}/conversations")
async def get_conversations(client_id: str, request: Request):
    """
    Get all conversations for a client.

    Requires: valid JWT token with matching client_id
    """
    if not auth_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    # Verify JWT and client_id match
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await auth_manager.verify_token(token)

    if user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # TODO: Fetch conversations from Supabase
    return {
        "client_id": client_id,
        "conversations": [],
    }


@app.get("/api/clients/{client_id}/leads")
async def get_leads(client_id: str, request: Request):
    """
    Get all leads for a client with scores.

    Requires: valid JWT token with matching client_id
    """
    if not auth_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await auth_manager.verify_token(token)

    if user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # TODO: Fetch leads from Supabase
    return {
        "client_id": client_id,
        "leads": [],
    }


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
        reload=ENVIRONMENT == "development",
    )
