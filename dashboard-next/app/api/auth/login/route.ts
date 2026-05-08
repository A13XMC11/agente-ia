import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'
import type { LoginRequest, LoginResponse, User } from '@/types'

interface SupabaseAuthResponse {
  access_token: string
  expires_in: number
  user: {
    id: string
    email: string
  }
}

export async function POST(request: NextRequest): Promise<NextResponse<LoginResponse>> {
  try {
    const body: LoginRequest = await request.json()

    if (!body.email || !body.password) {
      return NextResponse.json(
        {
          success: false,
          error: 'Email and password are required',
        },
        { status: 400 },
      )
    }

    // Environment variables
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
    const jwtSecret = process.env.JWT_SECRET
    const superAdminEmail = process.env.SUPER_ADMIN_EMAIL

    console.log('[AUTH/LOGIN] Step 1: Environment check')
    console.log('  NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl ? '✓' : '✗')
    console.log('  NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseKey ? '✓' : '✗')
    console.log('  SUPABASE_SERVICE_ROLE_KEY:', supabaseServiceKey ? '✓' : '✗')
    console.log('  JWT_SECRET:', jwtSecret ? '✓' : '✗')
    console.log('  SUPER_ADMIN_EMAIL:', superAdminEmail || 'not set')
    console.log('[AUTH/LOGIN] Email:', body.email)

    if (!supabaseUrl || !supabaseKey) {
      console.error('[AUTH/LOGIN] Configuration error - missing Supabase credentials')
      return NextResponse.json(
        {
          success: false,
          error: 'Server configuration error',
        },
        { status: 500 },
      )
    }

    // Step 2: Authenticate with Supabase Auth
    console.log('[AUTH/LOGIN] Step 2: Authenticating with Supabase Auth')
    const authResponse = await fetch(
      `${supabaseUrl}/auth/v1/token?grant_type=password`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          apikey: supabaseKey,
        },
        body: JSON.stringify({
          email: body.email,
          password: body.password,
        }),
      },
    )

    console.log('[AUTH/LOGIN] Supabase Auth response status:', authResponse.status)

    if (!authResponse.ok) {
      const error = await authResponse.json()
      console.error('[AUTH/LOGIN] Supabase Auth error:', JSON.stringify(error))
      return NextResponse.json(
        {
          success: false,
          error: error.error_description || 'Authentication failed',
        },
        { status: 401 },
      )
    }

    const authData: SupabaseAuthResponse = await authResponse.json()
    console.log('[AUTH/LOGIN] Auth successful, user ID:', authData.user.id)
    console.log('[AUTH/LOGIN] Access token expires in:', authData.expires_in, 'seconds')

    // Step 3: Check if user exists in usuarios table
    console.log('[AUTH/LOGIN] Step 3: Checking usuarios table')
    if (!supabaseServiceKey) {
      console.error('[AUTH/LOGIN] Service role key missing - cannot query usuarios table')
      return NextResponse.json(
        {
          success: false,
          error: 'Server configuration error',
        },
        { status: 500 },
      )
    }

    const usuariosResponse = await fetch(
      `${supabaseUrl}/rest/v1/usuarios?email=eq.${encodeURIComponent(body.email)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          apikey: supabaseServiceKey,
          Authorization: `Bearer ${supabaseServiceKey}`,
        },
      },
    )

    console.log('[AUTH/LOGIN] Usuarios table query status:', usuariosResponse.status)

    let usuario: User | null = null

    if (usuariosResponse.ok) {
      const usuarios = await usuariosResponse.json()
      console.log('[AUTH/LOGIN] Found', usuarios.length, 'usuario(s) with email:', body.email)

      if (usuarios.length > 0) {
        usuario = usuarios[0]
        // Ensure role is never undefined
        if (!usuario.role) {
          usuario.role = superAdminEmail && body.email === superAdminEmail ? 'super_admin' : 'admin'
        }
        console.log('[AUTH/LOGIN] User found in DB - Role:', usuario.role)
      } else {
        // Step 4: User doesn't exist - create one
        console.log('[AUTH/LOGIN] Step 4: User not found, creating new user')

        const defaultRole =
          superAdminEmail && body.email === superAdminEmail ? 'super_admin' : 'admin'
        console.log('[AUTH/LOGIN] Assigning default role:', defaultRole)

        const newUser: User = {
          id: authData.user.id,
          email: body.email,
          role: defaultRole,
          created_at: new Date().toISOString(),
        }

        const createResponse = await fetch(
          `${supabaseUrl}/rest/v1/usuarios`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              apikey: supabaseServiceKey,
              Authorization: `Bearer ${supabaseServiceKey}`,
              Prefer: 'return=representation',
            },
            body: JSON.stringify(newUser),
          },
        )

        console.log('[AUTH/LOGIN] Create usuario response status:', createResponse.status)

        if (createResponse.ok) {
          const createdUsers = await createResponse.json()
          usuario = createdUsers[0] || newUser
          console.log('[AUTH/LOGIN] User created successfully with role:', usuario.role)
        } else {
          const createError = await createResponse.json()
          console.error('[AUTH/LOGIN] Failed to create user:', JSON.stringify(createError))
          usuario = newUser // Fall back to new user object
        }
      }
    } else {
      const queryError = await usuariosResponse.json()
      console.error('[AUTH/LOGIN] Failed to query usuarios table:', JSON.stringify(queryError))
      // Continue anyway with a default user
      const defaultRole = superAdminEmail && body.email === superAdminEmail ? 'super_admin' : 'admin'
      usuario = {
        id: authData.user.id,
        email: body.email,
        role: defaultRole,
        created_at: new Date().toISOString(),
      }
    }

    // Ensure role is never undefined
    if (!usuario || !usuario.role) {
      const defaultRole = superAdminEmail && body.email === superAdminEmail ? 'super_admin' : 'admin'
      usuario = usuario || {
        id: authData.user.id,
        email: body.email,
        role: defaultRole,
        created_at: new Date().toISOString(),
      }
      if (!usuario.role) {
        usuario.role = defaultRole
      }
    }

    // Step 5: Set auth cookie
    console.log('[AUTH/LOGIN] Step 5: Setting auth cookie')
    const cookieStore = await cookies()
    cookieStore.set('auth-token', authData.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: authData.expires_in || 3600,
      path: '/',
    })

    // Set user role cookie for client-side access
    cookieStore.set('user-role', usuario.role, {
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: authData.expires_in || 3600,
      path: '/',
    })

    console.log('[AUTH/LOGIN] Step 6: Login successful')
    console.log('[AUTH/LOGIN] User:', {
      id: usuario.id,
      email: usuario.email,
      role: usuario.role,
    })

    return NextResponse.json(
      {
        success: true,
        access_token: authData.access_token,
        user: usuario,
      },
      { status: 200 },
    )
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'An error occurred'
    console.error('[AUTH/LOGIN] Unexpected error:', {
      message,
      stack: error instanceof Error ? error.stack : String(error),
    })
    return NextResponse.json(
      {
        success: false,
        error: message,
      },
      { status: 500 },
    )
  }
}
