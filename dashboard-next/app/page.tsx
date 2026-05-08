import { getServerSession } from '@/lib/server-auth'
import { redirect } from 'next/navigation'

export default async function Home() {
  const session = await getServerSession()

  if (!session) {
    redirect('/login')
  }

  if (session.role === 'super_admin') {
    redirect('/admin')
  }

  redirect('/cliente')
}
