import { NextResponse } from 'next/server'
import { auth, currentUser } from '@clerk/nextjs/server'
import { createClient } from '@supabase/supabase-js'
import { SignJWT } from 'jose'

function createServiceClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  )
}

// Password already updated by Clerk client-side (user.updatePassword).
// This route only clears the must_change_password flag and issues the custom JWT.
export async function POST() {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ success: false, error: 'No autenticado' }, { status: 401 })
  }

  const clerkUser = await currentUser()
  const email = clerkUser?.emailAddresses[0]?.emailAddress
  if (!email) {
    return NextResponse.json({ success: false, error: 'Email no encontrado' }, { status: 400 })
  }

  const supabase = createServiceClient()

  // Clear the flag
  await supabase
    .from('usuarios')
    .update({ must_change_password: false })
    .eq('email', email)

  // Fetch role and cliente_id
  const { data: usuario } = await supabase
    .from('usuarios')
    .select('rol, cliente_id')
    .eq('email', email)
    .single()

  const role = (usuario?.rol as 'super_admin' | 'admin' | 'operador') ?? 'admin'
  const cliente_id = usuario?.cliente_id ?? null

  // Issue custom JWT
  const jwtSecret = process.env.JWT_SECRET
  if (!jwtSecret) {
    return NextResponse.json({ success: false, error: 'Missing JWT secret' }, { status: 500 })
  }

  const secret = new TextEncoder().encode(jwtSecret)
  const token = await new SignJWT({ sub: userId, email, role, cliente_id })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('24h')
    .sign(secret)

  const response = NextResponse.json({
    success: true,
    user: { role, cliente_id },
  })

  response.cookies.set('auth-token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24,
    path: '/',
  })

  return response
}
