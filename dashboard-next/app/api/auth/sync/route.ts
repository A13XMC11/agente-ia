import { auth, currentUser, clerkClient } from '@clerk/nextjs/server'
import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'
import { SignJWT } from 'jose'

function createServiceClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  )
}

export async function GET(request: Request) {
  const { userId } = await auth()

  if (!userId) {
    return NextResponse.redirect(new URL('/sign-in', request.url))
  }

  const clerkUser = await currentUser()
  if (!clerkUser) {
    return NextResponse.redirect(new URL('/sign-in', request.url))
  }

  const email = clerkUser.emailAddresses[0]?.emailAddress
  if (!email) {
    return NextResponse.redirect(new URL('/sign-in', request.url))
  }

  const supabase = createServiceClient()
  const { data: usuario } = await supabase
    .from('usuarios')
    .select('rol, cliente_id, must_change_password')
    .eq('email', email)
    .single()

  const role = (usuario?.rol as 'super_admin' | 'admin' | 'operador') ?? 'admin'
  const cliente_id = usuario?.cliente_id ?? null
  const mustChangePassword = usuario?.must_change_password === true

  // Persist role and cliente_id into Clerk publicMetadata
  const clerk = await clerkClient()
  await clerk.users.updateUserMetadata(userId, {
    publicMetadata: { role, cliente_id, email },
  })

  // Force password change on first login — don't issue JWT yet
  if (mustChangePassword) {
    return NextResponse.redirect(new URL('/cambiar-contrasena', request.url))
  }

  // Issue custom JWT so API routes and server components work
  const jwtSecret = process.env.JWT_SECRET
  if (!jwtSecret) {
    return NextResponse.redirect(new URL('/sign-in', request.url))
  }

  const secret = new TextEncoder().encode(jwtSecret)
  const token = await new SignJWT({ sub: userId, email, role, cliente_id })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('24h')
    .sign(secret)

  const { searchParams } = new URL(request.url)
  const next = searchParams.get('next')
  const defaultDestination = role === 'super_admin' ? '/admin' : '/cliente'
  const destination = next && next.startsWith('/') ? next : defaultDestination

  const response = NextResponse.redirect(new URL(destination, request.url))

  response.cookies.set('auth-token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24,
    path: '/',
  })

  response.cookies.set('_role_synced', role, {
    maxAge: 300,
    path: '/',
    httpOnly: true,
    sameSite: 'lax',
  })

  return response
}
