import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { requireRole } from '@/lib/server-auth'

export default async function ClienteLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const user = await requireRole('admin')

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
