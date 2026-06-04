import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('campanas')
      .select('*')
      .eq('cliente_id', session.cliente_id)
      .order('created_at', { ascending: false })

    if (error) {
      if (error.code === '42P01') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    return NextResponse.json({ success: true, data: data || [] })
  } catch (error) {
    console.error('[CAMPANAS] GET error:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener campañas' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const { titulo, mensaje, target_segment, canal, programada_para, template_name, template_variables, template_language } = body

    if (!titulo?.trim()) {
      return NextResponse.json({ success: false, error: 'El título es requerido' }, { status: 400 })
    }
    if (!template_name?.trim() && !mensaje?.trim()) {
      return NextResponse.json({ success: false, error: 'Debes especificar un template o un mensaje de texto' }, { status: 400 })
    }

    const campaign = {
      cliente_id: session.cliente_id,
      title: titulo.trim(),
      message: mensaje?.trim() || '',
      target_segment: target_segment || 'all',
      channel: canal || 'whatsapp',
      scheduled_for: programada_para || new Date().toISOString(),
      status: 'draft',
      template_name: template_name?.trim() || null,
      template_variables: template_variables || [],
      template_language: template_language || 'es',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    const { data, error } = await supabase
      .from('campanas')
      .insert(campaign)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('[CAMPANAS] POST error:', error)
    return NextResponse.json({ success: false, error: 'Error al crear campaña' }, { status: 500 })
  }
}
