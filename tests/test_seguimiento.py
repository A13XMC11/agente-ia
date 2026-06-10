"""
Tests for SeguimientoModule: duplicate prevention, follow-up logic,
and the "stuck in follow-up" regression.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CLIENTE_ID = "cliente-test-001"
PHONE = "+593999111222"
INFO = {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}


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
                enviados = await module._verificar_prospectos_frios(CLIENTE_ID, INFO)

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
                    enviados = await module._verificar_prospectos_frios(CLIENTE_ID, INFO)

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
                enviados = await module._verificar_prospectos_frios(CLIENTE_ID, INFO)

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
                enviados = await module._verificar_leads_calientes(CLIENTE_ID, INFO)

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
            enviados = await module._verificar_recordatorio_cita_24h(CLIENTE_ID, INFO)

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
            enviados = await module._verificar_prospectos_frios(CLIENTE_ID, INFO)

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
        result = await module._verificar_prospectos_frios(CLIENTE_ID, INFO)
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


class TestHorarioEnvio:

    def test_dentro_de_horario(self):
        """Hora 10:00 local debe estar dentro del horario permitido."""
        from modulos.seguimiento import SeguimientoModule

        module = SeguimientoModule(supabase_client=MagicMock())
        with patch("modulos.seguimiento.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.hour = 10
            mock_dt.now.return_value = mock_now
            assert module._esta_en_horario_envio("America/Guayaquil") is True

    def test_fuera_de_horario_madrugada(self):
        """Hora 02:00 local debe estar fuera del horario permitido."""
        from modulos.seguimiento import SeguimientoModule

        module = SeguimientoModule(supabase_client=MagicMock())
        with patch("modulos.seguimiento.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.hour = 2
            mock_dt.now.return_value = mock_now
            assert module._esta_en_horario_envio("America/Guayaquil") is False

    def test_fuera_de_horario_noche(self):
        """Hora 21:00 local (inclusive) debe estar fuera del horario permitido."""
        from modulos.seguimiento import SeguimientoModule

        module = SeguimientoModule(supabase_client=MagicMock())
        with patch("modulos.seguimiento.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.hour = 21
            mock_dt.now.return_value = mock_now
            assert module._esta_en_horario_envio("America/Guayaquil") is False

    @pytest.mark.asyncio
    async def test_no_envia_frio_fuera_de_horario(self):
        """Prospectos fríos no deben enviarse fuera de horario."""
        from modulos.seguimiento import SeguimientoModule

        sb = make_supabase(leads=[{"id": "lead-1", "nombre": "Test", "telefono": PHONE}])
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_esta_en_horario_envio", return_value=False):
            result = await module._verificar_prospectos_frios(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_envia_caliente_fuera_de_horario(self):
        """Leads calientes no deben enviarse fuera de horario."""
        from modulos.seguimiento import SeguimientoModule

        sb = make_supabase(leads=[{"id": "lead-1", "nombre": "Test", "telefono": PHONE}])
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_esta_en_horario_envio", return_value=False):
            result = await module._verificar_leads_calientes(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )
        assert result == 0


class TestPostVenta:

    @pytest.mark.asyncio
    async def test_no_envia_post_venta_fuera_de_ventana(self):
        """Post-venta no se envía si el pago tiene más de 25h o menos de 23h."""
        from modulos.seguimiento import SeguimientoModule

        now = datetime.now(timezone.utc)
        pago_reciente = {"id": "pago-1", "sender_telefono": PHONE, "created_at": now.isoformat()}
        pago_viejo = {"id": "pago-2", "sender_telefono": PHONE, "created_at": (now - timedelta(hours=48)).isoformat()}
        sb = make_supabase()
        # Override pagos data
        orig_table = sb.table

        def table_override(name):
            tbl = orig_table(name)
            if name == "pagos":
                tbl.select = lambda *a: _chain_result(tbl, [pago_reciente, pago_viejo])
            return tbl

        sb.table = table_override
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_esta_en_horario_envio", return_value=True), \
             patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)), \
             patch.object(module, "_ya_enviado", new=AsyncMock(return_value=False)):
            result = await module._verificar_post_venta(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )

        # Neither pago is in the 23-25h window so nothing should send
        assert result == 0

    @pytest.mark.asyncio
    async def test_envia_post_venta_en_ventana(self):
        """Post-venta sí se envía cuando el pago está en la ventana 23-25h."""
        from modulos.seguimiento import SeguimientoModule

        now = datetime.now(timezone.utc)
        pago_en_ventana = {
            "id": "pago-3",
            "sender_telefono": PHONE,
            "created_at": (now - timedelta(hours=24)).isoformat(),
        }
        sb = make_supabase()
        orig_table = sb.table

        def table_override(name):
            tbl = orig_table(name)
            if name == "pagos":
                tbl.select = lambda *a: _chain_result(tbl, [pago_en_ventana])
            return tbl

        sb.table = table_override
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_esta_en_horario_envio", return_value=True), \
             patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)), \
             patch.object(module, "_ya_enviado", new=AsyncMock(return_value=False)), \
             patch.object(module, "_guardar_alerta_enviada", new=AsyncMock()), \
             patch.object(module, "_obtener_nombre_usuario", new=AsyncMock(return_value="Cliente")):
            result = await module._verificar_post_venta(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )

        assert result == 1


class TestReactivacion:

    @pytest.mark.asyncio
    async def test_no_envia_reactivacion_duplicada(self):
        """Reactivación no se reenvía si ya fue enviada en las últimas 168h."""
        from modulos.seguimiento import SeguimientoModule

        conv = {"id": "conv-1", "usuario_id": PHONE, "canal": "whatsapp", "usuario_nombre": "Juan"}
        sb = make_supabase(conversaciones=[conv])
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_esta_en_horario_envio", return_value=True), \
             patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)), \
             patch.object(module, "_ya_enviado", new=AsyncMock(return_value=True)):
            result = await module._verificar_reactivacion(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )

        assert result == 0

    @pytest.mark.asyncio
    async def test_envia_reactivacion_primera_vez(self):
        """Reactivación sí se envía cuando la conversación lleva +7 días inactiva."""
        from modulos.seguimiento import SeguimientoModule

        conv = {"id": "conv-2", "usuario_id": PHONE, "canal": "whatsapp", "usuario_nombre": "Ana"}
        sb = make_supabase(conversaciones=[conv])
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "_esta_en_horario_envio", return_value=True), \
             patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)), \
             patch.object(module, "_ya_enviado", new=AsyncMock(return_value=False)), \
             patch.object(module, "_guardar_alerta_enviada", new=AsyncMock()):
            result = await module._verificar_reactivacion(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )

        assert result == 1


class TestRecordatorio1h:

    @pytest.mark.asyncio
    async def test_no_envia_recordatorio_1h_si_cita_en_2h(self):
        """Recordatorio 1h no se envía si la cita es en más de 1h."""
        from modulos.seguimiento import SeguimientoModule

        now = datetime.now(timezone.utc)
        hora_en_2h = (now + timedelta(hours=2)).strftime("%H:%M")
        cita = {
            "id": "cita-1",
            "nombre_cliente": "Pedro",
            "hora": hora_en_2h,
            "telefono_cliente": PHONE,
            "fecha": now.date().isoformat(),
            "estado": "confirmada",
            "recordatorio_1h_enviado": False,
        }
        sb = make_supabase(citas=[cita])
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)):
            result = await module._verificar_recordatorio_cita_1h(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )

        assert result == 0

    @pytest.mark.asyncio
    async def test_envia_recordatorio_1h_en_ventana(self):
        """Recordatorio 1h sí se envía cuando la cita es dentro de los próximos 60 min."""
        from modulos.seguimiento import SeguimientoModule

        now = datetime.now(timezone.utc)
        hora_en_45min = (now + timedelta(minutes=45)).strftime("%H:%M")
        cita = {
            "id": "cita-2",
            "nombre_cliente": "Laura",
            "hora": hora_en_45min,
            "telefono_cliente": PHONE,
            "fecha": now.date().isoformat(),
            "estado": "confirmada",
            "recordatorio_1h_enviado": False,
        }
        sb = make_supabase(citas=[cita])

        # Need update mock on citas
        def make_update_chain():
            upd = MagicMock()
            upd.eq = lambda *a: upd
            upd.execute.return_value.data = []
            return upd

        orig_table = sb.table

        def table_with_update(name):
            tbl = orig_table(name)
            tbl.update = lambda *a, **kw: make_update_chain()
            return tbl

        sb.table = table_with_update
        module = SeguimientoModule(supabase_client=sb)

        with patch.object(module, "enviar_seguimiento", new=AsyncMock(return_value=True)):
            result = await module._verificar_recordatorio_cita_1h(
                CLIENTE_ID, {"agente_nombre": "Sofia", "empresa": "LanLabs", "timezone": "America/Guayaquil"}
            )

        assert result == 1


# ── Helpers for table overrides ─────────────────

def _chain_result(tbl: MagicMock, data: list):
    """Return a mock chain whose .limit().execute().data == data."""
    sel = MagicMock()
    sel.eq = lambda *a: sel
    sel.gte = lambda *a: sel
    sel.lte = lambda *a: sel
    sel.lt = lambda *a: sel
    sel.order = lambda *a, **kw: sel
    sel.limit = lambda *a: _execute_result(data)
    tbl.select = lambda *a: sel
    return sel


def _execute_result(data: list):
    inner = MagicMock()
    inner.execute.return_value.data = data
    return inner
