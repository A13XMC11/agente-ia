import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { requireRole } from '@/lib/server-auth'

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const user = await requireRole('super_admin')

  // Ensure super_admin role is enforced
  if (user.role !== 'super_admin') {
    throw new Error('Unauthorized: only super_admin can access this page')
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar role="super_admin" />

      <div className="flex-1 flex flex-col lg:ml-60">
        <Header title="Admin Dashboard" userName={user.email} />

        <main className="flex-1 overflow-auto pt-16">
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
