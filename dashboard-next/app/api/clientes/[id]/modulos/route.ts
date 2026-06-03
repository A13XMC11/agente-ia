import { NextResponse } from 'next/server'
import { getUserRole } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'

const MODULE_COLUMNS = [
  'ventas', 'agendamiento', 'cobros', 'links_pago',
  'calificacion', 'campanas', 'analytics', 'alertas', 'seguimientos', 'documentos',
] as const

type ModuleId = typeof MODULE_COLUMNS[number]

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const role = await getUserRole()
    if (role !== 'super_admin' && role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 403 })
    }

    const { id } = await params

    const { data, error } = await supabase
      .from('modulos_activos')
      .select(MODULE_COLUMNS.join(', '))
      .eq('cliente_id', id)
      .limit(1)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return NextResponse.json({
          success: true,
          data: MODULE_COLUMNS.map(col => ({ id: col, activo: false })),
        })
      }
      throw error
    }

    const row = data as unknown as Record<string, boolean>
    const modules = MODULE_COLUMNS.map(col => ({
      id: col,
      activo: Boolean(row[col]),
    }))

    return NextResponse.json({ success: true, data: modules })
  } catch (error) {
    console.error('Error fetching modulos:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch modulos' }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const role = await getUserRole()
    if (role !== 'super_admin' && role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 403 })
    }

    const { id } = await params
    const { modulo_id, activo } = await request.json()

    if (!MODULE_COLUMNS.includes(modulo_id as ModuleId)) {
      return NextResponse.json({ success: false, error: 'Invalid modulo_id' }, { status: 400 })
    }

    const { error } = await supabase
      .from('modulos_activos')
      .upsert(
        { cliente_id: id, [modulo_id]: activo },
        { onConflict: 'cliente_id' }
      )

    if (error) throw error

    return NextResponse.json({ success: true, data: { id: modulo_id, activo } })
  } catch (error) {
    console.error('Error updating modulo:', error)
    return NextResponse.json({ success: false, error: 'Failed to update modulo' }, { status: 500 })
  }
}
