import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    // Get pending payments for review
    const { data, error } = await supabase
      .from('pagos')
      .select('id, monto, moneda, metodo_pago, estado, banco_origen, banco_destino, numero_transaccion, created_at')
      .eq('cliente_id', session.cliente_id)
      .eq('estado', 'pendiente')
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching pending payments:', error)
      throw error
    }

    return NextResponse.json({ success: true, data: data || [] })
  } catch (error) {
    console.error('Error in GET /api/cliente/pagos:', error)
    return NextResponse.json({ success: false, error: 'Failed to fetch payments' }, { status: 500 })
  }
}

export async function PATCH(request: Request) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { id, accion } = body

    if (!id || !accion || !['aprobar', 'rechazar'].includes(accion)) {
      return NextResponse.json(
        { success: false, error: 'id and accion (aprobar/rechazar) are required' },
        { status: 400 }
      )
    }

    const nuevo_estado = accion === 'aprobar' ? 'verificado' : 'rechazado'

    // Update payment status
    const { data: pago, error: updateError } = await supabase
      .from('pagos')
      .update({
        estado: nuevo_estado,
        fecha_verificacion: new Date().toISOString(),
      })
      .eq('id', id)
      .eq('cliente_id', session.cliente_id)
      .select('id, monto, numero_transaccion')
      .single()

    if (updateError) {
      console.error('Error updating payment status:', updateError)
      throw updateError
    }

    // If approved: save to comprobantes_procesados
    if (nuevo_estado === 'verificado' && pago?.numero_transaccion) {
      await supabase
        .from('comprobantes_procesados')
        .insert({
          numero_transaccion: pago.numero_transaccion,
          cliente_id: session.cliente_id,
          monto: pago.monto,
          fecha_procesado: new Date().toISOString(),
        })
        .single()
    }

    return NextResponse.json({ success: true, data: pago })
  } catch (error) {
    console.error('Error in PATCH /api/cliente/pagos:', error)
    return NextResponse.json({ success: false, error: 'Failed to update payment' }, { status: 500 })
  }
}
