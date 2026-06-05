import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

interface ProductRow {
  nombre: string
  precio: number
  descripcion?: string | null
  stock?: number | null
  moneda?: string
  categoria?: string | null
  sku?: string | null
  imagen_url?: string | null
}

const COLUMN_ALIASES: Record<string, string> = {
  nombre: 'nombre', name: 'nombre', producto: 'nombre',
  descripcion: 'descripcion', description: 'descripcion',
  precio: 'precio', price: 'precio', costo: 'precio',
  stock: 'stock', cantidad: 'stock', inventory: 'stock',
  moneda: 'moneda', currency: 'moneda',
  categoria: 'categoria', category: 'categoria',
  imagen: 'imagen_url', imagen_url: 'imagen_url', image_url: 'imagen_url',
  sku: 'sku', codigo: 'sku', code: 'sku', ref: 'sku',
}

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter(Boolean)
  if (lines.length < 2) return []

  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, '').toLowerCase())

  return lines.slice(1).map(line => {
    const values: string[] = []
    let current = ''
    let inQuotes = false
    for (const ch of line) {
      if (ch === '"') { inQuotes = !inQuotes }
      else if (ch === ',' && !inQuotes) { values.push(current.trim()); current = '' }
      else { current += ch }
    }
    values.push(current.trim())

    const row: Record<string, string> = {}
    headers.forEach((h, i) => { row[h] = values[i] ?? '' })
    return row
  })
}

function normalizeRows(rows: Record<string, string>[]): ProductRow[] {
  return rows
    .map(row => {
      const normalized: Record<string, string> = {}
      for (const [k, v] of Object.entries(row)) {
        const mapped = COLUMN_ALIASES[k.toLowerCase()]
        if (mapped) normalized[mapped] = v
      }
      if (!normalized.nombre?.trim()) return null
      const precio = parseFloat(normalized.precio ?? '0')
      if (isNaN(precio)) return null

      const product: ProductRow = { nombre: normalized.nombre.trim(), precio }
      if (normalized.descripcion) product.descripcion = normalized.descripcion.trim() || null
      if (normalized.moneda) product.moneda = normalized.moneda.trim() || 'USD'
      if (normalized.categoria) product.categoria = normalized.categoria.trim() || null
      if (normalized.sku) product.sku = normalized.sku.trim() || null
      if (normalized.imagen_url) product.imagen_url = normalized.imagen_url.trim() || null
      if (normalized.stock !== undefined && normalized.stock !== '') {
        const s = parseInt(normalized.stock, 10)
        if (!isNaN(s)) product.stock = s
      }
      return product
    })
    .filter((p): p is ProductRow => p !== null)
}

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'No autorizado. Asegúrate de estar logueado como cliente (no super_admin).' }, { status: 401 })
    }

    const formData = await req.formData()
    const file = formData.get('file') as File | null
    if (!file) {
      return NextResponse.json({ success: false, error: 'Archivo requerido' }, { status: 400 })
    }
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return NextResponse.json({ success: false, error: 'Solo se aceptan archivos CSV (.csv)' }, { status: 400 })
    }

    const text = await file.text()
    const rows = parseCSV(text)
    const products = normalizeRows(rows)

    if (products.length === 0) {
      return NextResponse.json({ success: false, error: 'No se encontraron productos válidos. Verifica que el CSV tenga columnas "nombre" y "precio".' }, { status: 422 })
    }

    // Fetch existing products for upsert matching
    const { data: existing, error: fetchError } = await supabase
      .from('product_catalog')
      .select('id, sku, nombre')
      .eq('cliente_id', session.cliente_id)

    if (fetchError) {
      console.error('[CATALOGO] IMPORT fetch existing error:', fetchError)
      return NextResponse.json({
        success: false,
        error: `Error al acceder a la base de datos: ${fetchError.message}. ¿Ejecutaste la migración create_ventas.sql en Supabase?`,
      }, { status: 500 })
    }

    const bySku = new Map((existing || []).filter(r => r.sku).map(r => [r.sku!.toLowerCase(), r.id]))
    const byNombre = new Map((existing || []).map(r => [r.nombre.toLowerCase(), r.id]))

    const now = new Date().toISOString()
    let created = 0, updated = 0

    for (const product of products) {
      const skuKey = product.sku?.toLowerCase()
      const nombreKey = product.nombre.toLowerCase()
      const existingId = (skuKey && bySku.get(skuKey)) || byNombre.get(nombreKey)

      if (existingId) {
        const { error: updateError } = await supabase
          .from('product_catalog')
          .update({ ...product, updated_at: now })
          .eq('id', existingId)
          .eq('cliente_id', session.cliente_id)
        if (updateError) throw new Error(`Error actualizando "${product.nombre}": ${updateError.message}`)
        updated++
      } else {
        const { data: inserted, error: insertError } = await supabase
          .from('product_catalog')
          .insert({ ...product, cliente_id: session.cliente_id, activo: true, created_at: now, updated_at: now })
          .select('id, sku, nombre')
          .single()
        if (insertError) throw new Error(`Error insertando "${product.nombre}": ${insertError.message}`)
        if (inserted) {
          if (inserted.sku) bySku.set(inserted.sku.toLowerCase(), inserted.id)
          byNombre.set(inserted.nombre.toLowerCase(), inserted.id)
        }
        created++
      }
    }

    return NextResponse.json({ success: true, total_rows: products.length, created, updated })
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Error desconocido'
    console.error('[CATALOGO] IMPORT error:', msg)
    return NextResponse.json({ success: false, error: msg }, { status: 500 })
  }
}
