import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function PUT(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const body = await req.json()
    const { nombre, descripcion, precio, stock, moneda, categoria, sku, imagen_url, activo } = body

    const updates: Record<string, unknown> = { updated_at: new Date().toISOString() }
    if (nombre !== undefined) updates.nombre = nombre.trim()
    if (descripcion !== undefined) updates.descripcion = descripcion?.trim() || null
    if (precio !== undefined) updates.precio = Number(precio)
    if (moneda !== undefined) updates.moneda = moneda
    if (categoria !== undefined) updates.categoria = categoria?.trim() || null
    if (sku !== undefined) updates.sku = sku?.trim() || null
    if (imagen_url !== undefined) updates.imagen_url = imagen_url?.trim() || null
    if (stock !== undefined) updates.stock = stock !== '' && stock !== null ? Number(stock) : null
    if (activo !== undefined) updates.activo = activo

    const { data, error } = await supabase
      .from('product_catalog')
      .update(updates)
      .eq('id', id)
      .eq('cliente_id', session.cliente_id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('[CATALOGO] PUT error:', error)
    return NextResponse.json({ success: false, error: 'Error al actualizar producto' }, { status: 500 })
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params

    const { error } = await supabase
      .from('product_catalog')
      .delete()
      .eq('id', id)
      .eq('cliente_id', session.cliente_id)

    if (error) throw error

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('[CATALOGO] DELETE error:', error)
    return NextResponse.json({ success: false, error: 'Error al eliminar producto' }, { status: 500 })
  }
}
