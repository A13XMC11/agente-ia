import { NextResponse } from 'next/server'
import { jwtVerify, SignJWT } from 'jose'
import { cookies } from 'next/headers'

const TWO_HOURS_MS = 2 * 60 * 60 * 1000

export async function POST() {
  try {
    const jwtSecret = process.env.JWT_SECRET
    if (!jwtSecret) {
      return NextResponse.json({ success: false, error: 'Missing configuration' }, { status: 500 })
    }

    const secretKey = new TextEncoder().encode(jwtSecret)
    const cookieStore = await cookies()
    const token = cookieStore.get('auth-token')?.value

    if (!token) {
      return NextResponse.json({ success: false, error: 'No session' }, { status: 401 })
    }

    const { payload } = await jwtVerify(token, secretKey)

    // Only refresh if token expires within 2 hours
    const expiresAt = (payload.exp ?? 0) * 1000
    const now = Date.now()
    if (expiresAt - now > TWO_HOURS_MS) {
      return NextResponse.json({ success: true, refreshed: false })
    }

    const newToken = await new SignJWT({
      sub: payload.sub,
      email: payload.email,
      role: payload.role,
      cliente_id: payload.cliente_id,
    })
      .setProtectedHeader({ alg: 'HS256' })
      .setExpirationTime('24h')
      .sign(secretKey)

    cookieStore.set('auth-token', newToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24,
      path: '/',
    })

    return NextResponse.json({ success: true, refreshed: true })
  } catch {
    return NextResponse.json({ success: false, error: 'Invalid session' }, { status: 401 })
  }
}
