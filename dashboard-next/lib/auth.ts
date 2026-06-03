// Auth helpers — now backed by Clerk via lib/server-auth.ts
// Kept for backwards compatibility with existing imports.
export { getServerSession as getSession } from '@/lib/server-auth'
export type { SessionUser as User } from '@/lib/server-auth'

import { getServerSession } from '@/lib/server-auth'

export async function getUserRole(): Promise<'super_admin' | 'admin' | 'operador' | null> {
  const session = await getServerSession()
  return session?.role ?? null
}
