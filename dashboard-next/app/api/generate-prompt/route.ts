import { getServerSession } from '@/lib/server-auth'
import { NextResponse } from 'next/server'

export async function POST(request: Request): Promise<Response> {
  const session = await getServerSession()
  if (!session) {
    return NextResponse.json({ success: false, error: 'No autorizado' }, { status: 401 })
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) {
    return NextResponse.json({ success: false, error: 'API URL no configurada' }, { status: 500 })
  }

  try {
    const body = await request.json()

    const backendRes = await fetch(`${apiUrl}/internal/generate-prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Secret': process.env.INTERNAL_API_SECRET ?? '',
      },
      body: JSON.stringify(body),
    })

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}))
      return NextResponse.json(
        { success: false, error: (err as { detail?: string }).detail || 'Error al generar el prompt' },
        { status: 502 },
      )
    }

    const data = await backendRes.json() as { prompt: string }
    return NextResponse.json({ success: true, prompt: data.prompt })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error interno'
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}
