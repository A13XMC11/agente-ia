import { supabase } from '@/lib/supabase/server'

interface Metrics {
  totalClientes: number
  mrr: number
  mensajesHoy: number
}

export async function getMetrics(): Promise<Metrics> {
  try {
    // Total de clientes
    const { count: totalClientes } = await supabase
      .from('clientes')
      .select('*', { count: 'exact', head: true })

    // MRR (Monthly Recurring Revenue)
    const { data: mrrData } = await supabase
      .from('clientes')
      .select('precio_mensual')
      .eq('estado', 'activo')

    const mrr = (mrrData || []).reduce((sum, client) => {
      return sum + (client.precio_mensual || 0)
    }, 0)

    // Mensajes hoy
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const { count: mensajesHoy } = await supabase
      .from('mensajes')
      .select('*', { count: 'exact', head: true })
      .gte('created_at', today.toISOString())

    return {
      totalClientes: totalClientes || 0,
      mrr,
      mensajesHoy: mensajesHoy || 0,
    }
  } catch (error) {
    console.error('Error fetching metrics:', error)
    return {
      totalClientes: 0,
      mrr: 0,
      mensajesHoy: 0,
    }
  }
}

interface ClienteReciente {
  id: string
  nombre: string
  email: string
  plan: string
  estado: string
  created_at: string
}

export async function getClientesRecientes(): Promise<ClienteReciente[]> {
  try {
    const { data } = await supabase
      .from('clientes')
      .select('id, nombre, email, plan, estado, created_at')
      .order('created_at', { ascending: false })
      .limit(5)

    return data || []
  } catch (error) {
    console.error('Error fetching recent clients:', error)
    return []
  }
}
