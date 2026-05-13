import axios, { type AxiosInstance } from 'axios'
import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.lanlabsec.com'

async function getAuthHeader(): Promise<Record<string, string>> {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('auth-token')?.value

    return token
      ? { Authorization: `Bearer ${token}` }
      : {}
  } catch {
    return {}
  }
}

export async function getApiClient(): Promise<AxiosInstance> {
  const authHeader = await getAuthHeader()

  return axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
      ...authHeader,
    },
  })
}

// API endpoints
export async function getConversations(clientId: string) {
  const client = await getApiClient()
  return client.get(`/api/clients/${clientId}/conversations`)
}

export async function getLeads(clientId: string) {
  const client = await getApiClient()
  return client.get(`/api/clients/${clientId}/leads`)
}

export async function getHealth() {
  const client = await getApiClient()
  return client.get('/health')
}

export async function getReadiness() {
  const client = await getApiClient()
  return client.get('/health/ready')
}
