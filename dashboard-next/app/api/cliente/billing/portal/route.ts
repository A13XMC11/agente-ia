import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { redirect } from 'next/navigation'

/**
 * GET /api/cliente/billing/portal
 *
 * Creates a Stripe Billing Portal session and redirects the client there.
 * The portal lets them update payment method, view invoices, etc.
 * After finishing, Stripe redirects back to /cliente/billing.
 */
export async function GET() {
  const session = await getServerSession()
  if (!session?.cliente_id) {
    return NextResponse.redirect('/login')
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  const appUrl = process.env.NEXT_PUBLIC_APP_URL

  if (!apiUrl || !appUrl) {
    return NextResponse.json({ error: 'Configuración incompleta' }, { status: 500 })
  }

  const res = await fetch(`${apiUrl}/api/billing/customer-portal`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Secret': process.env.INTERNAL_API_SECRET ?? '',
    },
    body: JSON.stringify({
      client_id: session.cliente_id,
      return_url: `${appUrl}/cliente/billing`,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    console.error('[BILLING PORTAL]', res.status, err)
    return NextResponse.redirect(`${appUrl}/cliente/billing?portal_error=1`)
  }

  const { portal_url } = await res.json()
  return NextResponse.redirect(portal_url)
}
