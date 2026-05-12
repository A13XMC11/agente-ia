import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await getServerSession()
    if (!session || session.role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id: clienteId } = await params

    const { data, error } = await supabase
      .from('leads')
      .select('id, usuario_id, calificacion, estado, created_at')
      .eq('cliente_id', clienteId)
      .order('calificacion', { ascending: false })

    if (error) throw error

    const formattedData = (data || []).map((lead: any) => ({
      id: lead.id,
      usuario_id: lead.usuario_id,
      calificacion: lead.calificacion || 0,
      estado: lead.estado,
      created_at: lead.created_at,
    }))

    return NextResponse.json({ success: true, data: formattedData })
  } catch (error) {
    console.error('Error fetching leads:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch leads' },
      { status: 500 }
    )
  }
}
