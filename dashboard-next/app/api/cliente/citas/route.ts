import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(request: Request) {
  try {
    const session = await getServerSession()
    console.log('[CITAS] Session:', { id: session?.id, email: session?.email, cliente_id: session?.cliente_id })

    if (!session || !session.cliente_id) {
      console.log('[CITAS] Unauthorized: no session or cliente_id')
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const clienteId = session.cliente_id
    console.log('[CITAS] Fetching citas for cliente_id:', clienteId)

    const url = new URL(request.url)
    const start = url.searchParams.get('start')
    const end = url.searchParams.get('end')
    console.log('[CITAS] Date filters:', { start, end })

    let query = supabase
      .from('citas')
      .select('*')
      .eq('cliente_id', clienteId)

    // Temporarily disabled date filters for debugging
    // if (start) {
    //   query = query.gte('fecha', start)
    // }

    // if (end) {
    //   query = query.lte('fecha', end)
    // }

    const result = await query.order('fecha', { ascending: true })
    const { data, error } = result

    console.log('[CITAS] Query result:', {
      hasData: !!data,
      dataLength: data?.length || 0,
      error: error ? { message: error.message, code: error.code } : null
    })

    if (error) {
      console.log('[CITAS] Error details:', JSON.stringify(error, null, 2))
      // Return empty array if table doesn't exist yet
      if (error.code === '42P01' || error.code === 'PGRST204') {
        console.log('[CITAS] Table does not exist, returning empty array')
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    console.log('[CITAS] Raw data sample:', data && data.length > 0 ? JSON.stringify(data[0], null, 2) : 'No data')

    const mapped = (data || []).map((cita: any) => ({
      id: cita.id,
      usuario_id: cita.usuario_id,
      usuario_nombre: cita.nombre_cliente || 'Cliente desconocido',
      usuario_email: cita.email_cliente || '',
      usuario_telefono: cita.telefono_cliente || '',
      fecha: cita.fecha,
      hora: cita.hora,
      duracion_minutos: cita.duracion_minutos,
      servicio: cita.servicio || 'Sin servicio',
      estado: cita.estado,
      created_at: cita.created_at
    }))

    console.log('[CITAS] Mapped data length:', mapped.length)
    return NextResponse.json({ success: true, data: mapped })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    console.error('[CITAS] Error fetching citas:', errorMessage)
    return NextResponse.json({ success: false, error: `Failed to fetch citas: ${errorMessage}` }, { status: 500 })
  }
}
