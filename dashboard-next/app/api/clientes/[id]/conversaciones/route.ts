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

    const { data, error } = await supabase
      .from('conversaciones')
      .select('id, usuario_id, usuario_nombre:usuarios(nombre), canal, ultimo_mensaje, created_at, updated_at')
      .eq('cliente_id', clienteId)
      .order('updated_at', { ascending: false })

    if (error) throw error

    const formattedData = (data || []).map((conv: any) => ({
      id: conv.id,
      usuario_id: conv.usuario_id,
      usuario_nombre: conv.usuario_nombre?.nombre || 'Usuario',
      canal: conv.canal,
      ultimo_mensaje: conv.ultimo_mensaje,
      created_at: conv.created_at,
      updated_at: conv.updated_at,
    }))

    return NextResponse.json({ success: true, data: formattedData })
  } catch (error) {
    console.error('Error fetching conversaciones:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch conversaciones' },
      { status: 500 }
    )
  }
}
