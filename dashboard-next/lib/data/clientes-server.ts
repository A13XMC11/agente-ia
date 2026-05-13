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

export async function getClientes(): Promise<Cliente[]> {
  try {
    const { data } = await supabase
      .from('clientes')
      .select('id, nombre, email, plan, estado, created_at, telefono, precio_mensual')
      .order('created_at', { ascending: false })

    return data || []
  } catch (error) {
    console.error('Error fetching clientes:', error)
    return []
  }
}

export async function searchClientes(query: string): Promise<Cliente[]> {
  try {
    const { data } = await supabase
      .from('clientes')
      .select('id, nombre, email, plan, estado, created_at, telefono, precio_mensual')
      .or(`nombre.ilike.%${query}%, email.ilike.%${query}%`)
      .order('created_at', { ascending: false })

    return data || []
  } catch (error) {
    console.error('Error searching clientes:', error)
    return []
  }
}
