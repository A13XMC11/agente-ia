import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { requireAuth } from '@/lib/server-auth'
import { redirect } from 'next/navigation'

export default async function ClienteLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const user = await requireAuth()

  // Only super_admin should access /admin, not /cliente
  if (user.role === 'super_admin') {
    redirect('/admin')
  }

  // Both admin, operador, and cliente can access /cliente
  if (user.role !== 'admin' && user.role !== 'operador' && user.role !== 'cliente') {
    redirect('/login')
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar role={user.role as 'admin' | 'operador'} clienteName="Mi Negocio" />

      <div className="flex-1 flex flex-col lg:ml-60">
        <Header title="Dashboard" userName={user.email} />

        <main className="flex-1 overflow-auto pt-16">
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
