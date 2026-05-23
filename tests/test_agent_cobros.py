"""
Tests for AgentEngine tool dispatch and CobrosModule critical paths.

Covers:
- registrar_pago parameter alignment between agent and module
- enviar_datos_bancarios when no bank data configured
- registrar_pago guard: no media_url returns error (not exception)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── helpers ────────────────────────────────────────────────────────────────

def _make_agent(active_modules=None):
    """Build a minimal AgentEngine with mocked external dependencies."""
    from core.agent import AgentEngine

    config = {
        "client_id": "test-client",
        "system_prompt": "Test assistant",
        "temperature": 0.7,
        "max_tokens": 100,
        "active_modules": active_modules or {"cobros": True, "calificacion": True},
        "business_hours_start": "08:00",
        "business_hours_end": "18:00",
        "business_hours_timezone": "America/Guayaquil",
    }

    mock_supabase = MagicMock()
    mock_openai = AsyncMock()

    with patch("core.agent.AsyncOpenAI", return_value=mock_openai):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            agent = AgentEngine(
                client_config=config,
                supabase_client=mock_supabase,
                supabase_service_client=mock_supabase,
            )

    return agent, mock_supabase, mock_openai


# ── registrar_pago parameter alignment ─────────────────────────────────────

class TestRegistrarPagoDispatch:
    """Verify agent calls cobros.registrar_pago with correct keyword arguments."""

    @pytest.mark.asyncio
    async def test_registrar_pago_no_media_url_returns_error(self):
        """If no media_url in context, tool should return error dict, not raise."""
        agent, _, _ = _make_agent()

        # Simulate no image attached
        agent._current_media_url = None
        agent._current_media_type = None
        agent._current_conversation_id = "conv-1"
        agent._current_phone_number_id = "ph-1"

        result_str = await agent._execute_tool_call(
            "registrar_pago", {}, "test-client", "sender-1"
        )
        result = json.loads(result_str)

        assert "error" in result
        assert "imagen" in result["error"].lower() or "comprobante" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_registrar_pago_calls_cobros_with_correct_params(self):
        """registrar_pago must pass conversacion_id and media_id (not conversation_id / media_url)."""
        agent, _, _ = _make_agent()

        agent._current_media_url = "https://example.com/img.jpg"
        agent._current_media_type = "image/jpeg"
        agent._current_conversation_id = "conv-42"
        agent._current_phone_number_id = "phone-99"

        cobros_mock = AsyncMock()
        cobros_mock.registrar_pago = AsyncMock(return_value={"success": True, "outcome": "valid", "message": "ok"})
        agent.cobros = cobros_mock

        await agent._execute_tool_call("registrar_pago", {}, "client-1", "sender-1")

        cobros_mock.registrar_pago.assert_awaited_once_with(
            client_id="client-1",
            sender_id="sender-1",
            conversacion_id="conv-42",
            media_id="https://example.com/img.jpg",
            phone_number_id="phone-99",
        )

    @pytest.mark.asyncio
    async def test_registrar_pago_module_unavailable_returns_error(self):
        """Tool returns graceful error when cobros module is None."""
        agent, _, _ = _make_agent()
        agent.cobros = None
        agent._current_media_url = "https://example.com/img.jpg"

        result_str = await agent._execute_tool_call(
            "registrar_pago", {}, "client-1", "sender-1"
        )
        result = json.loads(result_str)

        assert "error" in result


# ── enviar_datos_bancarios ──────────────────────────────────────────────────

class TestEnviarDatosBancarios:
    """Unit tests for CobrosModule.enviar_datos_bancarios."""

    def _make_cobros(self, supabase_response=None):
        from modulos.cobros import CobrosModule

        mock_supabase = MagicMock()
        mock_openai = AsyncMock()

        table_mock = MagicMock()
        select_mock = MagicMock()
        eq_mock = MagicMock()
        limit_mock = MagicMock()

        if supabase_response is None:
            limit_mock.execute.return_value = MagicMock(data=[])
        else:
            limit_mock.execute.return_value = MagicMock(data=supabase_response)

        table_mock.select.return_value = select_mock
        select_mock.eq.return_value = eq_mock
        eq_mock.eq.return_value = eq_mock
        eq_mock.limit.return_value = limit_mock
        mock_supabase.table.return_value = table_mock

        module = CobrosModule(mock_supabase, mock_openai)
        return module, mock_supabase

    @pytest.mark.asyncio
    async def test_no_bank_data_returns_error_message(self):
        """If datos_bancarios is empty, returns friendly error, not exception."""
        module, _ = self._make_cobros(supabase_response=[])

        result = await module.enviar_datos_bancarios("client-1", "sender-1")

        assert result["exito"] is False
        assert "datos bancarios" in result["mensaje"].lower() or "configurado" in result["mensaje"].lower()

    @pytest.mark.asyncio
    async def test_valid_bank_data_formats_message(self):
        """Valid bank record produces formatted WhatsApp message."""
        bank_data = [{
            "banco": "Banco Pichincha",
            "tipo_cuenta": "ahorros",
            "numero_cuenta": "123456789",
            "titular": "LanLabs SAS",
            "ruc": "1234567890001",
        }]
        module, _ = self._make_cobros(supabase_response=bank_data)

        result = await module.enviar_datos_bancarios("client-1", "sender-1", monto_esperado=149.0)

        assert result["exito"] is True
        assert "Banco Pichincha" in result["mensaje"]
        assert "123456789" in result["mensaje"]
        assert "LanLabs SAS" in result["mensaje"]
        assert "149.00" in result["mensaje"]

    @pytest.mark.asyncio
    async def test_stores_pending_amount_in_redis(self):
        """Expected amount is stored in Redis with 24h TTL."""
        bank_data = [{
            "banco": "Banco Guayaquil",
            "tipo_cuenta": "corriente",
            "numero_cuenta": "987654321",
            "titular": "Test Corp",
            "ruc": None,
        }]
        module, _ = self._make_cobros(supabase_response=bank_data)
        redis_mock = AsyncMock()
        redis_mock.setex = AsyncMock()
        module.redis = redis_mock

        await module.enviar_datos_bancarios("client-1", "sender-1", monto_esperado=249.0)

        redis_mock.setex.assert_awaited_once_with(
            "cobros:pending:client-1:sender-1",
            86400,
            "249.0",
        )


# ── auth: JWT secret validation ─────────────────────────────────────────────

class TestAuthManagerSecretValidation:
    """JWT secret must not be empty — prevents signing with blank key."""

    def test_empty_jwt_secret_raises(self):
        from seguridad.auth import AuthManager
        from unittest.mock import MagicMock
        import pytest

        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            AuthManager(
                supabase_client=MagicMock(),
                jwt_secret="",
            )

    def test_none_jwt_secret_without_env_raises(self):
        from seguridad.auth import AuthManager
        from unittest.mock import MagicMock
        import os

        original = os.environ.pop("JWT_SECRET_KEY", None)
        try:
            with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
                AuthManager(supabase_client=MagicMock())
        finally:
            if original is not None:
                os.environ["JWT_SECRET_KEY"] = original
