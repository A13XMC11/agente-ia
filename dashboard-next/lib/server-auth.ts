import { jwtVerify } from 'jose'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { createClient } from '@supabase/supabase-js'
import type { User } from '@/types'

const secretKey = new TextEncoder().encode(
  process.env.JWT_SECRET || 'your-secret-key-change-this-in-production',
)

function createServiceClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.SUPABASE_SERVICE_ROLE_KEY || '',
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    }
  )
}

export async function getServerSession(): Promise<(User & { cliente_id: string }) | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth-token')?.value

  if (!token) {
    console.log('[AUTH] No auth token found')
    return null
  }

  try {
    console.log('[AUTH] Verifying JWT token')
    const verified = await jwtVerify(token, secretKey)
    const user = verified.payload as unknown as User
    console.log('[AUTH] JWT verified, user:', { id: user.id, email: user.email, role: user.role, cliente_id: user.cliente_id })

    // Obtener cliente_id de la tabla usuarios si no está en el JWT
    if (!user.cliente_id) {
      console.log('[AUTH] cliente_id not in JWT, querying usuarios table')
      const supabase = createServiceClient()
      const { data, error } = await supabase
        .from('usuarios')
        .select('cliente_id')
        .eq('email', user.email)
        .single()

      if (error) {
        console.log('[AUTH] Error querying usuarios:', error)
      } else {
        console.log('[AUTH] Usuarios query result:', data)
        if (data?.cliente_id) {
          user.cliente_id = data.cliente_id
        }
      }
    }

    if (!user.cliente_id) {
      console.log('[AUTH] No cliente_id found, returning null')
      return null
    }

    console.log('[AUTH] Session established with cliente_id:', user.cliente_id)
    return user as User & { cliente_id: string }
  } catch (error) {
    console.error('[AUTH] Exception during JWT verification:', error)
    return null
  }
}

export async function requireAuth(): Promise<User> {
  const session = await getServerSession()

  if (!session) {
    redirect('/login')
  }

  return session
}

export async function requireRole(role: 'super_admin' | 'admin' | 'operador'): Promise<User> {
  const session = await requireAuth()

  if (session.role !== role) {
    redirect('/')
  }

  return session
}
