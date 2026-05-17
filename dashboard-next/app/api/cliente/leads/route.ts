import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()
    console.log('[LEADS] Session:', { id: session?.id, email: session?.email, cliente_id: session?.cliente_id })

    if (!session || !session.cliente_id) {
      console.log('[LEADS] Unauthorized: no session or cliente_id')
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const clienteId = session.cliente_id
    console.log('[LEADS] Fetching leads for cliente_id:', clienteId)

    const result = await supabase
      .from('leads')
      .select('*')
      .eq('cliente_id', clienteId)
      .order('score', { ascending: false })

    console.log('[LEADS] Query result:', {
      hasData: !!result.data,
      dataLength: result.data?.length || 0,
      error: result.error ? { message: result.error.message, code: result.error.code } : null
    })

    const { data, error } = result

    if (error) {
      console.log('[LEADS] Error details:', JSON.stringify(error, null, 2))
      if (error.code === '42P01' || error.code === 'PGRST204') {
        console.log('[LEADS] Table does not exist, returning empty array')
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    console.log('[LEADS] Raw data sample:', data && data.length > 0 ? JSON.stringify(data[0], null, 2) : 'No data')

    const normalized = (data || []).map((lead: any) => ({
      id: lead.id,
      name: lead.nombre,
      email: lead.email,
      phone: lead.telefono,
      score: lead.score || 0,
      state: lead.estado || 'curioso',
      urgency: lead.urgency || 0,
      budget: lead.budget,
      decision_power: lead.decision_power || 0,
      last_interaction: lead.last_interaction,
      interaction_count: lead.interaction_count || 0,
      created_at: lead.created_at,
    }))

    console.log('[LEADS] Normalized data length:', normalized.length)
    return NextResponse.json({ success: true, data: normalized })
  } catch (error) {
    console.error('[LEADS] Error fetching leads:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch leads' }, { status: 500 })
  }
}
