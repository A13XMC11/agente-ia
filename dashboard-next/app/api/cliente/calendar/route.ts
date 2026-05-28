import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('agentes')
      .select('google_calendar_id')
      .eq('cliente_id', session.cliente_id)
      .maybeSingle()

    if (error) throw error

    return NextResponse.json({ success: true, data: { google_calendar_id: data?.google_calendar_id ?? null } })
  } catch (error) {
    console.error('Error fetching calendar config:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener configuración' }, { status: 500 })
  }
}

export async function PUT(request: Request) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { google_calendar_id } = await request.json()

    if (!google_calendar_id || typeof google_calendar_id !== 'string') {
      return NextResponse.json(
        { success: false, error: 'El Calendar ID es requerido' },
        { status: 400 }
      )
    }

    const { error } = await supabase
      .from('agentes')
      .update({ google_calendar_id: google_calendar_id.trim() })
      .eq('cliente_id', session.cliente_id)

    if (error) throw error

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error saving calendar config:', error)
    return NextResponse.json({ success: false, error: 'Error al guardar configuración' }, { status: 500 })
  }
}
