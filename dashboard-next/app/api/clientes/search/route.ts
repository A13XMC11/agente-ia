import { searchClientes } from '@/lib/data/clientes-server'
import { getUserRole } from '@/lib/auth'

interface ApiResponse {
  success: boolean
  data?: any[]
  error?: string
}

export async function GET(request: Request): Promise<Response> {
  const role = await getUserRole()
  if (role !== 'super_admin') {
    return Response.json({ success: false, error: 'Unauthorized' } as ApiResponse, { status: 403 })
  }

  try {
    const url = new URL(request.url)
    const query = url.searchParams.get('q')

    if (!query) {
      return Response.json(
        {
          success: false,
          error: 'Search query is required',
        } as ApiResponse,
        { status: 400 }
      )
    }

    const clientes = await searchClientes(query)
    return Response.json({
      success: true,
      data: clientes,
    } as ApiResponse)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error searching clientes'
    return Response.json(
      {
        success: false,
        error: message,
      } as ApiResponse,
      { status: 500 }
    )
  }
}
