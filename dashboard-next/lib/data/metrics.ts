import { supabase } from '@/lib/supabase/server'

const PLAN_PRECIOS: Record<string, number> = {
  basico: 149,
  profesional: 249,
  empresarial: 399,
}

interface PlanDistribucion {
  plan: string
  label: string
  count: number
  mrr: number
  porcentaje: number
}

export interface Metrics {
  totalClientes: number
  clientesActivos: number
  clientesPausados: number
  mrr: number
  arr: number
  arpu: number
  mrrNuevoEsteMes: number
  mrrPerdidoEsteMes: number
  mensajesHoy: number
  churnRate: number
  clientesNuevosEsteMes: number
  clientesNuevosMesAnterior: number
  crecimientoClientes: number
  distribucionPlanes: PlanDistribucion[]
}

interface ClienteReciente {
  id: string
  nombre: string
  email: string
  plan: string
  estado: string
  created_at: string
}

function calcMrr(clientes: { plan: string }[]): number {
  return clientes.reduce((sum, c) => sum + (PLAN_PRECIOS[c.plan?.toLowerCase()] || 0), 0)
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function startOfPrevMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() - 1, 1)
}

export async function getMetrics(): Promise<Metrics> {
  try {
    const now = new Date()
    const inicioEsteMes = startOfMonth(now)
    const inicioPrevMes = startOfPrevMonth(now)

    const [
      { data: todosClientes },
      { count: mensajesHoy },
      { data: nuevosEsteMes },
      { data: nuevosPrevMes },
      { data: pausadosEsteMes },
    ] = await Promise.all([
      supabase.from('clientes').select('id, plan, estado, created_at'),
      supabase
        .from('mensajes')
        .select('*', { count: 'exact', head: true })
        .gte('created_at', (() => { const d = new Date(); d.setHours(0,0,0,0); return d.toISOString() })()),
      supabase
        .from('clientes')
        .select('plan, estado')
        .gte('created_at', inicioEsteMes.toISOString()),
      supabase
        .from('clientes')
        .select('plan')
        .gte('created_at', inicioPrevMes.toISOString())
        .lt('created_at', inicioEsteMes.toISOString()),
      supabase
        .from('clientes')
        .select('plan')
        .neq('estado', 'activo')
        .gte('updated_at', inicioEsteMes.toISOString()),
    ])

    const todos = todosClientes || []
    const activos = todos.filter((c) => c.estado === 'activo')
    const pausados = todos.filter((c) => c.estado !== 'activo')

    const mrr = calcMrr(activos)
    const arr = mrr * 12
    const arpu = activos.length > 0 ? Math.round(mrr / activos.length) : 0

    const nuevosActivosEsteMes = (nuevosEsteMes || []).filter((c) => c.estado === 'activo')
    const mrrNuevoEsteMes = calcMrr(nuevosActivosEsteMes)
    const mrrPerdidoEsteMes = calcMrr(pausadosEsteMes || [])

    const churnRate =
      todos.length > 0 ? Math.round((pausados.length / todos.length) * 100 * 10) / 10 : 0

    const clientesNuevosEsteMes = (nuevosEsteMes || []).length
    const clientesNuevosMesAnterior = (nuevosPrevMes || []).length
    const crecimientoClientes =
      clientesNuevosMesAnterior > 0
        ? Math.round(((clientesNuevosEsteMes - clientesNuevosMesAnterior) / clientesNuevosMesAnterior) * 100)
        : clientesNuevosEsteMes > 0 ? 100 : 0

    const PLAN_LABELS: Record<string, string> = {
      basico: 'Básico',
      profesional: 'Profesional',
      empresarial: 'Empresarial',
    }

    const planCounts: Record<string, number> = {}
    for (const c of activos) {
      const p = c.plan?.toLowerCase() || 'basico'
      planCounts[p] = (planCounts[p] || 0) + 1
    }

    const distribucionPlanes: PlanDistribucion[] = Object.entries(PLAN_PRECIOS).map(([plan, precio]) => {
      const count = planCounts[plan] || 0
      const planMrr = count * precio
      return {
        plan,
        label: PLAN_LABELS[plan] || plan,
        count,
        mrr: planMrr,
        porcentaje: activos.length > 0 ? Math.round((count / activos.length) * 100) : 0,
      }
    })

    return {
      totalClientes: todos.length,
      clientesActivos: activos.length,
      clientesPausados: pausados.length,
      mrr,
      arr,
      arpu,
      mrrNuevoEsteMes,
      mrrPerdidoEsteMes,
      mensajesHoy: mensajesHoy || 0,
      churnRate,
      clientesNuevosEsteMes,
      clientesNuevosMesAnterior,
      crecimientoClientes,
      distribucionPlanes,
    }
  } catch (error) {
    console.error('Error fetching metrics:', error)
    return {
      totalClientes: 0,
      clientesActivos: 0,
      clientesPausados: 0,
      mrr: 0,
      arr: 0,
      arpu: 0,
      mrrNuevoEsteMes: 0,
      mrrPerdidoEsteMes: 0,
      mensajesHoy: 0,
      churnRate: 0,
      clientesNuevosEsteMes: 0,
      clientesNuevosMesAnterior: 0,
      crecimientoClientes: 0,
      distribucionPlanes: [],
    }
  }
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
