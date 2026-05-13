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
      .from('leads')
      .select('id, nombre, name, email, telefono, phone, score, estado, state, created_at, urgency, budget, decision_power, last_interaction, interaction_count, score_updated_at')
      .eq('cliente_id', session.cliente_id)
      .order('score', { ascending: false })
      .order('last_interaction', { ascending: false })

    if (error) {
      // Return empty array if table doesn't exist yet
      if (error.code === '42703' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    // Normalize field names (use new schema names, fall back to old Spanish names)
    const normalized = (data || []).map((lead: any) => ({
      id: lead.id,
      name: lead.name || lead.nombre,
      email: lead.email,
      phone: lead.phone || lead.telefono,
      score: lead.score || 0,
      state: lead.state || lead.estado || 'curioso',
      urgency: lead.urgency || 0,
      budget: lead.budget,
      decision_power: lead.decision_power || 0,
      last_interaction: lead.last_interaction,
      interaction_count: lead.interaction_count || 0,
      score_updated_at: lead.score_updated_at,
      created_at: lead.created_at,
    }))

    return NextResponse.json({ success: true, data: normalized })
  } catch (error) {
    console.error('Error fetching leads:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch leads' }, { status: 500 })
  }
}
