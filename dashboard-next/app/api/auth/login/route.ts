import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { SignJWT } from 'jose'
import { cookies } from 'next/headers'

export async function POST(request: Request) {
  try {
    const body = await request.json()

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
    const jwtSecret = process.env.JWT_SECRET

    if (!supabaseUrl || !supabaseAnonKey || !supabaseServiceKey || !jwtSecret) {
      return NextResponse.json({ success: false, error: 'Missing configuration' }, { status: 500 })
    }

    // Auth con Supabase
    const supabase = createClient(supabaseUrl, supabaseAnonKey)
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: body.email,
      password: body.password
    })

    if (authError || !authData?.user) {
      return NextResponse.json({ success: false, error: 'Credenciales incorrectas' }, { status: 401 })
    }

    // Leer rol de tabla usuarios
    const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey)
    console.log('[LOGIN] Querying usuarios table for email:', body.email)
    const { data: usuario, error: userError } = await supabaseAdmin
      .from('usuarios')
      .select('rol, cliente_id')
      .eq('email', body.email)
      .single()

    if (userError) {
      console.log('[LOGIN] Error querying usuarios:', userError)
    } else {
      console.log('[LOGIN] Usuario found:', usuario)
    }

    const rol = usuario?.rol || 'admin'
    const clienteId = usuario?.cliente_id || null
    console.log('[LOGIN] JWT will include:', { sub: authData.user.id, email: body.email, role: rol, cliente_id: clienteId })

    // Crear JWT
    const secret = new TextEncoder().encode(jwtSecret)
    const token = await new SignJWT({
      sub: authData.user.id,
      email: body.email,
      role: rol,
      cliente_id: clienteId
    })
      .setProtectedHeader({ alg: 'HS256' })
      .setExpirationTime('24h')
      .sign(secret)

    console.log('[LOGIN] JWT created successfully')

    // Cookie
    const cookieStore = await cookies()
    cookieStore.set('auth-token', token, {
      httpOnly: true,
      secure: false,
      sameSite: 'lax',
      maxAge: 60 * 60 * 24,
      path: '/'
    })

    return NextResponse.json({
      success: true,
      user: {
        id: authData.user.id,
        email: body.email,
        role: rol,
        cliente_id: clienteId
      }
    })

  } catch {
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}
