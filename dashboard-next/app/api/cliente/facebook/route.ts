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
      .eq('canal', 'facebook')
      .maybeSingle()

    if (error) throw error

    return NextResponse.json({ success: true, data: data ?? null })
  } catch (error) {
    console.error('Error fetching Facebook config:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener configuración' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const { page_id, access_token } = await request.json()

    if (!page_id || !access_token) {
      return NextResponse.json(
        { success: false, error: 'Page ID y Access Token son requeridos' },
        { status: 400 }
      )
    }

    // Verify credentials against Meta Graph API
    const metaRes = await fetch(
      `https://graph.facebook.com/v21.0/${page_id}?fields=name,fan_count&access_token=${access_token}`
    )

    if (!metaRes.ok) {
      const errData = await metaRes.json().catch(() => ({}))
      const metaMsg = errData?.error?.message ?? ''
      if (metaRes.status === 401 || metaRes.status === 403) {
        return NextResponse.json(
          { success: false, error: '❌ Token inválido. Verifica que copiaste el token completo y que tiene permisos de pages_messaging' },
          { status: 422 }
        )
      }
      return NextResponse.json(
        { success: false, error: `❌ Credenciales inválidas: ${metaMsg || 'Page ID no encontrado'}` },
        { status: 422 }
      )
    }

    const pageData = await metaRes.json()

    const { error } = await supabase.from('canales_config').upsert(
      {
        cliente_id: session.cliente_id,
        canal: 'facebook',
        phone_number_id: page_id,
        token: access_token,
        waba_id: pageData.name ?? null,
        activo: true,
      },
      { onConflict: 'cliente_id,canal' }
    )

    if (error) throw error

    return NextResponse.json({ success: true, page_name: pageData.name })
  } catch (error) {
    console.error('Error saving Facebook config:', error)
    return NextResponse.json({ success: false, error: 'Error al guardar configuración' }, { status: 500 })
  }
}
