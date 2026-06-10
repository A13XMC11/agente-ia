import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { createServerClient } from '@/lib/supabase/server'
import { randomUUID } from 'crypto'

const MAX_SIZE_BYTES = 5 * 1024 * 1024 // 5 MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'application/pdf']

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'No autorizado' }, { status: 401 })
    }

    const formData = await req.formData()
    const file = formData.get('file')

    if (!(file instanceof File)) {
      return NextResponse.json({ success: false, error: 'Se requiere un archivo' }, { status: 400 })
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      return NextResponse.json(
        { success: false, error: 'Tipo de archivo no permitido. Usa JPG, PNG, PDF o similar.' },
        { status: 400 },
      )
    }

    if (file.size > MAX_SIZE_BYTES) {
      return NextResponse.json(
        { success: false, error: 'El archivo supera el límite de 5 MB' },
        { status: 400 },
      )
    }

    const ext = file.name.split('.').pop() ?? 'jpg'
    const path = `${session.cliente_id}/${randomUUID()}.${ext}`

    const supabase = createServerClient()
    const arrayBuffer = await file.arrayBuffer()

    const { error: uploadError } = await supabase.storage
      .from('subscription-proofs')
      .upload(path, arrayBuffer, {
        contentType: file.type,
        upsert: false,
      })

    if (uploadError) {
      console.error('[BILLING PROOF] Storage upload error:', uploadError)
      return NextResponse.json({ success: false, error: 'Error al subir el archivo' }, { status: 500 })
    }

    const { data: urlData } = supabase.storage.from('subscription-proofs').getPublicUrl(path)
    const proofUrl = urlData.publicUrl

    // Notify backend to transition subscription status
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      return NextResponse.json({ success: false, error: 'API_URL no configurada' }, { status: 500 })
    }

    const apiRes = await fetch(`${apiUrl}/api/billing/submit-proof`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Secret': process.env.INTERNAL_API_SECRET ?? '',
      },
      body: JSON.stringify({ client_id: session.cliente_id, proof_url: proofUrl }),
    })

    if (!apiRes.ok) {
      const errBody = await apiRes.json().catch(() => ({}))
      return NextResponse.json(
        { success: false, error: (errBody as Record<string, string>).detail ?? 'Error al registrar comprobante' },
        { status: 502 },
      )
    }

    return NextResponse.json({ success: true, data: { proof_url: proofUrl } })
  } catch (err) {
    console.error('[BILLING PROOF] Unexpected error:', err)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}
