export interface User {
  sub: string
  email: string
  role: 'super_admin' | 'admin' | 'operador'
  cliente_id?: string | null
}

export interface Metrics {
  totalClientes: number
  mrr: number
  mensajesHoy: number
}

export interface Cliente {
  id: string
  nombre: string
  email: string
  plan: string
  estado: 'activo' | 'pausado' | 'cancelado'
  created_at: string
  telefono?: string
  precio_mensual?: number
}

export interface Agent {
  id: string
  cliente_id: string
  nombre: string
  tono: 'Amigable' | 'Formal' | 'Profesional'
  idioma: 'Español' | 'Inglés' | 'Portugués'
  modelo: 'GPT-4o' | 'GPT-4 Turbo' | 'GPT-3.5 Turbo'
  system_prompt: string
  created_at: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total: number
    page: number
    limit: number
  }
}
