import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'

/**
 * GET /api/cliente/billing/portal
 *
 * Payphone does not have a self-service customer portal.
 * Redirect clients to the billing support page instead.
 */
export async function GET() {
  const session = await getServerSession()
  if (!session?.cliente_id) {
    return NextResponse.redirect('/login')
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? ''
  return NextResponse.redirect(`${appUrl}/cliente/billing`)
}
