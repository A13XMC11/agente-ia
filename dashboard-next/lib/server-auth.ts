import { jwtVerify } from 'jose'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export type SessionUser = {
  sub: string
  email: string
  role: 'super_admin' | 'admin' | 'operador'
  cliente_id?: string | null
}

export async function getServerSession(): Promise<SessionUser | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth-token')?.value
  if (!token) return null

  const jwtSecret = process.env.JWT_SECRET
  if (!jwtSecret) return null

  try {
    const secret = new TextEncoder().encode(jwtSecret)
    const { payload } = await jwtVerify(token, secret)

    const role = payload.role as 'super_admin' | 'admin' | 'operador'
    if (!role) return null

    return {
      sub: payload.sub as string,
      email: payload.email as string,
      role,
      cliente_id: (payload.cliente_id as string | null) ?? null,
    }
  } catch {
    return null
  }
}

export async function requireAuth(): Promise<SessionUser> {
  const session = await getServerSession()
  if (!session) {
    redirect('/sign-in')
  }
  return session as SessionUser
}

export async function requireRole(
  role: 'super_admin' | 'admin' | 'operador',
): Promise<SessionUser> {
  const session = await requireAuth()
  if (session.role !== role) {
    redirect('/')
  }
  return session
}
