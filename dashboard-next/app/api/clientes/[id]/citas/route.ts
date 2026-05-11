import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await getSession()
    if (!session || session.role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id: clienteId } = await params
    const url = new URL(request.url)
    const start = url.searchParams.get('start')
    const end = url.searchParams.get('end')

    let query = supabase
      .from('citas')
      .select('id, usuario_id, usuario_nombre:usuarios(nombre), fecha, hora, estado, created_at')
      .eq('cliente_id', clienteId)

    if (start) {
      query = query.gte('fecha', start)
    }

    if (end) {
      query = query.lte('fecha', end)
    }

    const { data, error } = await query.order('fecha', { ascending: true })

    if (error) throw error

    const formattedData = (data || []).map((cita: any) => ({
      id: cita.id,
      usuario_id: cita.usuario_id,
      usuario_nombre: cita.usuario_nombre?.nombre || 'Usuario',
      fecha: cita.fecha,
      hora: cita.hora,
      estado: cita.estado,
      created_at: cita.created_at,
    }))

    return NextResponse.json({ success: true, data: formattedData })
  } catch (error) {
    console.error('Error fetching citas:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch citas' },
      { status: 500 }
    )
  }
}
