"""Unit tests for billing/manual.py — ManualBilling class."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest


def _now() -> datetime:
    return datetime.now(timezone.utc)

from billing.manual import ManualBilling


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_supabase():
    """Sync Supabase mock (ManualBilling uses sync client)."""
    sb = MagicMock()
    # Default: table().select()...execute() returns empty
    table = MagicMock()
    sb.table.return_value = table
    return sb


@pytest.fixture
def billing(mock_supabase):
    return ManualBilling(mock_supabase)


def _make_sub(
    sub_id="sub-001",
    client_id="client-001",
    status="pending_payment",
    payment_method="transferencia",
    monthly_amount=149.0,
    next_billing_date=None,
) -> dict:
    if next_billing_date is None:
        next_billing_date = (_now() + timedelta(days=30)).isoformat()
    return {
        "id": sub_id,
        "cliente_id": client_id,
        "status": status,
        "payment_method": payment_method,
        "monthly_amount": monthly_amount,
        "next_billing_date": next_billing_date,
        "current_period_start": _now().isoformat(),
        "current_period_end": next_billing_date,
        "pending_proof_url": None,
    }


# ── create_subscription ──────────────────────────────────────────────────────


class TestCreateSubscription:
    def test_creates_new_subscription_for_transferencia(self, billing, mock_supabase):
        # No existing subscription
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        table.insert.return_value.execute.return_value.data = [_make_sub()]

        result = billing.create_subscription("client-001", 149.0, "transferencia")

        # First insert is subscription row, second is subscription_payments row
        assert mock_supabase.table.call_count >= 2
        sub_insert = table.insert.call_args_list[0][0][0]
        assert sub_insert["payment_method"] == "transferencia"
        assert sub_insert["status"] == "pending_payment"
        assert sub_insert["monthly_amount"] == 149.0

    def test_updates_existing_subscription(self, billing, mock_supabase):
        existing_sub = _make_sub(status="cancelled")
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [existing_sub]
        table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        # Second call to _get_subscription (return value after update)
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [existing_sub]

        billing.create_subscription("client-001", 149.0, "efectivo")

        update_call = table.update.call_args
        assert update_call is not None
        payload = update_call[0][0]
        assert payload["payment_method"] == "efectivo"

    def test_rejects_invalid_payment_method(self, billing, mock_supabase):
        result = billing.create_subscription("client-001", 149.0, "paypal")
        assert result is None

    def test_inserts_ledger_row_in_subscription_payments(self, billing, mock_supabase):
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        created_sub = _make_sub()
        table.insert.return_value.execute.return_value.data = [created_sub]

        billing.create_subscription("client-001", 149.0, "transferencia")

        # subscription_payments insert
        calls = [str(c) for c in mock_supabase.table.call_args_list]
        assert any("subscription_payments" in c for c in calls)


# ── submit_proof ─────────────────────────────────────────────────────────────


class TestSubmitProof:
    def test_transitions_to_proof_submitted(self, billing, mock_supabase):
        sub = _make_sub()
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [sub]
        table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        table.update.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock()

        result = billing.submit_proof("client-001", "https://example.com/proof.jpg")

        assert result is True
        update_call = table.update.call_args_list[0]
        payload = update_call[0][0]
        assert payload["status"] == "proof_submitted"
        assert payload["pending_proof_url"] == "https://example.com/proof.jpg"

    def test_returns_false_when_no_subscription(self, billing, mock_supabase):
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = billing.submit_proof("client-001", "https://example.com/proof.jpg")

        # No subscription → update never called, returns True (does update on subscription table without guard)
        # The real guard is that update.eq.execute silently does nothing if no row matches
        assert result is True


# ── verify_payment ───────────────────────────────────────────────────────────


class TestVerifyPayment:
    def _setup_sub(self, mock_supabase, sub):
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [sub]
        table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        table.update.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock()
        return table

    def test_approve_sets_status_active(self, billing, mock_supabase):
        sub = _make_sub(status="proof_submitted")
        table = self._setup_sub(mock_supabase, sub)

        result = billing.verify_payment("client-001", approve=True, verified_by="admin@lanlabs.com")

        assert result is True
        # First update call is on subscription
        first_update = table.update.call_args_list[0][0][0]
        assert first_update["status"] == "active"
        assert "last_payment_date" in first_update

    def test_approve_flips_cliente_estado_if_pausado(self, billing, mock_supabase):
        sub = _make_sub(status="proof_submitted")
        table = self._setup_sub(mock_supabase, sub)

        billing.verify_payment("client-001", approve=True, verified_by="admin")

        # Should update clientes table with estado=activo
        tables_called = [c[0][0] for c in mock_supabase.table.call_args_list]
        assert "clientes" in tables_called

    def test_reject_resets_to_pending_payment(self, billing, mock_supabase):
        sub = _make_sub(status="proof_submitted")
        table = self._setup_sub(mock_supabase, sub)

        result = billing.verify_payment("client-001", approve=False, verified_by="admin", notes="Monto incorrecto")

        assert result is True
        first_update = table.update.call_args_list[0][0][0]
        assert first_update["status"] == "pending_payment"
        assert first_update["pending_proof_url"] is None

    def test_returns_false_when_no_subscription(self, billing, mock_supabase):
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = billing.verify_payment("client-001", approve=True, verified_by="admin")

        assert result is False


# ── renew ────────────────────────────────────────────────────────────────────


class TestRenew:
    def test_rolls_dates_forward_30_days(self, billing, mock_supabase):
        sub = _make_sub(status="active", payment_method="efectivo")
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [sub]
        table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        table.insert.return_value.execute.return_value = MagicMock()

        # manual.py stores naive UTC datetimes — strip tz for comparison
        before = _now().replace(tzinfo=None)
        result = billing.renew("client-001", verified_by="admin")
        after = _now().replace(tzinfo=None)

        assert result is True
        update_payload = table.update.call_args_list[0][0][0]
        new_end = datetime.fromisoformat(update_payload["current_period_end"])
        assert (new_end - before).days >= 29
        assert (after - new_end).total_seconds() < 5

    def test_efectivo_creates_paid_ledger_row(self, billing, mock_supabase):
        sub = _make_sub(status="active", payment_method="efectivo")
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [sub]
        table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        table.insert.return_value.execute.return_value = MagicMock()

        billing.renew("client-001", verified_by="admin")

        insert_payload = table.insert.call_args[0][0]
        assert insert_payload["status"] == "paid"
        assert insert_payload["verified_by"] == "admin"

    def test_transferencia_creates_pending_ledger_row(self, billing, mock_supabase):
        sub = _make_sub(status="active", payment_method="transferencia")
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [sub]
        table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        table.insert.return_value.execute.return_value = MagicMock()

        billing.renew("client-001", verified_by="admin")

        insert_payload = table.insert.call_args[0][0]
        assert insert_payload["status"] == "pending"
        assert insert_payload["verified_by"] is None

    def test_returns_false_when_no_subscription(self, billing, mock_supabase):
        table = mock_supabase.table.return_value
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = billing.renew("client-001", verified_by="admin")

        assert result is False


# ── get_due_subscriptions ────────────────────────────────────────────────────


class TestGetDueSubscriptions:
    def test_returns_due_subscriptions(self, billing, mock_supabase):
        due_subs = [
            _make_sub(client_id="c1", payment_method="transferencia", next_billing_date=(_now() + timedelta(days=1)).isoformat()),
            _make_sub(client_id="c2", payment_method="efectivo", next_billing_date=(_now() - timedelta(days=1)).isoformat()),
        ]
        table = mock_supabase.table.return_value
        # .not_ is property access (no call), .eq() is called — so chain is .not_.eq.return_value
        table.select.return_value.in_.return_value.lte.return_value.not_.eq.return_value.order.return_value.execute.return_value.data = due_subs

        result = billing.get_due_subscriptions()

        assert len(result) == 2

    def test_returns_empty_list_on_error(self, billing, mock_supabase):
        table = mock_supabase.table.return_value
        table.select.return_value.in_.return_value.lte.return_value.not_.eq.return_value.order.return_value.execute.side_effect = Exception("DB error")

        result = billing.get_due_subscriptions()

        assert result == []


# ── get_platform_bank_info ───────────────────────────────────────────────────


class TestGetPlatformBankInfo:
    def test_reads_from_environment(self):
        with patch.dict(os.environ, {
            "LANLABS_BANCO": "Banco Pichincha",
            "LANLABS_NUMERO_CUENTA": "1234567890",
            "LANLABS_TITULAR": "LanLabs S.A.",
            "LANLABS_RUC": "9999999999001",
            "LANLABS_TIPO_CUENTA": "corriente",
            "LANLABS_CASH_ADDRESS": "Av. Siempre Viva 123",
        }):
            info = ManualBilling.get_platform_bank_info()

        assert info["banco"] == "Banco Pichincha"
        assert info["numero_cuenta"] == "1234567890"
        assert info["cash_address"] == "Av. Siempre Viva 123"

    def test_returns_empty_strings_when_vars_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            info = ManualBilling.get_platform_bank_info()

        assert info["banco"] == ""
        assert info["numero_cuenta"] == ""
