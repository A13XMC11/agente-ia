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
      .from('datos_bancarios')
      .select('id, banco, tipo_cuenta, numero_cuenta, titular, ruc, activo')
      .eq('cliente_id', session.cliente_id)
      .eq('activo', true)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching bank accounts:', error)
      throw error
    }

    return NextResponse.json({ success: true, data: data || [] })
  } catch (error) {
    console.error('Error in GET /api/cliente/datos-bancarios:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch bank accounts' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { banco, tipo_cuenta, numero_cuenta, titular, ruc, pais } = body

    // Validate required fields
    if (!banco || !numero_cuenta || !titular) {
      return NextResponse.json(
        { success: false, error: 'banco, numero_cuenta, and titular are required' },
        { status: 400 }
      )
    }

    const { data, error } = await supabase
      .from('datos_bancarios')
      .insert({
        cliente_id: session.cliente_id,
        banco,
        tipo_cuenta: tipo_cuenta || 'corriente',
        numero_cuenta,
        titular,
        ruc: ruc || null,
        pais: pais || 'Ecuador',
        activo: true,
      })
      .select()
      .single()

    if (error) {
      console.error('Error creating bank account:', error)
      throw error
    }

    return NextResponse.json({ success: true, data }, { status: 201 })
  } catch (error) {
    console.error('Error in POST /api/cliente/datos-bancarios:', error)
    return NextResponse.json({ success: false, error: 'Failed to create bank account' }, { status: 500 })
  }
}

export async function PUT(request: Request) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { id, ...updates } = body

    if (!id) {
      return NextResponse.json({ success: false, error: 'id is required' }, { status: 400 })
    }

    // Only allow updating these fields
    const allowedUpdates: Record<string, any> = {}
    if (updates.banco !== undefined) allowedUpdates.banco = updates.banco
    if (updates.tipo_cuenta !== undefined) allowedUpdates.tipo_cuenta = updates.tipo_cuenta
    if (updates.numero_cuenta !== undefined) allowedUpdates.numero_cuenta = updates.numero_cuenta
    if (updates.titular !== undefined) allowedUpdates.titular = updates.titular
    if (updates.ruc !== undefined) allowedUpdates.ruc = updates.ruc
    if (updates.activo !== undefined) allowedUpdates.activo = updates.activo

    const { data, error } = await supabase
      .from('datos_bancarios')
      .update(allowedUpdates)
      .eq('id', id)
      .eq('cliente_id', session.cliente_id) // RLS enforcement
      .select()
      .single()

    if (error) {
      console.error('Error updating bank account:', error)
      throw error
    }

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('Error in PUT /api/cliente/datos-bancarios:', error)
    return NextResponse.json({ success: false, error: 'Failed to update bank account' }, { status: 500 })
  }
}

export async function DELETE(request: Request) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const url = new URL(request.url)
    const id = url.searchParams.get('id')

    if (!id) {
      return NextResponse.json({ success: false, error: 'id is required' }, { status: 400 })
    }

    // Soft delete: set activo=false to preserve payment history integrity
    const { error } = await supabase
      .from('datos_bancarios')
      .update({ activo: false })
      .eq('id', id)
      .eq('cliente_id', session.cliente_id)

    if (error) {
      console.error('Error deleting bank account:', error)
      throw error
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error in DELETE /api/cliente/datos-bancarios:', error)
    return NextResponse.json({ success: false, error: 'Failed to delete bank account' }, { status: 500 })
  }
}
