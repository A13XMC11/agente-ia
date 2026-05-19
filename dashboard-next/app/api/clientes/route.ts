import { getClientes } from '@/lib/data/clientes-server'

interface ApiResponse {
  success: boolean
  data?: any[]
  error?: string
}

export async function GET(): Promise<Response> {
  console.log('[ADMIN CLIENTES] fetching...')
  try {
    const clientes = await getClientes()
    console.log('[ADMIN CLIENTES] result:', clientes)
    return Response.json({
      success: true,
      data: clientes,
    } as ApiResponse)
  } catch (error) {
    console.log('[ADMIN CLIENTES] error:', error)
    const message = error instanceof Error ? error.message : 'Error fetching clientes'
    return Response.json(
      {
        success: false,
        error: message,
      } as ApiResponse,
      { status: 500 }
    )
  }
}
