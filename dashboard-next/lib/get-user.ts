import { getServerSession } from './server-auth'

export async function getClienteId(): Promise<string | null> {
  const session = await getServerSession()
  return session?.cliente_id ?? null
}

export async function getCurrentUser() {
  const session = await getServerSession()
  if (!session) {
    throw new Error('Not authenticated')
  }
  return session
}
