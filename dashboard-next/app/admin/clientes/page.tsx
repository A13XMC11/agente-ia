import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import { Users } from 'lucide-react'

export default function ClientesPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Clientes</h1>
          <p className="text-text-secondary mt-2">Gestiona todos los clientes de la plataforma</p>
        </div>
        <Link href="/admin/clientes/nuevo">
          <Button>Nuevo Cliente</Button>
        </Link>
      </div>

      <div className="flex gap-2">
        <Input placeholder="Buscar cliente por nombre o email..." className="flex-1" />
        <Button variant="outline">Filtrar</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Clientes</CardTitle>
          <CardDescription>Todos los clientes suscritos</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12">
            <Users className="h-12 w-12 text-text-muted mb-4" />
            <p className="text-text-secondary">No hay clientes aún</p>
            <p className="text-sm text-text-muted mt-2">Crea tu primer cliente para empezar</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
