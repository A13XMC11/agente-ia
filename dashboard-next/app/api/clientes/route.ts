import { getClientes } from '@/lib/data/clientes-server'
import { getUserRole } from '@/lib/auth'

interface ApiResponse {
  success: boolean
  data?: any[]
  error?: string
}

export async function GET(): Promise<Response> {
  const role = await getUserRole()
  if (role !== 'super_admin') {
    return Response.json({ success: false, error: 'Unauthorized' } as ApiResponse, { status: 403 })
  }

  try {
    const clientes = await getClientes()
    return Response.json({ success: true, data: clientes } as ApiResponse)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error fetching clientes'
    return Response.json({ success: false, error: message } as ApiResponse, { status: 500 })
  }
}
