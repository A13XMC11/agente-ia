"""
Pytest configuration and shared fixtures.

Provides:
- Mock Supabase client
- Mock Redis client
- Mock OpenAI client
- Test data fixtures
"""

import os
from datetime import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock


# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    supabase = AsyncMock()
    supabase.table = MagicMock(return_value=MagicMock())
    return supabase


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(return_value=None)
    redis_client.set = AsyncMock()
    redis_client.incr = AsyncMock(return_value=1)
    redis_client.lpush = AsyncMock()
    redis_client.rpush = AsyncMock()
    redis_client.lrange = AsyncMock(return_value=[])
    redis_client.delete = AsyncMock()
    redis_client.exists = AsyncMock(return_value=False)
    redis_client.expire = AsyncMock()
    redis_client.ttl = AsyncMock(return_value=3600)
    return redis_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    openai = AsyncMock()
    return openai


@pytest.fixture
def test_client_id():
    """Test client ID."""
    return "test-client-123"


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return "test-user-456"


@pytest.fixture
def test_conversation_id():
    """Test conversation ID."""
    return "test-conversation-789"


@pytest.fixture
def test_message():
    """Sample test message."""
    return {
        "id": "msg-001",
        "conversation_id": "test-conversation-789",
        "sender_id": "test-user-456",
        "sender_type": "user",
        "message_text": "Hello, I'm interested in your service",
        "channel": "whatsapp",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def test_conversation():
    """Sample test conversation."""
    return {
        "id": "test-conversation-789",
        "client_id": "test-client-123",
        "user_id": "test-user-456",
        "channel": "whatsapp",
        "status": "active",
        "lead_state": "curioso",
        "lead_score": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def test_user():
    """Sample test user."""
    return {
        "id": "test-user-456",
        "email": "user@example.com",
        "full_name": "Test User",
        "phone": "+593999999999",
        "client_id": "test-client-123",
    }


@pytest.fixture
def test_client():
    """Sample test client."""
    return {
        "id": "test-client-123",
        "name": "Test Business",
        "industry": "retail",
        "website": "https://example.com",
        "status": "active",
        "support_email": "support@example.com",
        "support_phone": "+5931234567",
        "timezone": "America/Guayaquil",
    }


@pytest.fixture
def whatsapp_webhook_payload():
    """Sample WhatsApp webhook payload from Meta."""
    return {
        "entry": [
            {
                "id": "123456789",  # phone_number_id
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "1234567890",
                                "phone_number_id": "123456789",
                            },
                            "messages": [
                                {
                                    "from": "5491234567890",
                                    "id": "wamid.123456789=",
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {
                                        "body": "Hello, I'm interested in your service"
                                    },
                                }
                            ],
                            "contacts": [
                                {
                                    "profile": {"name": "John Doe"},
                                    "wa_id": "5491234567890",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


@pytest.fixture
def agent_config():
    """Sample agent configuration."""
    return {
        "client_id": "test-client-123",
        "system_prompt": "You are a helpful sales assistant.",
        "temperature": 0.7,
        "max_tokens": 4000,
        "active_modules": {
            "ventas": True,
            "agendamiento": True,
            "cobros": True,
            "links_pago": True,
            "calificacion": True,
            "campanas": False,
            "alertas": True,
            "seguimientos": True,
            "documentos": True,
        },
        "business_hours_start": "08:00",
        "business_hours_end": "18:00",
        "enabled_channels": ["whatsapp"],
    }


@pytest.mark.asyncio
class AsyncTestCase:
    """Base async test case class."""

    pass
