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

  // Use JWT role, or fall back to short-lived bridge cookie set by /api/auth/sync
  // while Clerk's JWT refreshes (JWT caches claims and doesn't update immediately)
  const roleCookie = request.cookies.get('_role_synced')
  const effectiveRole = meta.role || roleCookie?.value

  if (!effectiveRole) {
    // Non-GET requests (e.g. Clerk's internal signOut server actions) must not be
    // redirected to /api/auth/sync — that route only handles GET navigations.
    if (request.method !== 'GET') {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }
    const syncUrl = new URL('/api/auth/sync', request.url)
    syncUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(syncUrl)
  }

  // Role-based route enforcement
  if (
    (pathname.startsWith('/admin') ||
      pathname.startsWith('/api/admin') ||
      pathname.startsWith('/api/clientes')) &&
    effectiveRole !== 'super_admin'
  ) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 })
    }
    return NextResponse.redirect(new URL('/cliente', request.url))
  }

  if (pathname.startsWith('/cliente') && effectiveRole === 'super_admin') {
    return NextResponse.redirect(new URL('/admin', request.url))
  }

  return NextResponse.next()
})

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
}
