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
      .from('canales_config')
      .select('phone_number_id, waba_id, activo')
      .eq('cliente_id', session.cliente_id)
      .eq('canal', 'whatsapp')
      .maybeSingle()

    if (error) throw error

    return NextResponse.json({ success: true, data: data ?? null })
  } catch (error) {
    console.error('Error fetching WhatsApp config:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener configuración' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { phone_number_id, token, waba_id } = await request.json()

    if (!phone_number_id || !token) {
      return NextResponse.json(
        { success: false, error: 'Phone Number ID y token son requeridos' },
        { status: 400 }
      )
    }

    // Verify credentials against Meta API
    const metaRes = await fetch(
      `https://graph.facebook.com/v21.0/${phone_number_id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    )

    if (!metaRes.ok) {
      const errData = await metaRes.json().catch(() => ({}))
      const metaMsg = errData?.error?.message ?? ''
      if (metaRes.status === 401 || metaRes.status === 403) {
        return NextResponse.json(
          {
            success: false,
            error:
              '❌ Token inválido. Verifica que copiaste el token completo y que tiene permisos de whatsapp_business_messaging',
          },
          { status: 422 }
        )
      }
      return NextResponse.json(
        {
          success: false,
          error: `❌ Credenciales inválidas: ${metaMsg || 'Phone Number ID no encontrado'}`,
        },
        { status: 422 }
      )
    }

    // Upsert canales_config
    const { error } = await supabase.from('canales_config').upsert(
      {
        cliente_id: session.cliente_id,
        canal: 'whatsapp',
        phone_number_id,
        token,
        waba_id: waba_id || null,
        activo: true,
      },
      { onConflict: 'cliente_id,canal' }
    )

    if (error) throw error

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error saving WhatsApp config:', error)
    return NextResponse.json({ success: false, error: 'Error al guardar configuración' }, { status: 500 })
  }
}
