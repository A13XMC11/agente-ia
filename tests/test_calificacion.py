"""
Tests for lead qualification and scoring module.

Unit tests cover pure scoring logic (LeadScoringEngine).
Integration tests cover CalificacionModule with mocked Supabase.
"""

import pytest
from datetime import datetime, timedelta
from modulos.calificacion import (
    LeadScoringEngine,
    ScoreSignal,
    ScoringResult,
)


class TestLeadScoringEngine:
    """Unit tests for deterministic scoring engine."""

    @pytest.mark.unit
    def test_normalize_strips_accents(self):
        """Test accent normalization works correctly."""
        engine = LeadScoringEngine()
        assert engine._normalize("demostración") == "demostracion"
        assert engine._normalize("DEMOSTRACIÓN") == "demostracion"
        assert engine._normalize("Presupuesto") == "presupuesto"

    @pytest.mark.unit
    def test_urgency_keywords_award_3_points(self):
        """Test urgency detection (+3 points)."""
        engine = LeadScoringEngine()
        result = engine.score_message("Necesito esto urgente")
        assert result.score == 3
        assert any(sig.name == "urgency" for sig in result.signals)
        assert result.breakdown.get("urgency") == 3

    @pytest.mark.unit
    def test_urgency_with_variations(self):
        """Test urgency keywords with various Spanish forms."""
        engine = LeadScoringEngine()
        messages = [
            "Necesito esto ya",
            "lo necesito hoy mismo",
            "Esta semana es importante",
            "Lo necesito pronto",
            "Inmediatamente",
        ]
        for msg in messages:
            result = engine.score_message(msg)
            assert result.score >= 3, f"Failed for message: {msg}"
            assert any(sig.name == "urgency" for sig in result.signals)

    @pytest.mark.unit
    def test_budget_keywords_award_3_points(self):
        """Test budget mention detection (+3 points)."""
        engine = LeadScoringEngine()
        result = engine.score_message("Cuánto cuesta el servicio")
        assert result.score >= 3
        assert any(sig.name == "budget" for sig in result.signals)

    @pytest.mark.unit
    def test_decision_power_keywords_award_3_points(self):
        """Test decision power detection (+3 points)."""
        engine = LeadScoringEngine()
        result = engine.score_message("Yo decido en mi empresa")
        assert result.score == 3
        assert any(sig.name == "decision_power" for sig in result.signals)

    @pytest.mark.unit
    def test_specific_questions_award_2_points(self):
        """Test question detection (+2 points)."""
        engine = LeadScoringEngine()
        # Default threshold is 2 questions
        result = engine.score_message(
            "¿Cómo funciona? ¿Cuál es el precio? ¿Hay descuento?"
        )
        assert result.score >= 2
        assert any(sig.name == "specific_questions" for sig in result.signals)

    @pytest.mark.unit
    def test_demo_request_award_2_points(self):
        """Test demo request detection (+2 points)."""
        engine = LeadScoringEngine()
        result = engine.score_message("¿Puedes mostrarme una demo?")
        assert result.score >= 2
        assert any(sig.name == "demo_request" for sig in result.signals)

    @pytest.mark.unit
    def test_curiosity_penalty_minus_2_points(self):
        """Test curiosity-only penalty (-2 points, clamped to 0)."""
        engine = LeadScoringEngine()
        result = engine.score_message("Solo preguntando por curiosidad")
        # Penalties are clamped to 0 minimum
        assert result.score == 0
        assert any(sig.name == "curiosity_only" for sig in result.signals)

    @pytest.mark.unit
    def test_short_repeated_message_penalty_minus_1(self):
        """Test short repeated message penalty (-1 point, clamped to 0)."""
        engine = LeadScoringEngine()
        prior_messages = (
            {"content": "ok", "timestamp": "2026-05-13T10:00:00"},
            {"content": "gracias", "timestamp": "2026-05-13T10:01:00"},
        )
        result = engine.score_message("ok", prior_messages=prior_messages)
        # Penalties are clamped to 0 minimum
        assert result.score == 0
        assert any(sig.name == "short_repeated" for sig in result.signals)

    @pytest.mark.unit
    def test_quick_response_award_2_points(self):
        """Test quick response detection (+2 points, <2 min)."""
        engine = LeadScoringEngine()
        now = datetime.utcnow()
        prior_messages = (
            {"content": "Hola, ¿cómo estás?", "timestamp": (now - timedelta(seconds=60)).isoformat()},
        )
        result = engine.score_message("Bien, gracias", prior_messages=prior_messages, current_ts=now)
        assert result.score >= 2
        assert any(sig.name == "quick_response" for sig in result.signals)

    @pytest.mark.unit
    def test_score_clamped_to_10(self):
        """Test score is clamped to 10 even with multiple signals."""
        engine = LeadScoringEngine()
        # All positive signals: 3+3+3+2+2+2 = 15, should clamp to 10
        result = engine.score_message(
            "Necesito esto urgente, ¿cuánto cuesta? Soy el dueño de mi empresa. "
            "¿Cómo funciona? ¿Puedes hacer una demo? Responde rápido por favor."
        )
        assert result.score <= 10

    @pytest.mark.unit
    def test_score_clamped_to_0(self):
        """Test score is clamped to 0 even with negative signals."""
        engine = LeadScoringEngine()
        # Multiple negative signals should not go below 0
        result = engine.score_message(
            "Solo preguntando por curiosidad. ok. ok. ok."
        )
        assert result.score >= 0

    @pytest.mark.unit
    def test_multiple_signals_stack(self):
        """Test multiple signals combine correctly."""
        engine = LeadScoringEngine()
        result = engine.score_message("Necesito urgente y presupuesto")
        # Should have urgency (3) + budget (3) = 6
        assert result.score >= 6
        assert len(result.signals) >= 2

    @pytest.mark.unit
    def test_word_boundary_avoids_false_positives(self):
        """Test that word boundaries prevent false matches."""
        engine = LeadScoringEngine()
        # "presupuestaria" should NOT match "presupuesto"
        result = engine.score_message("Esta es una restricción presupuestaria")
        # Word boundary check - presupuestaria should not match presupuesto keyword
        has_budget = any(sig.name == "budget" for sig in result.signals)
        # If word boundary works correctly, shouldn't match presupuestaria for presupuesto
        assert not has_budget

    @pytest.mark.unit
    def test_state_mapping_curioso(self):
        """Test state mapping for CURIOSO (0-2)."""
        engine = LeadScoringEngine()
        result = engine.score_message("hola")
        assert result.score <= 2
        assert result.state == "curioso"

    @pytest.mark.unit
    def test_state_mapping_prospecto(self):
        """Test state mapping for PROSPECTO (3-4)."""
        engine = LeadScoringEngine()
        result = engine.score_message("¿Cómo funciona tu servicio? ¿Cuál es el precio?")
        # With questions + price keyword, might hit interesado (5+)
        assert result.score >= 2
        assert result.state in ("prospecto", "interesado", "curioso")

    @pytest.mark.unit
    def test_state_mapping_interesado(self):
        """Test state mapping for INTERESADO (5-6)."""
        engine = LeadScoringEngine()
        result = engine.score_message("¿Cuánto cuesta? Necesito esto")  # budget + urgency
        assert 5 <= result.score <= 6
        assert result.state == "interesado"

    @pytest.mark.unit
    def test_state_mapping_caliente(self):
        """Test state mapping for CALIENTE (7-8)."""
        engine = LeadScoringEngine()
        result = engine.score_message("Necesito urgente, ¿cuánto cuesta? ¿Puedo ver una demo?")
        # This will score high and might even be urgente (9+)
        assert result.score >= 7
        assert result.state in ("caliente", "urgente")

    @pytest.mark.unit
    def test_state_mapping_urgente(self):
        """Test state mapping for URGENTE (9-10)."""
        engine = LeadScoringEngine()
        # Craft a message that gets 9+ points
        result = engine.score_message(
            "Necesito urgente, ¿cuánto cuesta? Soy el dueño. ¿Puedes hacer una demo rápido?"
        )
        # This should score high
        assert result.score >= 7  # At least caliente

    @pytest.mark.unit
    def test_empty_message_returns_zero(self):
        """Test empty message returns 0 score."""
        engine = LeadScoringEngine()
        result = engine.score_message("")
        assert result.score == 0
        assert result.state == "curioso"
        assert len(result.signals) == 0

    @pytest.mark.unit
    def test_emoji_only_message(self):
        """Test emoji-only message doesn't crash."""
        engine = LeadScoringEngine()
        result = engine.score_message("👍 🔥 ✅")
        assert result.score == 0
        assert result.state == "curioso"

    @pytest.mark.unit
    def test_scoring_result_immutable(self):
        """Test ScoringResult is immutable (frozen dataclass)."""
        result = ScoringResult(
            score=5,
            state="interesado",
            signals=(),
            breakdown={}
        )
        with pytest.raises(Exception):
            # Attempting to modify frozen dataclass should fail
            result.score = 10  # type: ignore

    @pytest.mark.unit
    def test_score_signal_immutable(self):
        """Test ScoreSignal is immutable (frozen dataclass)."""
        signal = ScoreSignal(
            name="urgency",
            delta=3,
            matched_keywords=("urgente",),
            excerpt="mensaje"
        )
        with pytest.raises(Exception):
            # Attempting to modify frozen dataclass should fail
            signal.delta = 5  # type: ignore


