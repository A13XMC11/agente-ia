import { NextResponse, NextRequest } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id: conversacionId } = await params

    // Obtener conversación
    const { data: conversation, error: convError } = await supabase
      .from('conversaciones')
      .select('id, usuario_id, usuario_nombre, usuario_telefono, canal, estado, fecha_inicio, fecha_ultimo_mensaje')
      .eq('id', conversacionId)
      .eq('cliente_id', session.cliente_id)
      .single()

    if (convError) {
      return NextResponse.json({ success: false, error: 'Conversación no encontrada' }, { status: 404 })
    }

    // Obtener mensajes ordenados por fecha
    const { data: messages, error: msgError } = await supabase
      .from('mensajes')
      .select('id, conversacion_id, sender_id, sender_type, contenido, tipo, created_at')
      .eq('conversacion_id', conversacionId)
      .eq('cliente_id', session.cliente_id)
      .order('created_at', { ascending: true })

    if (msgError) {
      return NextResponse.json({ success: false, error: 'Error al obtener mensajes' }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      data: {
        conversation,
        messages: messages || []
      }
    })
  } catch (error) {
    console.error('Error fetching conversación:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch conversación' }, { status: 500 })
  }
}
