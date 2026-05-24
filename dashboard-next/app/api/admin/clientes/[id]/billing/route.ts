import { NextResponse, NextRequest } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'

type RouteContext = { params: Promise<{ id: string }> }

/* ── GET — fetch subscription for a client ─────────── */
export async function GET(_req: NextRequest, { params }: RouteContext) {
  try {
    const session = await getServerSession()
    if (!session || session.role !== 'super_admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id: clienteId } = await params

    const { data, error } = await supabase
      .from('subscription')
      .select('*')
      .eq('cliente_id', clienteId)
      .maybeSingle()

    if (error) {
      console.error('[ADMIN BILLING GET]', error)
      return NextResponse.json({ success: false, error: 'Error al obtener suscripción' }, { status: 500 })
    }

    return NextResponse.json({ success: true, data: data ?? null })
  } catch (err) {
    console.error('[ADMIN BILLING GET] unexpected:', err)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}

/* ── POST — create subscription for a client ───────── */
export async function POST(req: NextRequest, { params }: RouteContext) {
  try {
    const session = await getServerSession()
    if (!session || session.role !== 'super_admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id: clienteId } = await params
    const body = await req.json()
    const { monthly_amount } = body

    if (!monthly_amount || isNaN(Number(monthly_amount)) || Number(monthly_amount) <= 0) {
      return NextResponse.json({ success: false, error: 'monthly_amount requerido y debe ser positivo' }, { status: 400 })
    }

    // Block only if there's an active/past_due subscription
    const { data: existing } = await supabase
      .from('subscription')
      .select('id, status')
      .eq('cliente_id', clienteId)
      .not('status', 'eq', 'cancelled')
      .maybeSingle()

    if (existing) {
      return NextResponse.json({ success: false, error: 'El cliente ya tiene una suscripción activa. Cancela la existente primero.' }, { status: 409 })
    }

    // Fetch client email
    const { data: cliente, error: clienteError } = await supabase
      .from('clientes')
      .select('email, nombre')
      .eq('id', clienteId)
      .single()

    if (clienteError || !cliente) {
      return NextResponse.json({ success: false, error: 'Cliente no encontrado' }, { status: 404 })
    }

    // Create via backend API (which handles Stripe + DB insert)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      return NextResponse.json({ success: false, error: 'API_URL no configurada' }, { status: 500 })
    }

    const apiRes = await fetch(`${apiUrl}/api/billing/create-subscription`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Secret': process.env.INTERNAL_API_SECRET ?? '',
      },
      body: JSON.stringify({
        client_id: clienteId,
        monthly_amount: Number(monthly_amount),
        customer_email: cliente.email,
      }),
    })

    if (!apiRes.ok) {
      const rawText = await apiRes.text().catch(() => '')
      let errBody: Record<string, unknown> = {}
      try { errBody = JSON.parse(rawText) } catch { /* non-JSON response */ }
      console.error('[ADMIN BILLING POST] backend error:', apiRes.status, rawText)
      const detail = typeof errBody.detail === 'string' ? errBody.detail : `Error backend ${apiRes.status}`
      return NextResponse.json({ success: false, error: detail }, { status: 502 })
    }

    const result = await apiRes.json()
    return NextResponse.json({ success: true, data: result })
  } catch (err) {
    console.error('[ADMIN BILLING POST] unexpected:', err)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}

/* ── DELETE — cancel subscription ─────────────────── */
export async function DELETE(_req: NextRequest, { params }: RouteContext) {
  try {
    const session = await getServerSession()
    if (!session || session.role !== 'super_admin') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { id: clienteId } = await params

    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      return NextResponse.json({ success: false, error: 'API_URL no configurada' }, { status: 500 })
    }

    const apiRes = await fetch(`${apiUrl}/api/billing/cancel-subscription`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clienteId }),
    })

    if (!apiRes.ok) {
      const errBody = await apiRes.json().catch(() => ({}))
      return NextResponse.json({ success: false, error: errBody.detail || 'Error al cancelar suscripción' }, { status: 502 })
    }

    return NextResponse.json({ success: true })
  } catch (err) {
    console.error('[ADMIN BILLING DELETE] unexpected:', err)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}
