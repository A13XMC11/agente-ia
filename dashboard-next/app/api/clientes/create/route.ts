import { createCliente, createAgent, activateModulos, configureWhatsApp } from '@/lib/data/clientes'

interface CreateClienteRequest {
  nombre: string
  email: string
  telefono: string
  plan: string
  precio_mensual: number
  nombreAgente: string
  tono: string
  idioma: string
  modelo: string
  systemPrompt: string
  modulos: Record<string, boolean>
  whatsappEnabled: boolean
  whatsappPhone?: string
  whatsappToken?: string
}

interface ApiResponse {
  success: boolean
  data?: any
  error?: string
}

export async function POST(request: Request): Promise<Response> {
  try {
    const body: CreateClienteRequest = await request.json()

    // Validate required fields
    if (!body.nombre || !body.email || !body.telefono) {
      return Response.json(
        { success: false, error: 'Missing required client fields' } as ApiResponse,
        { status: 400 }
      )
    }

    if (!body.nombreAgente || !body.systemPrompt) {
      return Response.json(
        { success: false, error: 'Missing required agent fields' } as ApiResponse,
        { status: 400 }
      )
    }

    // 1. Create cliente
    const clienteResult = await createCliente({
      nombre: body.nombre,
      email: body.email,
      telefono: body.telefono,
      plan: body.plan,
      precio_mensual: body.precio_mensual,
    })

    if (!clienteResult.success || !clienteResult.cliente) {
      throw new Error(clienteResult.error || 'Error creating client')
    }

    const clienteId = clienteResult.cliente.id

    // 2. Create agent
    const agentResult = await createAgent({
      cliente_id: clienteId,
      nombre: body.nombreAgente,
      tono: body.tono,
      idioma: body.idioma,
      modelo: body.modelo,
      system_prompt: body.systemPrompt,
    })

    if (!agentResult.success) {
      throw new Error(agentResult.error || 'Error creating agent')
    }

    // 3. Activate modules
    const modulosResult = await activateModulos(clienteId, body.modulos)
    if (!modulosResult.success) {
      throw new Error(modulosResult.error || 'Error activating modules')
    }

    // 4. Configure WhatsApp if enabled
    if (body.whatsappEnabled && body.whatsappPhone && body.whatsappToken) {
      const whatsappResult = await configureWhatsApp(clienteId, body.whatsappPhone, body.whatsappToken)
      if (!whatsappResult.success) {
        throw new Error(whatsappResult.error || 'Error configuring WhatsApp')
      }
    }

    return Response.json({
      success: true,
      data: { clienteId },
    } as ApiResponse)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error creating cliente'
    return Response.json(
      {
        success: false,
        error: message,
      } as ApiResponse,
      { status: 500 }
    )
  }
}
