"""
Tests for SeguimientoModule: duplicate prevention, follow-up logic,
and the "stuck in follow-up" regression.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CLIENTE_ID = "cliente-test-001"
PHONE = "+593999111222"


def make_supabase(leads=None, conversaciones=None, alertas=None, citas=None):
    """Create a mock Supabase client with configurable return data."""
    sb = MagicMock()

    def table(name):
        tbl = MagicMock()
        data_map = {
            "leads": leads or [],
            "conversaciones": conversaciones or [],
            "alertas": alertas or [],
            "citas": citas or [],
        }

        def select(*args):
            sel = MagicMock()

            def eq(*a):
                return sel

            def lt(*a):
                return sel

            def gte(*a):
                return sel

            def neq(*a):
                return sel

            def order(*a, **kw):
                return sel

            def limit(*a):
                inner = MagicMock()
                inner.execute.return_value.data = data_map.get(name, [])
                return inner

            sel.eq = eq
            sel.lt = lt
            sel.gte = gte
            sel.neq = neq
            sel.order = order
            sel.limit = limit
            return sel

        def insert(data):
            ins = MagicMock()
            ins.execute.return_value.data = [data]
            return ins

        def update(data):
            upd = MagicMock()
            upd.eq = lambda *a: upd
            upd.execute.return_value.data = [data]
            return upd

        tbl.select = select
        tbl.insert = insert
        tbl.update = update
        return tbl

    sb.table = table
    return sb


class TestSeguimientoNoDuplicado:

    @pytest.mark.asyncio
    async def test_no_envia_seguimiento_frio_dos_veces(self):
        """
        Si ya se envió un seguimiento_frio en las últimas 24h,
        NO debe enviarse otro.
        """
        from modulos.seguimiento import SeguimientoModule

        hace_25h = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        leads = [{"id": "lead-001", "nombre": "Juan", "telefono": PHONE}]
        conversaciones = [{"fecha_ultimo_mensaje": hace_25h}]
        # Alerta reciente (hace 1h) — indica que ya se envió
        hace_1h = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        alertas_recientes = [{
            "tipo": "seguimiento_frio",
            "referencia_id": "lead-001",
            "created_at": hace_1h,
        }]

        sb = make_supabase(
            leads=leads,
            conversaciones=conversaciones,
            alertas=alertas_recientes,
        )
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)) as mock_send:
            with patch.object(module, "_ya_enviado", new=AsyncMock(return_value=True)):
                enviados = await module._verificar_prospectos_frios(CLIENTE_ID)

        assert enviados == 0, "No debe enviar duplicado en ventana de 24h"
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_envia_seguimiento_frio_primera_vez(self):
        """
        Lead frío sin seguimiento previo → debe enviar mensaje.
        """
        from modulos.seguimiento import SeguimientoModule

        hace_30h = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        leads = [{"id": "lead-002", "nombre": "Ana", "telefono": PHONE}]
        conversaciones = [{"fecha_ultimo_mensaje": hace_30h}]

        sb = make_supabase(leads=leads, conversaciones=conversaciones)
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)):
            with patch.object(module, "_ya_enviado", new=AsyncMock(return_value=False)):
                with patch.object(module, "_guardar_alerta_enviada", new=AsyncMock()):
                    enviados = await module._verificar_prospectos_frios(CLIENTE_ID)

        assert enviados == 1

    @pytest.mark.asyncio
    async def test_no_envia_seguimiento_a_lead_reciente(self):
        """
        Lead que habló hace menos de 24h NO debe recibir seguimiento frío.
        """
        from modulos.seguimiento import SeguimientoModule

        hace_2h = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        leads = [{"id": "lead-003", "nombre": "Carlos", "telefono": PHONE}]
        conversaciones = [{"fecha_ultimo_mensaje": hace_2h}]

        sb = make_supabase(leads=leads, conversaciones=conversaciones)
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)) as mock_send:
            with patch.object(module, "_ya_enviado", new=AsyncMock(return_value=False)):
                enviados = await module._verificar_prospectos_frios(CLIENTE_ID)

        assert enviados == 0
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_envia_seguimiento_caliente_dos_veces_en_24h(self):
        """
        Lead caliente (score >= 7) no debe recibir más de 1 seguimiento en 24h.
        """
        from modulos.seguimiento import SeguimientoModule

        hace_3h = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        leads = [{"id": "lead-004", "nombre": "Lucía", "telefono": PHONE, "score": 8}]
        conversaciones = [{"fecha_ultimo_mensaje": hace_3h}]

        sb = make_supabase(leads=leads, conversaciones=conversaciones)
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)) as mock_send:
            with patch.object(module, "_ya_enviado", new=AsyncMock(return_value=True)):
                enviados = await module._verificar_leads_calientes(CLIENTE_ID)

        assert enviados == 0
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_recordatorio_cita_24h_no_duplicado(self):
        """
        Recordatorio de cita 24h no debe enviarse si ya se marcó recordatorio_24h_enviado=True.
        """
        from modulos.seguimiento import SeguimientoModule

        mañana = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        citas = []  # No citas con recordatorio_24h_enviado=False

        sb = make_supabase(citas=citas)
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)) as mock_send:
            enviados = await module._verificar_recordatorio_cita_24h(CLIENTE_ID)

        assert enviados == 0
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_lead_sin_telefono_se_omite(self):
        """Leads sin teléfono no deben causar errores ni envíos."""
        from modulos.seguimiento import SeguimientoModule

        hace_30h = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        leads = [{"id": "lead-005", "nombre": "Sin Tel", "telefono": None}]
        conversaciones = [{"fecha_ultimo_mensaje": hace_30h}]

        sb = make_supabase(leads=leads, conversaciones=conversaciones)
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)) as mock_send:
            enviados = await module._verificar_prospectos_frios(CLIENTE_ID)

        assert enviados == 0
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_supabase_no_crashea(self):
        """Error de Supabase en seguimientos no debe propagar excepción."""
        from modulos.seguimiento import SeguimientoModule

        sb = MagicMock()
        sb.table.side_effect = Exception("Supabase connection error")
        module = SeguimientoModule(supabase_client=sb)

        # Should not raise; should return 0
        result = await module._verificar_prospectos_frios(CLIENTE_ID)
        assert result == 0

    @pytest.mark.asyncio
    async def test_verificar_todos_retorna_dict_completo(self):
        """verificar_seguimientos_pendientes siempre retorna dict con 6 llaves."""
        from modulos.seguimiento import SeguimientoModule

        sb = make_supabase()
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_verificar_prospectos_frios", new=AsyncMock(return_value=0)):
            with patch.object(module, "_verificar_leads_calientes", new=AsyncMock(return_value=0)):
                with patch.object(module, "_verificar_recordatorio_cita_24h", new=AsyncMock(return_value=0)):
                    with patch.object(module, "_verificar_recordatorio_cita_1h", new=AsyncMock(return_value=0)):
                        with patch.object(module, "_verificar_post_venta", new=AsyncMock(return_value=0)):
                            with patch.object(module, "_verificar_reactivacion", new=AsyncMock(return_value=0)):
                                result = await module.verificar_seguimientos_pendientes(CLIENTE_ID)

        expected_keys = {"frios", "calientes", "cita_24h", "cita_1h", "post_venta", "reactivacion"}
        assert set(result.keys()) == expected_keys
