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
      .from('agentes')
      .select('google_calendar_id, google_calendar_credentials_json')
      .eq('cliente_id', session.cliente_id)
      .maybeSingle()

    if (error) throw error

    // Extract client_email from credentials without exposing the private key
    let credentials_email: string | null = null
    if (data?.google_calendar_credentials_json) {
      try {
        const parsed = JSON.parse(data.google_calendar_credentials_json)
        credentials_email = parsed.client_email ?? null
      } catch {
        // ignore malformed JSON
      }
    }

    return NextResponse.json({
      success: true,
      data: {
        google_calendar_id: data?.google_calendar_id ?? null,
        has_credentials: !!data?.google_calendar_credentials_json,
        credentials_email,
      },
    })
  } catch (error) {
    console.error('Error fetching calendar config:', error)
    return NextResponse.json({ success: false, error: 'Error al obtener configuración' }, { status: 500 })
  }
}

export async function PUT(request: Request) {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { google_calendar_id, google_calendar_credentials_json } = body as {
      google_calendar_id?: string
      google_calendar_credentials_json?: string
    }

    if (!google_calendar_id || typeof google_calendar_id !== 'string') {
      return NextResponse.json(
        { success: false, error: 'El Calendar ID es requerido' },
        { status: 400 }
      )
    }

    if (google_calendar_credentials_json) {
      try {
        const parsed = JSON.parse(google_calendar_credentials_json)
        if (parsed.type !== 'service_account') {
          return NextResponse.json(
            { success: false, error: 'Las credenciales deben ser de tipo Service Account (campo "type": "service_account")' },
            { status: 400 }
          )
        }
        if (!parsed.client_email || !parsed.private_key) {
          return NextResponse.json(
            { success: false, error: 'El JSON no contiene los campos requeridos (client_email, private_key)' },
            { status: 400 }
          )
        }
      } catch {
        return NextResponse.json(
          { success: false, error: 'El JSON de credenciales no es válido' },
          { status: 400 }
        )
      }
    }

    const update: Record<string, string> = { google_calendar_id: google_calendar_id.trim() }
    if (google_calendar_credentials_json) {
      update.google_calendar_credentials_json = google_calendar_credentials_json
    }

    const { error } = await supabase
      .from('agentes')
      .update(update)
      .eq('cliente_id', session.cliente_id)

    if (error) throw error

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error saving calendar config:', error)
    return NextResponse.json({ success: false, error: 'Error al guardar configuración' }, { status: 500 })
  }
}
