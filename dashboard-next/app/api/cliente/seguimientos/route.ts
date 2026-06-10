import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

const SEGUIMIENTO_TIPOS = [
  'seguimiento_frio',
  'seguimiento_caliente',
  'seguimiento_post_venta',
  'reactivacion',
] as const

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const clienteId = session.cliente_id

    const { data: alertas, error } = await supabase
      .from('alertas')
      .select('id, tipo, referencia_id, mensaje, canal_envio, created_at')
      .eq('cliente_id', clienteId)
      .in('tipo', SEGUIMIENTO_TIPOS)
      .order('created_at', { ascending: false })
      .limit(500)

    if (error) {
      console.error('[SEGUIMIENTOS] Error fetching alertas:', error)
      if (error.code === '42P01' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [], stats: buildEmptyStats() })
      }
      throw error
    }

    const { count: recordatorios24h } = await supabase
      .from('citas')
      .select('id', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .eq('recordatorio_24h_enviado', true)

    const { count: recordatorios1h } = await supabase
      .from('citas')
      .select('id', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .eq('recordatorio_1h_enviado', true)

    const stats: Record<string, number> = {
      seguimiento_frio: 0,
      seguimiento_caliente: 0,
      seguimiento_post_venta: 0,
      reactivacion: 0,
      cita_24h: recordatorios24h ?? 0,
      cita_1h: recordatorios1h ?? 0,
    }

    for (const alerta of alertas ?? []) {
      if (alerta.tipo in stats) stats[alerta.tipo]++
    }

    stats.total = Object.values(stats).reduce((a, b) => a + b, 0)

    return NextResponse.json({ success: true, data: alertas ?? [], stats })
  } catch (error) {
    console.error('[SEGUIMIENTOS] Error:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch seguimientos' }, { status: 500 })
  }
}

function buildEmptyStats() {
  return {
    seguimiento_frio: 0,
    seguimiento_caliente: 0,
    seguimiento_post_venta: 0,
    reactivacion: 0,
    cita_24h: 0,
    cita_1h: 0,
    total: 0,
  }
}
