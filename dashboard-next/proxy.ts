import { NextRequest, NextResponse } from 'next/server'
import { jwtVerify } from 'jose'

const jwtSecret = process.env.JWT_SECRET
const secretKey = jwtSecret ? new TextEncoder().encode(jwtSecret) : null

const PUBLIC_PATHS = ['/login', '/api/auth/login', '/api/auth/logout', '/onboarding']

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  const isProtected =
    pathname.startsWith('/cliente') ||
    pathname.startsWith('/admin') ||
    pathname.startsWith('/api/cliente') ||
    pathname.startsWith('/api/admin') ||
    pathname.startsWith('/api/clientes')

  if (!isProtected) {
    return NextResponse.next()
  }

  const token = request.cookies.get('auth-token')?.value

  if (!token || !secretKey) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }
    return NextResponse.redirect(new URL('/login', request.url))
  }

  try {
    const { payload } = await jwtVerify(token, secretKey)

    if (
      pathname.startsWith('/admin') ||
      pathname.startsWith('/api/admin') ||
      pathname.startsWith('/api/clientes')
    ) {
      if (payload.role !== 'super_admin') {
        if (pathname.startsWith('/api/')) {
          return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 })
        }
        return NextResponse.redirect(new URL('/cliente', request.url))
      }
    }

    return NextResponse.next()
  } catch {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 })
    }
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
}
