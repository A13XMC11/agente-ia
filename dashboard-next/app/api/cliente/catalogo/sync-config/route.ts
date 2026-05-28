import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('catalog_sync_config')
      .select('*')
      .eq('cliente_id', session.cliente_id)
      .single()

    if (error && error.code !== 'PGRST116') throw error

    return NextResponse.json({ success: true, data: data || null })
  } catch (error) {
    console.error('[SYNC-CONFIG] GET error:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener configuración' }, { status: 500 })
  }
}

export async function PUT(req: NextRequest) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const { tipo, sheets_url, webhook_url, sync_interval_minutes } = body

    if (!['manual', 'sheets', 'webhook'].includes(tipo)) {
      return NextResponse.json({ success: false, error: 'tipo inválido' }, { status: 400 })
    }
    if (tipo === 'sheets' && !sheets_url?.trim()) {
      return NextResponse.json({ success: false, error: 'URL de Google Sheets requerida' }, { status: 400 })
    }
    if (tipo === 'webhook' && !webhook_url?.trim()) {
      return NextResponse.json({ success: false, error: 'URL del webhook requerida' }, { status: 400 })
    }

    const row = {
      cliente_id: session.cliente_id,
      tipo,
      sheets_url: sheets_url?.trim() || null,
      webhook_url: webhook_url?.trim() || null,
      sync_interval_minutes: Number(sync_interval_minutes) || 60,
      activo: true,
      updated_at: new Date().toISOString(),
    }

    const { data, error } = await supabase
      .from('catalog_sync_config')
      .upsert(row, { onConflict: 'cliente_id' })
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('[SYNC-CONFIG] PUT error:', error)
    return NextResponse.json({ success: false, error: 'Error al guardar configuración' }, { status: 500 })
  }
}
