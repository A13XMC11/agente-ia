import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(request: Request) {
  try {
    const session = await getSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const url = new URL(request.url)
    const start = url.searchParams.get('start')
    const end = url.searchParams.get('end')

    let query = supabase
      .from('citas')
      .select('id, usuario_id, usuario_nombre:usuarios(nombre), email:usuarios(email), fecha, hora, duracion_minutos, estado, descripcion')
      .eq('cliente_id', session.cliente_id)

    if (start) {
      query = query.gte('fecha', start)
    }

    if (end) {
      query = query.lte('fecha', end)
    }

    const { data, error } = await query.order('fecha', { ascending: true })

    if (error) throw error

    return NextResponse.json({ success: true, data: data || [] })
  } catch (error) {
    console.error('Error fetching citas:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch citas' }, { status: 500 })
  }
}
