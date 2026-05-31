import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

const MODULE_COLUMNS = [
  'ventas', 'agendamiento', 'cobros', 'links_pago',
  'calificacion', 'campanas', 'alertas', 'seguimientos', 'documentos',
] as const

type ModuleId = typeof MODULE_COLUMNS[number]

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('modulos_activos')
      .select(MODULE_COLUMNS.join(', '))
      .eq('cliente_id', session.cliente_id)
      .limit(1)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        // No row yet — return all modules as inactive
        return NextResponse.json({
          success: true,
          data: MODULE_COLUMNS.map(id => ({ id, activo: false })),
        })
      }
      throw error
    }

    const modules = MODULE_COLUMNS.map(id => ({
      id,
      activo: Boolean((data as Record<ModuleId, boolean>)[id]),
    }))

    return NextResponse.json({ success: true, data: modules })
  } catch (error) {
    console.error('Error fetching modulos:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch modulos' }, { status: 500 })
  }
}

export async function PUT(request: Request) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { modulo_id, activo } = await request.json()

    if (!MODULE_COLUMNS.includes(modulo_id as ModuleId)) {
      return NextResponse.json({ success: false, error: 'Invalid modulo_id' }, { status: 400 })
    }

    const { data, error } = await supabase
      .from('modulos_activos')
      .upsert(
        { cliente_id: session.cliente_id, [modulo_id]: activo },
        { onConflict: 'cliente_id' }
      )
      .select(MODULE_COLUMNS.join(', '))
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data: { id: modulo_id, activo } })
  } catch (error) {
    console.error('Error updating modulo:', error)
    return NextResponse.json({ success: false, error: 'Failed to update modulo' }, { status: 500 })
  }
}
