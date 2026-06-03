import { auth, currentUser } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'

export type SessionUser = {
  sub: string
  email: string
  role: 'super_admin' | 'admin' | 'operador'
  cliente_id?: string | null
}

type ClerkPublicMetadata = {
  role?: 'super_admin' | 'admin' | 'operador'
  cliente_id?: string
  email?: string
}

export async function getServerSession(): Promise<SessionUser | null> {
  const { userId } = await auth()
  if (!userId) return null

  const clerkUser = await currentUser()
  if (!clerkUser) return null

  const meta = (clerkUser.publicMetadata ?? {}) as ClerkPublicMetadata

  // No role means sync hasn't run yet — treat as unauthenticated
  if (!meta.role) return null

  const email =
    meta.email ?? clerkUser.emailAddresses[0]?.emailAddress ?? ''

  return {
    sub: userId,
    email,
    role: meta.role,
    cliente_id: meta.cliente_id ?? null,
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
