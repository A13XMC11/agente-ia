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
  next_billing_date?: string | null
  subscription_status?: string | null
}

const CLIENTES_SELECT = '*'

export async function getClientes(): Promise<Cliente[]> {
  const { data, error } = await supabase
    .from('clientes')
    .select(CLIENTES_SELECT)
    .order('created_at', { ascending: false })

  if (error) throw new Error(error.message)
  const clientes = data || []
  if (clientes.length === 0) return clientes

  const ids = clientes.map((c) => c.id)
  const { data: subs } = await supabase
    .from('subscription')
    .select('cliente_id, next_billing_date, status')
    .in('cliente_id', ids)

  const subMap = new Map((subs || []).map((s) => [s.cliente_id, s]))

  return clientes.map((c) => ({
    ...c,
    next_billing_date: subMap.get(c.id)?.next_billing_date ?? null,
    subscription_status: subMap.get(c.id)?.status ?? null,
  }))
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
