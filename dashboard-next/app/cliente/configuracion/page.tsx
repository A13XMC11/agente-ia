import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'

export default function ConfiguracionPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Configuración</h1>
        <p className="text-text-secondary mt-2">Personaliza tu agente IA y los módulos activos</p>
      </div>

      {/* Agent Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuración del Agente</CardTitle>
          <CardDescription>Personaliza el comportamiento de tu agente IA</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="agent-name">Nombre del Agente</Label>
            <Input id="agent-name" placeholder="Mi Asistente" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tone">Tono</Label>
            <Select id="tone">
              <option>Amigable</option>
              <option>Formal</option>
              <option>Profesional</option>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="language">Idioma</Label>
            <Select id="language">
              <option>Español</option>
              <option>Inglés</option>
              <option>Portugués</option>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="system-prompt">System Prompt</Label>
            <Textarea
              id="system-prompt"
              placeholder="Instrucciones para el agente IA..."
              className="min-h-40"
            />
          </div>

          <Button>Guardar Cambios</Button>
        </CardContent>
      </Card>

      <Separator />

      {/* Modules */}
      <Card>
        <CardHeader>
          <CardTitle>Módulos Activos</CardTitle>
          <CardDescription>Activa o desactiva funcionalidades para tu agente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Ventas</Label>
                <p className="text-sm text-text-secondary">Catálogo, cotizaciones, objecciones</p>
              </div>
              <Switch checked={true} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Agendamiento</Label>
                <p className="text-sm text-text-secondary">Integración Google Calendar</p>
              </div>
              <Switch checked={true} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Cobros</Label>
                <p className="text-sm text-text-secondary">Verificación de pagos con IA Vision</p>
              </div>
              <Switch checked={false} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Links de Pago</Label>
                <p className="text-sm text-text-secondary">Stripe, MercadoPago, PayPal</p>
              </div>
              <Switch checked={false} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Calificación</Label>
                <p className="text-sm text-text-secondary">Scoring automático de leads</p>
              </div>
              <Switch checked={true} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Campañas</Label>
                <p className="text-sm text-text-secondary">Mensajería masiva</p>
              </div>
              <Switch checked={false} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Analytics</Label>
                <p className="text-sm text-text-secondary">Reportes y métricas</p>
              </div>
              <Switch checked={true} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Alertas</Label>
                <p className="text-sm text-text-secondary">Notificaciones del sistema</p>
              </div>
              <Switch checked={true} />
            </div>
          </div>

          <Button>Guardar Módulos</Button>
        </CardContent>
      </Card>
    </div>
  )
}
