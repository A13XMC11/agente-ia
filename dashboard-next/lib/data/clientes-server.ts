import { supabase } from '@/lib/supabase/server'

export interface Cliente {
  id: string
  nombre: string
  email: string
  plan: string
  estado: string
  created_at: string
  telefono?: string
  industria?: string
  whatsapp_dueño?: string
  website?: string
}

const CLIENTES_SELECT = 'id, nombre, email, plan, estado, created_at, telefono, industria, whatsapp_dueño, website'

export async function getClientes(): Promise<Cliente[]> {
  const { data, error } = await supabase
    .from('clientes')
    .select(CLIENTES_SELECT)
    .order('created_at', { ascending: false })

  if (error) throw new Error(error.message)
  return data || []
}

export async function searchClientes(query: string): Promise<Cliente[]> {
  try {
    const { data } = await supabase
      .from('clientes')
      .select(CLIENTES_SELECT)
      .or(`nombre.ilike.%${query}%, email.ilike.%${query}%`)
      .order('created_at', { ascending: false })

    return data || []
  } catch (error) {
    console.error('Error searching clientes:', error)
    return []
  }
}
