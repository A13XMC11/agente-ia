import { createClient } from '@supabase/supabase-js'
import { SignJWT } from 'jose'
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

interface LoginRequest {
  email: string
  password: string
}

interface Usuario {
  id: string
  email: string
  rol: string
  cliente_id?: string | null
}

export async function POST(request: Request) {
  try {
    const { email, password }: LoginRequest = await request.json()

    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: 'Email and password are required' },
        { status: 400 }
      )
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
    const jwtSecret = process.env.JWT_SECRET

    if (!supabaseUrl || !anonKey || !serviceKey || !jwtSecret) {
      console.error('[LOGIN] Missing env vars')
      return NextResponse.json(
        { success: false, error: 'Server configuration error' },
        { status: 500 }
      )
    }

    // Authenticate with Supabase Auth
    const supabase = createClient(supabaseUrl, anonKey)
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (authError || !authData.user) {
      console.log('[LOGIN] Auth failed:', authError?.message)
      return NextResponse.json(
        { success: false, error: 'Invalid email or password' },
        { status: 401 }
      )
    }

    console.log('[LOGIN] Auth successful for:', email)

    // Query usuarios table with service role
    const supabaseAdmin = createClient(supabaseUrl, serviceKey)
    const { data: usuarios, error: dbError } = await supabaseAdmin
      .from('usuarios')
      .select('id, email, rol, cliente_id')
      .eq('email', email)
      .single()

    let usuario: Usuario | null = null
    if (!dbError && usuarios) {
      usuario = usuarios
      console.log('[LOGIN] Found usuario in DB:', { email: usuario.email, rol: usuario.rol })
    } else {
      console.log('[LOGIN] Usuario not in DB, using auth email')
      usuario = {
        id: authData.user.id,
        email,
        rol: 'admin',
      }
    }

    const rol = usuario?.rol || 'admin'
    const clienteId = usuario?.cliente_id || null

    console.log('[LOGIN] Final role:', rol)

    // Create JWT
    const secret = new TextEncoder().encode(jwtSecret)
    const token = await new SignJWT({
      sub: authData.user.id,
      email,
      rol,
      cliente_id: clienteId,
    })
      .setProtectedHeader({ alg: 'HS256' })
      .setExpirationTime('24h')
      .sign(secret)

    // Set cookie
    const cookieStore = await cookies()
    cookieStore.set('auth-token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24,
      path: '/',
    })

    return NextResponse.json({
      success: true,
      user: {
        id: authData.user.id,
        email,
        rol,
        cliente_id: clienteId,
      },
    })
  } catch (error) {
    console.error('[LOGIN] Error:', error)
    return NextResponse.json(
      { success: false, error: 'Server error' },
      { status: 500 }
    )
  }
}
