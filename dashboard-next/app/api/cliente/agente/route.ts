import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('agentes')
      .select('*')
      .eq('cliente_id', session.cliente_id)
      .single()

    if (error && error.code !== 'PGRST116') throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error fetching agente:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch agente' }, { status: 500 })
  }
}

export async function PUT(request: Request) {
  try {
    const session = await getSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()

    const { data, error } = await supabase
      .from('agentes')
      .update({
        nombre: body.nombre,
        tono: body.tono,
        idioma: body.idioma,
        modelo: body.modelo,
        system_prompt: body.system_prompt
      })
      .eq('cliente_id', session.cliente_id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error updating agente:', error)
    return NextResponse.json({ success: false, error: 'Failed to update agente' }, { status: 500 })
  }
}
