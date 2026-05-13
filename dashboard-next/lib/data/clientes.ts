import { supabase } from '@/lib/supabase/server'

export interface Cliente {
  id: string
  nombre: string
  email: string
  plan: string
  estado: string
  created_at: string
  telefono?: string
  precio_mensual?: number
}

interface CreateClienteData {
  nombre: string
  email: string
  telefono: string
  plan: string
  precio_mensual?: number
  estado?: string
}

interface CreateClienteResult {
  success: boolean
  cliente?: Cliente
  error?: string
}

export async function createCliente(data: CreateClienteData): Promise<CreateClienteResult> {
  try {
    const { data: cliente, error } = await supabase
      .from('clientes')
      .insert([
        {
          nombre: data.nombre,
          email: data.email,
          telefono: data.telefono,
          plan: data.plan,
          precio_mensual: data.precio_mensual || 0,
          estado: data.estado || 'activo',
        },
      ])
      .select()
      .single()

    if (error) {
      return { success: false, error: error.message }
    }

    return { success: true, cliente }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error creating cliente'
    return { success: false, error: message }
  }
}

interface CreateAgentData {
  cliente_id: string
  nombre: string
  tono: string
  idioma: string
  modelo: string
  system_prompt: string
}

interface CreateAgentResult {
  success: boolean
  agent_id?: string
  error?: string
}

export async function createAgent(data: CreateAgentData): Promise<CreateAgentResult> {
  try {
    const { data: agent, error } = await supabase
      .from('agentes')
      .insert([
        {
          cliente_id: data.cliente_id,
          nombre: data.nombre,
          tono: data.tono,
          idioma: data.idioma,
          modelo: data.modelo,
          system_prompt: data.system_prompt,
        },
      ])
      .select('id')
      .single()

    if (error) {
      return { success: false, error: error.message }
    }

    return { success: true, agent_id: agent.id }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error creating agent'
    return { success: false, error: message }
  }
}

interface CreateModulosResult {
  success: boolean
  error?: string
}

export async function activateModulos(
  cliente_id: string,
  modulos: Record<string, boolean>
): Promise<CreateModulosResult> {
  try {
    const modulosActivos = Object.entries(modulos)
      .filter(([_, active]) => active)
      .map(([nombre]) => ({
        cliente_id,
        nombre: nombre.toLowerCase(),
      }))

    if (modulosActivos.length === 0) {
      return { success: true }
    }

    const { error } = await supabase.from('modulos_activos').insert(modulosActivos)

    if (error) {
      return { success: false, error: error.message }
    }

    return { success: true }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error activating modulos'
    return { success: false, error: message }
  }
}

interface CreateChannelConfigResult {
  success: boolean
  error?: string
}

export async function configureWhatsApp(
  cliente_id: string,
  phoneNumberId: string,
  token: string
): Promise<CreateChannelConfigResult> {
  try {
    const { error } = await supabase.from('canales_config').insert([
      {
        cliente_id,
        canal: 'whatsapp',
        phone_number_id: phoneNumberId,
        token,
        activo: true,
      },
    ])

    if (error) {
      return { success: false, error: error.message }
    }

    return { success: true }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Error configuring WhatsApp'
    return { success: false, error: message }
  }
}
