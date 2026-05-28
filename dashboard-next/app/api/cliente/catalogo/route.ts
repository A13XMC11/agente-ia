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
      .from('product_catalog')
      .select('*')
      .eq('cliente_id', session.cliente_id)
      .order('nombre', { ascending: true })

    if (error) {
      if (error.code === '42P01') {
        return NextResponse.json({ success: true, data: [] })
      }
      throw error
    }

    return NextResponse.json({ success: true, data: data || [] })
  } catch (error) {
    console.error('[CATALOGO] GET error:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener catálogo' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const { nombre, descripcion, precio, stock, moneda, categoria, sku, imagen_url } = body

    if (!nombre?.trim()) {
      return NextResponse.json({ success: false, error: 'El nombre es requerido' }, { status: 400 })
    }
    if (precio === undefined || precio === null || isNaN(Number(precio))) {
      return NextResponse.json({ success: false, error: 'El precio es requerido' }, { status: 400 })
    }

    const now = new Date().toISOString()
    const product = {
      cliente_id: session.cliente_id,
      nombre: nombre.trim(),
      descripcion: descripcion?.trim() || null,
      precio: Number(precio),
      moneda: moneda || 'USD',
      categoria: categoria?.trim() || null,
      sku: sku?.trim() || null,
      imagen_url: imagen_url?.trim() || null,
      stock: stock !== undefined && stock !== '' ? Number(stock) : null,
      activo: true,
      created_at: now,
      updated_at: now,
    }

    const { data, error } = await supabase
      .from('product_catalog')
      .insert(product)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ success: true, data })
  } catch (error) {
    console.error('[CATALOGO] POST error:', error)
    return NextResponse.json({ success: false, error: 'Error al crear producto' }, { status: 500 })
  }
}
