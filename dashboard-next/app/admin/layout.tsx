import { LayoutClient } from '@/components/layout/layout-client'
import { requireRole } from '@/lib/server-auth'

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const user = await requireRole('super_admin')

  if (user.role !== 'super_admin') {
    throw new Error('Unauthorized: only super_admin can access this page')
  }

  return (
    <LayoutClient role="super_admin" userName={user.email}>
      {children}
    </LayoutClient>
  )
}
