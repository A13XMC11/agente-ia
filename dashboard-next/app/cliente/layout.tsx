import { LayoutClient } from '@/components/layout/layout-client'
import { requireAuth } from '@/lib/server-auth'
import { redirect } from 'next/navigation'

export default async function ClienteLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const user = await requireAuth()

  if (user.role === 'super_admin') {
    redirect('/admin')
  }

  if (user.role !== 'admin' && user.role !== 'operador' && user.role !== 'cliente') {
    redirect('/login')
  }

  return (
    <LayoutClient
      role={user.role as 'admin' | 'operador'}
      clienteName="Mi Negocio"
      userName={user.email}
    >
      {children}
    </LayoutClient>
  )
}
