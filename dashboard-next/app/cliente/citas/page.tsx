import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Calendar } from 'lucide-react'

export default function CitasPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Citas</h1>
        <p className="text-text-secondary mt-2">Calendario integrado con Google Calendar</p>
      </div>

      <div className="flex gap-2">
        <Button variant="outline">Mes Anterior</Button>
        <Button variant="outline">Hoy</Button>
        <Button variant="outline">Mes Siguiente</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Calendario</CardTitle>
              <CardDescription>Vista mensual de citas</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-32 bg-border/20 rounded-lg">
                <p className="text-text-secondary">Calendario aquí</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle>Próximas Citas</CardTitle>
              <CardDescription>Hoy y próximos días</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-12">
                <Calendar className="h-12 w-12 text-text-muted mb-4" />
                <p className="text-text-secondary text-sm">No hay citas programadas</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
