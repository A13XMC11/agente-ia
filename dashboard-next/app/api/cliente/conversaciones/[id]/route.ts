import { NextResponse, NextRequest } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const conversacionId = params.id

    // Get conversation details
    const { data: conversation, error: convError } = await supabase
      .from('conversaciones')
      .select('*')
      .eq('id', conversacionId)
      .eq('cliente_id', session.cliente_id)
      .single()

    if (convError || !conversation) {
      return NextResponse.json({ success: false, error: 'Conversación no encontrada' }, { status: 404 })
    }

    // Get messages
    const { data: messages, error: msgError } = await supabase
      .from('mensajes')
      .select('*')
      .eq('conversacion_id', conversacionId)
      .order('created_at', { ascending: true })

    if (msgError) {
      console.error('Error fetching messages:', msgError)
      return NextResponse.json({ success: false, error: 'Failed to fetch messages' }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      data: {
        conversation,
        messages: messages || []
      }
    })
  } catch (error) {
    console.error('Error fetching conversation:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch conversation' }, { status: 500 })
  }
}
