import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import Link from 'next/link'

export default function NuevoClientePage() {
  return (
    <div className="space-y-6">
      <div>
        <Link href="/admin/clientes" className="text-accent hover:text-accent-hover mb-2 inline-block">
          ← Volver
        </Link>
        <h1 className="text-3xl font-bold text-text-primary">Nuevo Cliente</h1>
        <p className="text-text-secondary mt-2">Crea un nuevo cliente y configura su agente IA</p>
      </div>

      {/* Client Data */}
      <Card>
        <CardHeader>
          <CardTitle>Información del Cliente</CardTitle>
          <CardDescription>Datos básicos del cliente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="client-name">Nombre del Negocio</Label>
              <Input id="client-name" placeholder="Ej: Mi Tienda Online" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-email">Email</Label>
              <Input id="client-email" type="email" placeholder="admin@mitiendo.com" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-phone">Teléfono</Label>
              <Input id="client-phone" placeholder="+57 300 1234567" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-plan">Plan</Label>
              <Select id="client-plan">
                <option>Starter - $99/mes</option>
                <option>Professional - $299/mes</option>
                <option>Enterprise - Consultar</option>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Agent Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuración del Agente</CardTitle>
          <CardDescription>Personaliza el comportamiento inicial del agente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Nombre del Agente</Label>
              <Input id="agent-name" placeholder="Asistente Virtual" />
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
              <Label htmlFor="model">Modelo IA</Label>
              <Select id="model">
                <option>GPT-4o</option>
                <option>GPT-4 Turbo</option>
                <option>GPT-3.5 Turbo</option>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="system-prompt">System Prompt</Label>
            <Textarea
              id="system-prompt"
              placeholder="Eres un asistente amable que ayuda a los clientes con sus preguntas..."
              className="min-h-32"
            />
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Modules */}
      <Card>
        <CardHeader>
          <CardTitle>Módulos a Activar</CardTitle>
          <CardDescription>Selecciona qué funcionalidades estará disponible para este cliente</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { name: 'Ventas', desc: 'Catálogo, cotizaciones, objecciones' },
              { name: 'Agendamiento', desc: 'Integración Google Calendar' },
              { name: 'Cobros', desc: 'Verificación de pagos con IA Vision' },
              { name: 'Links de Pago', desc: 'Stripe, MercadoPago, PayPal' },
              { name: 'Calificación', desc: 'Scoring automático de leads' },
              { name: 'Campañas', desc: 'Mensajería masiva' },
              { name: 'Analytics', desc: 'Reportes y métricas' },
              { name: 'Alertas', desc: 'Notificaciones del sistema' },
            ].map((module) => (
              <div key={module.name} className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">{module.name}</Label>
                  <p className="text-sm text-text-secondary">{module.desc}</p>
                </div>
                <Switch />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Channels */}
      <Card>
        <CardHeader>
          <CardTitle>Canales</CardTitle>
          <CardDescription>Configura los canales de comunicación</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">WhatsApp</Label>
              <Switch checked={true} />
            </div>

            <div className="space-y-2 pl-4">
              <div className="space-y-2">
                <Label htmlFor="whatsapp-phone">Phone Number ID</Label>
                <Input id="whatsapp-phone" placeholder="123456789012345" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="whatsapp-token">Token</Label>
                <Input id="whatsapp-token" placeholder="EABC..." />
              </div>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Instagram</Label>
              <Switch />
            </div>

            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Facebook</Label>
              <Switch />
            </div>

            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Email</Label>
              <Switch />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button>Crear Cliente</Button>
        <Link href="/admin/clientes">
          <Button variant="outline">Cancelar</Button>
        </Link>
      </div>
    </div>
  )
}
