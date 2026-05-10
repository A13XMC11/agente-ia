import { NextResponse } from 'next/server'
import { getUserRole } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const role = await getUserRole()
    if (role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 403 })
    }

    const { id } = await params

    const { data, error } = await supabase
      .from('modulos_activos')
      .select('*')
      .eq('cliente_id', id)

    if (error) throw error

    return NextResponse.json({ success: true, data: data || [] })
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
    if (role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 403 })
    }

    const { id } = await params
    const { modulo_id, activo } = await request.json()

    const { data, error } = await supabase
      .from('modulos_activos')
      .update({ activo })
      .eq('cliente_id', id)
      .eq('modulo_id', modulo_id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error updating modulo:', error)
    return NextResponse.json({ success: false, error: 'Failed to update modulo' }, { status: 500 })
  }
}
