import { getClientes } from '@/lib/data/clientes-server'
import { requireRole } from '@/lib/server-auth'
import { ClientesView } from './_components/clientes-view'

export const dynamic = 'force-dynamic'

export default async function ClientesPage() {
  await requireRole('super_admin')
  const clientes = await getClientes()
  return <ClientesView clientes={clientes} />
}
