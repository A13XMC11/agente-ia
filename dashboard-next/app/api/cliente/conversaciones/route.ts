import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('conversaciones')
      .select('id, usuario_id, usuario_nombre, usuario_telefono, canal, estado, fecha_inicio, fecha_ultimo_mensaje')
      .eq('cliente_id', session.cliente_id)
      .order('fecha_ultimo_mensaje', { ascending: false })

    if (error) {
      if (error.code === '42P01' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    return NextResponse.json({ success: true, data: data || [] })
  } catch (error) {
    console.error('Error fetching conversaciones:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch conversaciones' }, { status: 500 })
  }
}
