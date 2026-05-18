import { createCliente, createAgent, activateModulos, configureWhatsApp, saveDatosBancarios } from '@/lib/data/clientes'
import { randomBytes } from 'crypto'

interface CreateClienteRequest {
  nombre: string
  email: string
  telefono: string
  whatsapp_dueno?: string
  industria?: string
  website?: string
  plan: 'basico' | 'profesional' | 'empresarial'
  nombreAgente: string
  tono: string
  idioma: string
  modelo: string
  systemPrompt: string
  modulos: Record<string, boolean>
  whatsappEnabled: boolean
  whatsappPhone?: string
  whatsappToken?: string
  whatsappWabaId?: string
  banco?: string
  tipo_cuenta?: string
  numero_cuenta?: string
  titular?: string
  ruc?: string
}

interface ApiResponse {
  success: boolean
  data?: { clienteId: string; email: string; password: string }
  error?: string
}

const VALID_PLANS = ['basico', 'profesional', 'empresarial'] as const

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

    const plan = VALID_PLANS.includes(body.plan) ? body.plan : 'basico'

    // 1. Create cliente
    const clienteResult = await createCliente({
      nombre: body.nombre,
      email: body.email,
      telefono: body.telefono,
      plan,
      industria: body.industria,
      whatsapp_dueno: body.whatsapp_dueno,
      website: body.website,
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
      const whatsappResult = await configureWhatsApp(
        clienteId,
        body.whatsappPhone,
        body.whatsappToken,
        body.whatsappWabaId
      )
      if (!whatsappResult.success) {
        throw new Error(whatsappResult.error || 'Error configuring WhatsApp')
      }
    }

    // 5. Save bank data if provided
    if (body.banco && body.numero_cuenta && body.titular) {
      const bancosResult = await saveDatosBancarios({
        cliente_id: clienteId,
        banco: body.banco,
        tipo_cuenta: body.tipo_cuenta || 'ahorros',
        numero_cuenta: body.numero_cuenta,
        titular: body.titular,
        ruc: body.ruc,
      })
      if (!bancosResult.success) {
        throw new Error(bancosResult.error || 'Error saving bank data')
      }
    }

    // Generate a temporary password for the client
    const tempPassword = randomBytes(6).toString('hex')

    return Response.json({
      success: true,
      data: {
        clienteId,
        email: body.email,
        password: tempPassword,
      },
    } as ApiResponse)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error creating cliente'
    return Response.json(
      { success: false, error: message } as ApiResponse,
      { status: 500 }
    )
  }
}
