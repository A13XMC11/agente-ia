import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

const isPublicRoute = createRouteMatcher([
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/login(.*)',
  '/api/auth/sync(.*)',
  '/onboarding(.*)',
  '/api/auth/logout(.*)',
])

export const proxy = clerkMiddleware(async (auth, request) => {
  const { userId, sessionClaims } = await auth()
  const { pathname } = new URL(request.url)

  if (isPublicRoute(request)) {
    return NextResponse.next()
  }

  // Unauthenticated → redirect to Clerk sign-in
  if (!userId) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }
    const signIn = new URL('/sign-in', request.url)
    signIn.searchParams.set('redirect_url', request.url)
    return NextResponse.redirect(signIn)
  }

  // Authenticated but role not yet synced → sync
  const meta = (sessionClaims?.publicMetadata ?? {}) as {
    role?: string
    cliente_id?: string
  }

  if (!meta.role) {
    return NextResponse.redirect(new URL('/api/auth/sync', request.url))
  }

  // Role-based route enforcement
  if (
    (pathname.startsWith('/admin') ||
      pathname.startsWith('/api/admin') ||
      pathname.startsWith('/api/clientes')) &&
    meta.role !== 'super_admin'
  ) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 })
    }
    return NextResponse.redirect(new URL('/cliente', request.url))
  }

  if (pathname.startsWith('/cliente') && meta.role === 'super_admin') {
    return NextResponse.redirect(new URL('/admin', request.url))
  }

  return NextResponse.next()
})

export const proxyConfig = {
  matcher: [
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
}
