import { getSession } from './auth'

export async function getClienteId(): Promise<string | null> {
  const session = await getSession()
  return session?.cliente_id ?? null
}

export async function getCurrentUser() {
  const session = await getSession()
  if (!session) {
    throw new Error('Not authenticated')
  }
  return session
}
