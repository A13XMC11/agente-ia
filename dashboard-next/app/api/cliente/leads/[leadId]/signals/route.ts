import { NextResponse, NextRequest } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ leadId: string }> }
) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { leadId } = await params

    // Verificar que el lead pertenece al cliente
    const { data: lead, error: leadError } = await supabase
      .from('leads')
      .select('id')
      .eq('id', leadId)
      .eq('cliente_id', session.cliente_id)
      .single()

    if (leadError) {
      return NextResponse.json({ success: false, error: 'Lead no encontrado' }, { status: 404 })
    }

    // Obtener historial de señales (score changes)
    const { data: signals, error: signalsError } = await supabase
      .from('leads_signals')
      .select('id, lead_id, score_before, score_after, delta, signal_type, signal_keywords, message_excerpt, created_at')
      .eq('lead_id', leadId)
      .order('created_at', { ascending: false })
      .limit(50)

    if (signalsError && signalsError.code !== '42P01') {
      // 42P01 = table doesn't exist, return empty array
      return NextResponse.json({ success: false, error: 'Error al obtener señales' }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      data: signals || []
    })
  } catch (error) {
    console.error('Error fetching signals:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch signals' }, { status: 500 })
  }
}
