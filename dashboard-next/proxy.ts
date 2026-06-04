import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { jwtVerify } from 'jose'

const isProtectedRoute = createRouteMatcher([
  '/admin(.*)',
  '/cliente(.*)',
  '/api/admin(.*)',
  '/api/cliente(.*)',
  '/api/clientes(.*)',
])
const isAdminOnlyRoute = createRouteMatcher([
  '/admin(.*)',
  '/api/admin(.*)',
  '/api/clientes(.*)',
])
const isClienteRoute = createRouteMatcher(['/cliente(.*)'])

export default clerkMiddleware(async (auth, request) => {
  if (!isProtectedRoute(request)) return

  await auth.protect()

  const { pathname } = request.nextUrl
  const token = request.cookies.get('auth-token')?.value
  const jwtSecret = process.env.JWT_SECRET

  if (!token || !jwtSecret) return

  let role: string | undefined
  try {
    const secret = new TextEncoder().encode(jwtSecret)
    const { payload } = await jwtVerify(token, secret)
    role = payload.role as string | undefined
  } catch {
    return
  }

  if (isAdminOnlyRoute(request) && role !== 'super_admin') {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 })
    }
    return NextResponse.redirect(new URL('/cliente', request.url))
  }

  if (isClienteRoute(request) && role === 'super_admin') {
    return NextResponse.redirect(new URL('/admin', request.url))
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
