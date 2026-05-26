import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const body = await req.json()
    const { action } = body

    if (!['launch', 'cancel'].includes(action)) {
      return NextResponse.json({ success: false, error: 'Acción inválida' }, { status: 400 })
    }

    // Verify ownership
    const { data: existing, error: fetchError } = await supabase
      .from('campanas')
      .select('id, status, title')
      .eq('id', id)
      .eq('cliente_id', session.cliente_id)
      .single()

    if (fetchError || !existing) {
      return NextResponse.json({ success: false, error: 'Campaña no encontrada' }, { status: 404 })
    }

    if (action === 'launch') {
      if (existing.status !== 'draft') {
        return NextResponse.json({ success: false, error: 'Solo se pueden lanzar campañas en borrador' }, { status: 400 })
      }

      // Count leads for estimate
      const { count } = await supabase
        .from('leads')
        .select('id', { count: 'exact', head: true })
        .eq('cliente_id', session.cliente_id)

      const { data, error } = await supabase
        .from('campanas')
        .update({
          status: 'scheduled',
          recipients_count: count || 0,
          launched_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .eq('id', id)
        .select()
        .single()

      if (error) throw error
      return NextResponse.json({ success: true, data })
    }

    if (action === 'cancel') {
      if (!['draft', 'scheduled'].includes(existing.status)) {
        return NextResponse.json({ success: false, error: 'No se puede cancelar esta campaña' }, { status: 400 })
      }

      const { data, error } = await supabase
        .from('campanas')
        .update({
          status: 'cancelled',
          cancelled_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .eq('id', id)
        .select()
        .single()

      if (error) throw error
      return NextResponse.json({ success: true, data })
    }
  } catch (error) {
    console.error('[CAMPANAS] PATCH error:', error)
    return NextResponse.json({ success: false, error: 'Error al actualizar campaña' }, { status: 500 })
  }
}
