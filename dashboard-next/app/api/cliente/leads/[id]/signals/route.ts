import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const leadId = params.id

    // First verify the lead belongs to this client
    const { data: lead, error: leadError } = await supabase
      .from('leads')
      .select('id')
      .eq('id', leadId)
      .eq('cliente_id', session.cliente_id)
      .single()

    if (leadError || !lead) {
      return NextResponse.json({ success: false, error: 'Lead not found' }, { status: 404 })
    }

    // Fetch score signals/events
    const { data, error } = await supabase
      .from('lead_signals')
      .select('*')
      .eq('lead_id', leadId)
      .order('created_at', { ascending: false })
      .limit(100)

    if (error) {
      // If table doesn't exist, return empty array
      if (error.code === '42703' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    // Map data to expected format
    const mapped = (data || []).map((signal: any) => ({
      id: signal.id,
      lead_id: signal.lead_id,
      score_before: signal.score_before || 0,
      score_after: signal.score_after || 0,
      delta: (signal.score_after || 0) - (signal.score_before || 0),
      signal_type: signal.signal_type || 'unknown',
      signal_keywords: signal.signal_keywords || [],
      message_excerpt: signal.message_excerpt || '',
      created_at: signal.created_at
    }))

    return NextResponse.json({ success: true, data: mapped })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    console.error('Error fetching signals:', errorMessage)
    return NextResponse.json(
      { success: false, error: `Failed to fetch signals: ${errorMessage}` },
      { status: 500 }
    )
  }
}
