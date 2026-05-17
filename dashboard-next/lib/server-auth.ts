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
    return null
  }

  try {
    const verified = await jwtVerify(token, secretKey)
    const user = verified.payload as unknown as User

    // Obtener cliente_id de la tabla usuarios si no está en el JWT
    if (!user.cliente_id) {
      const supabase = createServiceClient()
      const { data } = await supabase
        .from('usuarios')
        .select('cliente_id')
        .eq('email', user.email)
        .single()

      if (data?.cliente_id) {
        user.cliente_id = data.cliente_id
      }
    }

    if (!user.cliente_id) {
      return null
    }

    return user as User & { cliente_id: string }
  } catch {
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