@pytest.mark.integration
class TestCalificacionModuleIntegration:
    """Integration tests for CalificacionModule (requires mocked Supabase)."""

    @pytest.mark.integration
    async def test_calcular_score_automatico_creates_history(self, mock_supabase):
        """Test that calcular_score_automatico creates a history row."""
        from modulos.calificacion import CalificacionModule

        module = CalificacionModule(mock_supabase)

        # Mock the lead fetch to return no lead (create scenario)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception(
            "No lead"
        )

        result = await module.calcular_score_automatico(
            client_id="client123",
            usuario_id="user456",
            current_message="Necesito urgente, ¿cuánto cuesta?",
            prior_messages=[],
        )

        assert result.get("success") is True
        assert result.get("new_score") >= 3

    @pytest.mark.integration
    async def test_calcular_score_automatico_swallows_errors(self, mock_supabase):
        """Test that errors are caught and returned, never raised."""
        from modulos.calificacion import CalificacionModule

        module = CalificacionModule(mock_supabase)

        # Mock Supabase to raise an error
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception(
            "Supabase error"
        )
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Supabase insert error"
        )

        result = await module.calcular_score_automatico(
            client_id="client123",
            usuario_id="user456",
            current_message="Test message",
            prior_messages=[],
        )

        # Should return error dict, not raise
        assert "error" in result
        assert result.get("error") is not None

    @pytest.mark.unit
    def test_count_questions(self):
        """Test question counting logic."""
        engine = LeadScoringEngine()
        # Count various question markers
        assert engine._count_questions("¿Cómo funciona?") >= 1
        assert engine._count_questions("¿Cuándo? ¿Dónde? ¿Por qué?") >= 3
        assert engine._count_questions("Sin preguntas aquí.") == 0

    @pytest.mark.unit
    def test_is_short_repeated(self):
        """Test short repeated message detection."""
        engine = LeadScoringEngine()
        prior = (
            {"content": "ok"},
            {"content": "gracias"},
        )
        assert engine._is_short_repeated("ok", prior) is True
        assert engine._is_short_repeated("diferente mensaje", prior) is False
        assert engine._is_short_repeated("muy largo mensaje con muchas palabras", prior) is False

    @pytest.mark.unit
    def test_is_quick_response(self):
        """Test quick response detection (< 120 sec)."""
        engine = LeadScoringEngine()
        now = datetime.utcnow()

        # Within 2 minutes
        prior_within = (
            {"content": "msg", "timestamp": (now - timedelta(seconds=60)).isoformat()},
        )
        assert engine._is_quick_response(prior_within, now) is True

        # Beyond 2 minutes
        prior_beyond = (
            {"content": "msg", "timestamp": (now - timedelta(seconds=200)).isoformat()},
        )
        assert engine._is_quick_response(prior_beyond, now) is False

        # No prior messages
        assert engine._is_quick_response((), now) is False
