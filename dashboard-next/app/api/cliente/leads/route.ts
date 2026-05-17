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
      .select('id, nombre, email, telefono, score, estado, created_at, urgency, budget, decision_power, last_interaction, interaction_count')
      .eq('cliente_id', session.cliente_id)
      .order('score', { ascending: false })

    if (error) {
      if (error.code === '42P01' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

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

    return NextResponse.json({ success: true, data: normalized })
  } catch (error) {
    console.error('Error fetching leads:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch leads' }, { status: 500 })
  }
}
