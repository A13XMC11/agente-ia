import { createCliente, createAgent, activateModulos, configureWhatsApp, saveDatosBancarios } from '@/lib/data/clientes'
import { getUserRole } from '@/lib/auth'
import { supabase } from '@/lib/supabase/server'
import { clerkClient } from '@clerk/nextjs/server'
import { randomBytes, randomUUID } from 'crypto'

const DASHBOARD_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'https://dashboard.lanlabsec.com'
const EMAIL_API_URL = 'https://api.lanlabsec.com/internal/send-email'

async function sendWelcomeEmail({
  nombre,
  email,
  password,
}: {
  nombre: string
  email: string
  password: string
}) {
  const body = `
Hola ${nombre},

¡Bienvenido a LanLabs! Tu agente IA ya está configurado y listo para activar.

━━━━━━━━━━━━━━━━━━━━━━━━
ACCESO AL DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━
URL:        ${DASHBOARD_URL}
Email:      ${email}
Contraseña: ${password}

Te recomendamos cambiar tu contraseña en el primer inicio de sesión.

━━━━━━━━━━━━━━━━━━━━━━━━
SIGUIENTE PASO: CONECTAR WHATSAPP
━━━━━━━━━━━━━━━━━━━━━━━━
Para activar tu agente en WhatsApp sigue esta guía completa:
${DASHBOARD_URL}/onboarding/guia

Dentro del dashboard ve a:
Configuración → WhatsApp → Verificar y conectar

━━━━━━━━━━━━━━━━━━━━━━━━
¿NECESITAS AYUDA?
━━━━━━━━━━━━━━━━━━━━━━━━
Responde este correo o escríbenos a soporte@lanlabsec.com

¡Estamos aquí para ayudarte!

— El equipo de LanLabs
`.trim()

  const res = await fetch(EMAIL_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      to: email,
      subject: 'Bienvenido a LanLabs — Activa tu agente IA',
      body,
    }),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Email API ${res.status}: ${text}`)
  }
}

async function createClerkUser(email: string, password: string, clienteId: string, nombre: string): Promise<void> {
  const clerk = await clerkClient()

  // Create user in Clerk with the temporary password
  let clerkUserId: string
  try {
    const parts = nombre.trim().split(' ')
    const createdUser = await clerk.users.createUser({
      emailAddress: [email],
      password,
      firstName: parts[0],
      lastName: parts.slice(1).join(' ') || undefined,
    })
    clerkUserId = createdUser.id
  } catch (err: unknown) {
    const clerkErr = err as { errors?: Array<{ message: string }> }
    throw new Error(`Clerk user creation failed: ${clerkErr?.errors?.[0]?.message ?? 'Unknown error'}`)
  }

  // Create record in usuarios table so JWT gets rol + cliente_id
  const { error: usuarioError } = await supabase.from('usuarios').insert({
    id: randomUUID(),
    cliente_id: clienteId,
    email,
    password_hash: 'managed_by_clerk',
    rol: 'admin',
    nombre_completo: nombre,
    activo: true,
    must_change_password: true,
  })

  if (usuarioError) {
    // Clean up Clerk user to keep state consistent
    await clerk.users.deleteUser(clerkUserId).catch(() => {})
    throw new Error(`Usuario record creation failed: ${usuarioError.message}`)
  }
}

interface CreateClienteRequest {
  nombre: string
  email: string
  telefono: string
  whatsapp_dueño?: string
  industria?: string
  website?: string
  plan: 'basico' | 'profesional' | 'empresarial'
  nombreAgente: string
  tono: string
  idioma: string
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

const PLAN_PRICES: Record<string, number> = {
  basico: 149,
  profesional: 249,
  empresarial: 399,
}

export async function POST(request: Request): Promise<Response> {
  const role = await getUserRole()
  if (role !== 'super_admin') {
    return Response.json({ success: false, error: 'Unauthorized' } as ApiResponse, { status: 403 })
  }

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
      whatsapp_dueño: body.whatsapp_dueño,
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

    // 6. Create trialing subscription so the bot works until first billing cycle
    const { error: subError } = await supabase.from('subscription').insert({
      cliente_id: clienteId,
      status: 'trialing',
      monthly_amount: PLAN_PRICES[plan] ?? 0,
    })
    if (subError) {
      throw new Error(`Error creating subscription: ${subError.message}`)
    }

    // Generate a temporary password for the client
    const tempPassword = randomBytes(6).toString('hex')

    // Create Clerk user + usuarios record so the client can log in
    await createClerkUser(body.email, tempPassword, clienteId, body.nombre)

    // Send welcome email (fire-and-forget — don't fail the request if email fails)
    sendWelcomeEmail({
      nombre: body.nombre,
      email: body.email,
      password: tempPassword,
    }).catch((err) => console.error('Welcome email failed:', err))

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
