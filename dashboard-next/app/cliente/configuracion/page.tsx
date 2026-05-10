'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useState, useEffect } from 'react'

interface Agente {
  id: string
  nombre: string
  tono: 'Amigable' | 'Formal' | 'Profesional'
  idioma: 'Español' | 'Inglés' | 'Portugués'
  modelo: 'GPT-4o' | 'GPT-4 Turbo' | 'GPT-3.5 Turbo'
  system_prompt: string
}

interface Modulo {
  id: string
  nombre: string
  descripcion: string
  activo: boolean
}

const MODULOS_DISPONIBLES = [
  { id: 'ventas', nombre: 'Ventas', descripcion: 'Catálogo, cotizaciones, objecciones' },
  { id: 'agendamiento', nombre: 'Agendamiento', descripcion: 'Integración Google Calendar' },
  { id: 'cobros', nombre: 'Cobros', descripcion: 'Verificación de pagos con IA Vision' },
  { id: 'links_pago', nombre: 'Links de Pago', descripcion: 'Stripe, MercadoPago, PayPal' },
  { id: 'calificacion', nombre: 'Calificación', descripcion: 'Scoring automático de leads' },
  { id: 'campanas', nombre: 'Campañas', descripcion: 'Mensajería masiva' },
  { id: 'analytics', nombre: 'Analytics', descripcion: 'Reportes y métricas' },
  { id: 'alertas', nombre: 'Alertas', descripcion: 'Notificaciones del sistema' }
]

export default function ConfiguracionPage() {
  const [agente, setAgente] = useState<Agente | null>(null)
  const [modulos, setModulos] = useState<Modulo[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [agenteRes, modulosRes] = await Promise.all([
        fetch('/api/cliente/agente'),
        fetch('/api/cliente/modulos')
      ])

      if (agenteRes.ok) {
        const agenteData = await agenteRes.json()
        setAgente(agenteData.data)
      }

      if (modulosRes.ok) {
        const modulosData = await modulosRes.json()
        setModulos(modulosData.data || [])
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveAgente() {
    if (!agente) return

    setSaving(true)
    try {
      const response = await fetch('/api/cliente/agente', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agente)
      })

      if (response.ok) {
        alert('Configuración del agente guardada exitosamente')
      } else {
        alert('Error al guardar la configuración')
      }
    } catch (error) {
      console.error('Error saving agente:', error)
      alert('Error al guardar la configuración')
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleModulo(moduloId: string, activo: boolean) {
    try {
      const response = await fetch('/api/cliente/modulos', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modulo_id: moduloId, activo })
      })

      if (response.ok) {
        setModulos(modulos.map(m =>
          m.id === moduloId ? { ...m, activo } : m
        ))
      }
    } catch (error) {
      console.error('Error toggling modulo:', error)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Configuración</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-text-secondary">Cargando configuración...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Configuración</h1>
        <p className="text-text-secondary mt-2">Personaliza tu agente IA y los módulos activos</p>
      </div>

      {agente && (
        <Card>
          <CardHeader>
            <CardTitle>Configuración del Agente</CardTitle>
            <CardDescription>Personaliza el comportamiento de tu agente IA</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Nombre del Agente</Label>
              <Input
                id="agent-name"
                value={agente.nombre}
                onChange={(e) => setAgente({ ...agente, nombre: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tone">Tono</Label>
                <select
                  id="tone"
                  value={agente.tono}
                  onChange={(e) => setAgente({ ...agente, tono: e.target.value as any })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>Amigable</option>
                  <option>Formal</option>
                  <option>Profesional</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="language">Idioma</Label>
                <select
                  id="language"
                  value={agente.idioma}
                  onChange={(e) => setAgente({ ...agente, idioma: e.target.value as any })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>Español</option>
                  <option>Inglés</option>
                  <option>Portugués</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">Modelo</Label>
                <select
                  id="model"
                  value={agente.modelo}
                  onChange={(e) => setAgente({ ...agente, modelo: e.target.value as any })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>GPT-4o</option>
                  <option>GPT-4 Turbo</option>
                  <option>GPT-3.5 Turbo</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="system-prompt">System Prompt</Label>
              <Textarea
                id="system-prompt"
                value={agente.system_prompt}
                onChange={(e) => setAgente({ ...agente, system_prompt: e.target.value })}
                className="min-h-40"
              />
            </div>

            <Button onClick={handleSaveAgente} disabled={saving}>
              {saving ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </CardContent>
        </Card>
      )}

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Módulos Activos</CardTitle>
          <CardDescription>Activa o desactiva funcionalidades para tu agente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {MODULOS_DISPONIBLES.map((modDef) => {
              const modActive = modulos.find(m => m.id === modDef.id)
              const activo = modActive?.activo || false

              return (
                <div key={modDef.id} className="flex items-center justify-between">
                  <div>
                    <Label className="text-base font-medium">{modDef.nombre}</Label>
                    <p className="text-sm text-text-secondary">{modDef.descripcion}</p>
                  </div>
                  <Switch
                    checked={activo}
                    onCheckedChange={(checked) => handleToggleModulo(modDef.id, checked)}
                  />
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
