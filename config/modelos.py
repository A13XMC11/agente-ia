"""
Data models and schemas for Agente-IA.

Defines Pydantic schemas for API requests/responses and database models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# ENUMS
# ============================================================================

class RoleEnum(str, Enum):
    """User roles in the system."""

    SUPER_ADMIN = "super_admin"  # Full control of all clients
    ADMIN = "admin"  # Control own client
    OPERADOR = "operador"  # Can take conversations


class ClientStatusEnum(str, Enum):
    """Client subscription status."""

    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"


class ChannelTypeEnum(str, Enum):
    """Available communication channels."""

    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    EMAIL = "email"


class ConversationStatusEnum(str, Enum):
    """State of a conversation."""

    ACTIVE = "active"
    WAITING = "waiting"  # Waiting for user response
    ESCALATED = "escalated"  # Handed to human
    CLOSED = "closed"


class LeadStateEnum(str, Enum):
    """Lead classification."""

    CURIOSO = "curioso"  # Just browsing
    PROSPECTO = "prospecto"  # Showed interest
    CALIENTE = "caliente"  # Hot lead, score >= 8
    CLIENTE = "cliente"  # Converted customer
    DESCARTADO = "descartado"  # Not a fit


# ============================================================================
# USER & AUTHENTICATION
# ============================================================================

class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str
    role: RoleEnum


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8)
    client_id: Optional[str] = None  # Required for non-super-admin users


class UserResponse(UserBase):
    """User response schema."""

    id: str
    client_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds


# ============================================================================
# CLIENT (BUSINESS)
# ============================================================================

class ClientBase(BaseModel):
    """Base client schema."""

    name: str = Field(..., min_length=1, max_length=255)
    industry: str
    website: Optional[str] = None
    support_email: str
    support_phone: str
    timezone: str = "America/Guayaquil"


class ClientCreate(ClientBase):
    """Schema for client creation."""

    admin_email: EmailStr
    admin_full_name: str
    admin_password: str = Field(..., min_length=8)


class ClientUpdate(BaseModel):
    """Schema for updating client config."""

    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None


class ClientResponse(ClientBase):
    """Client response schema."""

    id: str
    status: ClientStatusEnum
    created_at: datetime
    updated_at: datetime
    message_limit_monthly: int
    message_count_current_month: int

    class Config:
        from_attributes = True


# ============================================================================
# AGENT & CONFIG
# ============================================================================

class AgentConfig(BaseModel):
    """Agent configuration per client."""

    client_id: str
    system_prompt: str
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4000, ge=500, le=8000)
    active_modules: dict[str, bool] = Field(
        default={
            "ventas": True,
            "agendamiento": True,
            "cobros": True,
            "links_pago": True,
            "calificacion": True,
            "campanas": False,
            "alertas": True,
            "seguimientos": True,
            "documentos": True,
        }
    )
    business_hours_start: str = "08:00"
    business_hours_end: str = "18:00"
    business_hours_timezone: str = "America/Guayaquil"
    enabled_channels: list[ChannelTypeEnum] = [ChannelTypeEnum.WHATSAPP]


# ============================================================================
# MESSAGES & CONVERSATIONS
# ============================================================================

class Message(BaseModel):
    """A single message in a conversation."""

    id: str
    conversation_id: str
    sender_id: str  # User ID or "agent"
    sender_type: str = Field(..., description="'user' or 'agent'")
    message_text: str
    channel: ChannelTypeEnum
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # "image", "video", "document"
    created_at: datetime
    function_calls: Optional[list[dict[str, Any]]] = None
    metadata: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base conversation schema."""

    client_id: str
    user_id: str
    channel: ChannelTypeEnum


class ConversationCreate(ConversationBase):
    """Schema for starting a conversation."""

    pass


class ConversationResponse(ConversationBase):
    """Conversation response with messages."""

    id: str
    status: ConversationStatusEnum
    lead_state: LeadStateEnum = LeadStateEnum.CURIOSO
    lead_score: float = 0.0
    messages: list[Message] = []
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Schema for creating a message."""

    conversation_id: str
    message_text: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None


# ============================================================================
# LEADS & SCORING
# ============================================================================

class LeadProfile(BaseModel):
    """Lead scoring and qualification data."""

    user_id: str
    client_id: str
    state: LeadStateEnum = LeadStateEnum.CURIOSO
    score: float = Field(0.0, ge=0.0, le=10.0)
    urgency: float = Field(0.0, ge=0.0, le=10.0)
    budget: Optional[float] = None
    decision_power: float = Field(0.0, ge=0.0, le=10.0)
    last_interaction: Optional[datetime] = None
    tags: list[str] = []

    class Config:
        from_attributes = True


# ============================================================================
# PAYMENTS & TRANSFERS
# ============================================================================

class PaymentVerification(BaseModel):
    """Payment receipt verification with Vision analysis."""

    id: str
    client_id: str
    user_id: str
    conversation_id: str
    image_url: str
    amount: float
    currency: str = "USD"
    destination_account: Optional[str] = None
    analysis_result: dict[str, Any]  # Vision analysis output
    is_valid: bool
    fraud_score: float = Field(0.0, ge=0.0, le=1.0)
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# APPOINTMENTS & BOOKING
# ============================================================================

class Appointment(BaseModel):
    """Calendar appointment."""

    id: str
    client_id: str
    user_id: str
    calendar_event_id: str  # Google Calendar event ID
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    timezone: str
    status: str = Field("scheduled", description="scheduled, confirmed, cancelled, completed")
    google_calendar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ALERTS & NOTIFICATIONS
# ============================================================================

class AlertLevel(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"  # Via WhatsApp immediate
    IMPORTANT = "important"  # Via WhatsApp + Email
    INFO = "info"  # Via Email + Dashboard


class Alert(BaseModel):
    """System alert to business owner."""

    id: str
    client_id: str
    level: AlertLevel
    title: str
    message: str
    data: Optional[dict[str, Any]] = None
    read: bool = False
    sent_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# WEBHOOK EVENTS
# ============================================================================

class WebhookEvent(BaseModel):
    """Normalized webhook event from any channel."""

    channel: ChannelTypeEnum
    event_type: str  # "message", "delivery", "read", "status_update", etc.
    sender_id: str
    message_id: Optional[str] = None
    message_text: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    timestamp: datetime
    raw_data: dict[str, Any]  # Original webhook payload

    class Config:
        from_attributes = True
