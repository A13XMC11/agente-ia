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
      .from('subscription')
      .select('*')
      .eq('cliente_id', session.cliente_id)
      .maybeSingle()

    if (error) {
      console.error('[BILLING] Error fetching subscription:', error)
      return NextResponse.json({ success: false, error: 'Error al obtener suscripción' }, { status: 500 })
    }

    return NextResponse.json({ success: true, data: data ?? null })
  } catch (error) {
    console.error('[BILLING] Unexpected error:', error)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}
