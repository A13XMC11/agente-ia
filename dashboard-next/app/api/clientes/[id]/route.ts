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
      .from('clientes')
      .select('*')
      .eq('id', id)
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error fetching cliente:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch cliente' }, { status: 500 })
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
      .from('clientes')
      .update({
        nombre: body.nombre,
        email: body.email,
        telefono: body.telefono,
        plan: body.plan,
        precio_mensual: body.precio_mensual,
        estado: body.estado
      })
      .eq('id', id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error updating cliente:', error)
    return NextResponse.json({ success: false, error: 'Failed to update cliente' }, { status: 500 })
  }
}
