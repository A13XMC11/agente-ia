import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()

    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const clienteId = session.cliente_id

    const { data, error } = await supabase
      .from('leads')
      .select('*, conversaciones(usuario_nombre)')
      .eq('cliente_id', clienteId)
      .order('score', { ascending: false })

    if (error) {
      if (error.code === '42P01' || error.code === 'PGRST204') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    const normalized = (data || []).map((lead: any) => ({
      id: lead.id,
      name: lead.nombre || lead.conversaciones?.usuario_nombre || '',
      email: lead.email,
      phone: lead.telefono,
      score: lead.score || 0,
      state: lead.estado || 'curioso',
      urgency: lead.urgencia || 0,
      budget: lead.presupuesto_estimado ?? null,
      decision_power: lead.decision || 0,
      last_interaction: null,
      interaction_count: 0,
      created_at: lead.created_at,
    }))

    return NextResponse.json({ success: true, data: normalized })
  } catch {
    return NextResponse.json({ success: false, error: 'Failed to fetch leads' }, { status: 500 })
  }
}
