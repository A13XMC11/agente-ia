import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TrendingUp } from 'lucide-react'

export default function LeadsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Leads</h1>
        <p className="text-text-secondary mt-2">Calificación automática de leads con inteligencia artificial</p>
      </div>

      <div className="flex gap-2">
        <Input placeholder="Buscar lead..." className="flex-1" />
        <Button variant="outline">Filtrar por score</Button>
        <Button variant="outline">Filtrar por estado</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Leads Calificados</CardTitle>
          <CardDescription>Ordenados por score de calificación</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12">
            <TrendingUp className="h-12 w-12 text-text-muted mb-4" />
            <p className="text-text-secondary">No hay leads aún</p>
            <p className="text-sm text-text-muted mt-2">Los leads se mostrarán aquí conforme tu agente califique contactos</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
