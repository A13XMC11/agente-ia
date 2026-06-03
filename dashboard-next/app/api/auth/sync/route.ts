import { auth, currentUser, clerkClient } from '@clerk/nextjs/server'
import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

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

  // Look up role and cliente_id from Supabase
  const supabase = createServiceClient()
  const { data: usuario } = await supabase
    .from('usuarios')
    .select('rol, cliente_id')
    .eq('email', email)
    .single()

  const role = (usuario?.rol as 'super_admin' | 'admin' | 'operador') ?? 'admin'
  const cliente_id = usuario?.cliente_id ?? null

  // Persist role and cliente_id into Clerk publicMetadata
  const clerk = await clerkClient()
  await clerk.users.updateUserMetadata(userId, {
    publicMetadata: { role, cliente_id, email },
  })

  // Route to the right dashboard (respect ?next= param set by middleware)
  const { searchParams } = new URL(request.url)
  const next = searchParams.get('next')
  const defaultDestination = role === 'super_admin' ? '/admin' : '/cliente'
  const destination = next && next.startsWith('/') ? next : defaultDestination

  const response = NextResponse.redirect(new URL(destination, request.url))
  // Bridge cookie: lets middleware allow through while Clerk JWT refreshes (~1 min)
  response.cookies.set('_role_synced', role, {
    maxAge: 300,
    path: '/',
    httpOnly: true,
    sameSite: 'lax',
  })
  return response
}
