import { NextResponse } from 'next/server'
import { getUserRole } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const role = await getUserRole()
    if (role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 403 })
    }

    const { id } = await params

    const { data, error } = await supabase
      .from('agentes')
      .select('*')
      .eq('cliente_id', id)
      .single()

    if (error && error.code !== 'PGRST116') throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error fetching agente:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch agente' }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const role = await getUserRole()
    if (role !== 'admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 403 })
    }

    const { id } = await params
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
      .eq('cliente_id', id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error updating agente:', error)
    return NextResponse.json({ success: false, error: 'Failed to update agente' }, { status: 500 })
  }
}
