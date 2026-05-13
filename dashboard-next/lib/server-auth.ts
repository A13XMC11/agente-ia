import { jwtVerify } from 'jose'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import type { User } from '@/types'

const secretKey = new TextEncoder().encode(
  process.env.JWT_SECRET || 'your-secret-key-change-this-in-production',
)

export async function getServerSession(): Promise<User | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth-token')?.value

  if (!token) {
    return null
  }

  try {
    const verified = await jwtVerify(token, secretKey)
    return verified.payload as unknown as User
  } catch {
    return null
  }
}

export async function requireAuth(): Promise<User> {
  const session = await getServerSession()

  if (!session) {
    redirect('/login')
  }

  return session
}

export async function requireRole(role: 'super_admin' | 'admin' | 'operador'): Promise<User> {
  const session = await requireAuth()

  if (session.role !== role) {
    redirect('/')
  }

  return session
}
