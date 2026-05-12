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
      .select('id, usuario_id, canal, ultimo_mensaje, fecha_ultimo_mensaje, estado')
      .eq('cliente_id', session.cliente_id)
      .order('fecha_ultimo_mensaje', { ascending: false })

    if (error) {
      // Return empty array if table doesn't exist yet
      if (error.code === '42703' || error.code === 'PGRST204') {
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
