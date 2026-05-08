// User & Auth
export interface User {
  id: string
  email: string
  role: 'super_admin' | 'admin' | 'operador'
  cliente_id?: string
  created_at: string
}

export interface AuthSession {
  user: User
  access_token: string
  expires_at: number
}

// Clientes
export interface Cliente {
  id: string
  nombre: string
  email: string
  telefono: string
  plan: 'starter' | 'professional' | 'enterprise'
  estado: 'activo' | 'pausado' | 'cancelado'
  stripe_customer_id?: string
  mrr: number
  created_at: string
  updated_at: string
}

// Agentes
export interface Agente {
  id: string
  cliente_id: string
  nombre: string
  tono: 'amigable' | 'formal' | 'profesional'
  idioma: string
  system_prompt: string
  modelo_ia: string
  temperature: number
  created_at: string
  updated_at: string
}

// Módulos Activos
export interface ModulosActivos {
  cliente_id: string
  ventas: boolean
  agendamiento: boolean
  cobros: boolean
  links_pago: boolean
  calificacion: boolean
  campanas: boolean
  analytics: boolean
  alertas: boolean
  seguimientos: boolean
  documentos: boolean
  multiidioma: boolean
  multi_agente: boolean
}

// Canales Config
export interface CanalConfig {
  id: string
  cliente_id: string
  canal: 'whatsapp' | 'instagram' | 'facebook' | 'email'
  phone_number_id?: string
  waba_id?: string
  token?: string
  activo: boolean
  created_at: string
}

// Conversaciones
export interface Conversacion {
  id: string
  cliente_id: string
  canal: 'whatsapp' | 'instagram' | 'facebook' | 'email'
  usuario_id: string
  usuario_nombre: string
  usuario_telefono: string
  estado: 'activa' | 'pausada' | 'cerrada'
  lead_score: number
  lead_state: 'nuevo' | 'contactado' | 'interesado' | 'propuesta' | 'ganado' | 'perdido'
  fecha_inicio: string
  fecha_ultimo_mensaje: string
  mensaje_count: number
  assigned_to?: string
  created_at: string
  updated_at: string
}

// Mensajes
export interface Mensaje {
  id: string
  conversacion_id: string
  cliente_id: string
  sender_id: string
  sender_type: 'user' | 'agent' | 'admin'
  contenido: string
  tipo: 'text' | 'image' | 'video' | 'document' | 'audio'
  media_url?: string
  created_at: string
}

// Leads
export interface Lead {
  id: string
  cliente_id: string
  conversacion_id?: string
  nombre: string
  telefono: string
  email?: string
  canal: 'whatsapp' | 'instagram' | 'facebook' | 'email'
  score: number
  estado: 'nuevo' | 'contactado' | 'interesado' | 'propuesta' | 'ganado' | 'perdido'
  urgencia: 'baja' | 'media' | 'alta'
  last_activity: string
  created_at: string
  updated_at: string
}

// Citas
export interface Cita {
  id: string
  cliente_id: string
  usuario_nombre: string
  usuario_telefono: string
  usuario_email?: string
  servicio: string
  fecha: string
  hora: string
  duracion: number // en minutos
  estado: 'confirmada' | 'pendiente' | 'cancelada' | 'completada'
  notas?: string
  google_event_id?: string
  created_at: string
  updated_at: string
}

// Alertas
export interface Alerta {
  id: string
  cliente_id: string
  tipo: 'critica' | 'importante' | 'info'
  titulo: string
  mensaje: string
  leida: boolean
  created_at: string
}

// API Responses
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

// Login Request/Response
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  success: boolean
  access_token?: string
  user?: User
  error?: string
}
