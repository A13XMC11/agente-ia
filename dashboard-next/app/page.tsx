import { getServerSession } from '@/lib/server-auth'
import { redirect } from 'next/navigation'

export default async function Home() {
  const session = await getServerSession()

  if (!session) {
    redirect('/login')
  }

  // Route based on role
  if (session.role === 'super_admin') {
    redirect('/admin')
  } else if (session.role === 'admin' || session.role === 'operador' || session.role === 'cliente') {
    redirect('/cliente')
  }

  // Default: send to login if role is not recognized
  redirect('/login')
}
