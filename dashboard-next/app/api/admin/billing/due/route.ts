import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session || session.role !== 'super_admin') {
      return NextResponse.json({ success: false, error: 'No autorizado' }, { status: 401 })
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      return NextResponse.json({ success: false, error: 'API_URL no configurada' }, { status: 500 })
    }

    const apiRes = await fetch(`${apiUrl}/api/billing/due-manual`, {
      method: 'GET',
      headers: {
        'X-Internal-Secret': process.env.INTERNAL_API_SECRET ?? '',
      },
    })

    if (!apiRes.ok) {
      const errBody = await apiRes.json().catch(() => ({}))
      return NextResponse.json(
        { success: false, error: (errBody as Record<string, string>).detail ?? 'Error al obtener renovaciones' },
        { status: 502 },
      )
    }

    const result = await apiRes.json()
    return NextResponse.json({ success: true, data: result.data ?? [] })
  } catch (err) {
    console.error('[ADMIN BILLING DUE] Unexpected error:', err)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}
