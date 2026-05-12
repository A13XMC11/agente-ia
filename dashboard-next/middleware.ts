import { NextRequest, NextResponse } from 'next/server'
import { jwtVerify } from 'jose'

const secretKey = new TextEncoder().encode(
  process.env.JWT_SECRET || 'your-secret-key-change-this-in-production',
)

async function verifyJWT(token: string) {
  try {
    const verified = await jwtVerify(token, secretKey)
    return verified.payload as unknown
  } catch {
    return null
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow login and public routes without token verification
  if (pathname === '/login' || pathname === '/api/auth/login' || pathname.startsWith('/api/auth')) {
    return NextResponse.next()
  }

  // Get token from cookies
  const token = request.cookies.get('auth-token')?.value

  if (!token) {
    // No token, redirect to login
    if (pathname !== '/login') {
      return NextResponse.redirect(new URL('/login', request.url))
    }
    return NextResponse.next()
  }

  // Verify token
  const user = await verifyJWT(token)

  if (!user) {
    // Invalid token, redirect to login
    if (pathname !== '/login') {
      return NextResponse.redirect(new URL('/login', request.url))
    }
    return NextResponse.next()
  }

  // Role-based access control
  const userRole = (user as any).role

  // Admin routes - only super_admin
  if (pathname.startsWith('/admin')) {
    if (userRole !== 'super_admin') {
      return NextResponse.redirect(new URL('/cliente', request.url))
    }
  }

  // Cliente routes - only non-super_admin users (admin, operador, cliente)
  if (pathname.startsWith('/cliente')) {
    if (userRole === 'super_admin') {
      return NextResponse.redirect(new URL('/admin', request.url))
    }
    // Verify role is valid for cliente area
    if (userRole !== 'admin' && userRole !== 'operador' && userRole !== 'cliente') {
      return NextResponse.redirect(new URL('/login', request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
