import { NextResponse, NextRequest } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { createServerClient } from '@/lib/supabase/server'
import { clerkClient } from '@clerk/nextjs/server'

type RouteContext = { params: Promise<{ id: string }> }

const CHILD_TABLES = [
  'campaign_recipients',
  'campanas',
  'comprobantes_procesados',
  'pagos',
  'citas',
  'alertas',
  'datos_bancarios',
  'modulos_activos',
  'leads',
  'mensajes',
  'conversaciones',
  'canales_config',
  'agentes',
  'usage_logs',
  'subscription',
  'usuarios',
]

export async function DELETE(req: NextRequest, { params }: RouteContext) {
  try {
    const session = await getServerSession()
    if (!session || session.role !== 'super_admin') {
      return NextResponse.json({ success: false, error: 'No autorizado' }, { status: 401 })
    }

    const { id: clienteId } = await params

    const supabase = createServerClient()

    // Fetch client first to get email for Clerk lookup and confirm it exists
    const { data: cliente, error: fetchError } = await supabase
      .from('clientes')
      .select('id, nombre, email')
      .eq('id', clienteId)
      .maybeSingle()

    if (fetchError) {
      return NextResponse.json({ success: false, error: 'Error al buscar el cliente' }, { status: 500 })
    }

    if (!cliente) {
      return NextResponse.json({ success: false, error: 'Cliente no encontrado' }, { status: 404 })
    }

    // Validate confirmation token from request body
    const body = await req.json().catch(() => ({}))
    if (!body.confirmacion || body.confirmacion !== cliente.nombre) {
      return NextResponse.json(
        { success: false, error: 'Confirmación incorrecta. Escribe exactamente el nombre del cliente.' },
        { status: 422 },
      )
    }

    const errors: string[] = []

    // campaign_recipients needs a join since it references campanas.id, not cliente_id directly
    const { data: campanas } = await supabase
      .from('campanas')
      .select('id')
      .eq('cliente_id', clienteId)

    if (campanas && campanas.length > 0) {
      const campanaIds = campanas.map((c: { id: string }) => c.id)
      const { error } = await supabase
        .from('campaign_recipients')
        .delete()
        .in('campana_id', campanaIds)
      if (error) errors.push(`campaign_recipients: ${error.message}`)
    }

    // mensajes references conversaciones, delete before conversaciones
    const { data: convs } = await supabase
      .from('conversaciones')
      .select('id')
      .eq('cliente_id', clienteId)

    if (convs && convs.length > 0) {
      const convIds = convs.map((c: { id: string }) => c.id)
      const { error } = await supabase
        .from('mensajes')
        .delete()
        .in('conversacion_id', convIds)
      if (error) errors.push(`mensajes: ${error.message}`)
    }

    // Delete remaining child tables by cliente_id
    const directTables = [
      'campanas',
      'comprobantes_procesados',
      'pagos',
      'citas',
      'alertas',
      'datos_bancarios',
      'modulos_activos',
      'leads',
      'conversaciones',
      'canales_config',
      'agentes',
      'usage_logs',
      'subscription',
    ]

    for (const table of directTables) {
      const { error } = await supabase.from(table).delete().eq('cliente_id', clienteId)
      if (error) errors.push(`${table}: ${error.message}`)
    }

    // Delete usuarios record (they have cliente_id FK)
    const { data: usuarios } = await supabase
      .from('usuarios')
      .select('email')
      .eq('cliente_id', clienteId)

    const { error: usuariosError } = await supabase
      .from('usuarios')
      .delete()
      .eq('cliente_id', clienteId)

    if (usuariosError) errors.push(`usuarios: ${usuariosError.message}`)

    // Delete Clerk users associated with this client
    if (usuarios && usuarios.length > 0) {
      const clerk = await clerkClient()
      for (const u of usuarios) {
        try {
          const clerkUsers = await clerk.users.getUserList({ emailAddress: [u.email] })
          for (const cu of clerkUsers.data) {
            await clerk.users.deleteUser(cu.id)
          }
        } catch (err) {
          errors.push(`clerk user ${u.email}: ${err instanceof Error ? err.message : 'unknown'}`)
        }
      }
    }

    // Finally delete the client record
    const { error: clienteError } = await supabase
      .from('clientes')
      .delete()
      .eq('id', clienteId)

    if (clienteError) {
      return NextResponse.json(
        { success: false, error: `Error al eliminar cliente: ${clienteError.message}`, partialErrors: errors },
        { status: 500 },
      )
    }

    return NextResponse.json({
      success: true,
      message: `Cliente "${cliente.nombre}" eliminado correctamente.`,
      ...(errors.length > 0 && { warnings: errors }),
    })
  } catch (err) {
    console.error('[DELETE CLIENTE]', err)
    return NextResponse.json(
      { success: false, error: 'Error inesperado al eliminar el cliente' },
      { status: 500 },
    )
  }
}
