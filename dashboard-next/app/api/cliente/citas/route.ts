import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(request: Request) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const url = new URL(request.url)
    const start = url.searchParams.get('start')
    const end = url.searchParams.get('end')

    let query = supabase
      .from('citas')
      .select(`
        id,
        usuario_id,
        fecha,
        hora,
        duracion_minutos,
        estado,
        descripcion,
        usuarios:usuario_id (
          nombre,
          email,
          telefono
        )
      `)
      .eq('cliente_id', session.cliente_id)

    if (start) {
      query = query.gte('fecha', start)
    }

    if (end) {
      query = query.lte('fecha', end)
    }

    const { data, error } = await query.order('fecha', { ascending: true })

    if (error) {
      console.error('Supabase error fetching citas:', error)
      // Return empty array if table doesn't exist yet
      if (error.code === '42703' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    // Map the data to include usuario_nombre and usuario_email
    const mapped = (data || []).map((cita: any) => ({
      id: cita.id,
      usuario_id: cita.usuario_id,
      usuario_nombre: cita.usuarios?.nombre || 'Usuario desconocido',
      usuario_email: cita.usuarios?.email || '',
      fecha: cita.fecha,
      hora: cita.hora,
      duracion_minutos: cita.duracion_minutos,
      estado: cita.estado,
      descripcion: cita.descripcion
    }))

    return NextResponse.json({ success: true, data: mapped })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    console.error('Error fetching citas:', errorMessage)
    return NextResponse.json({ success: false, error: `Failed to fetch citas: ${errorMessage}` }, { status: 500 })
  }
}
