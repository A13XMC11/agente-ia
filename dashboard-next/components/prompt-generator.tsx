'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Sparkles, X, RefreshCw, Check } from 'lucide-react'

const MODULE_LABELS: Record<string, string> = {
  ventas: 'Ventas',
  agendamiento: 'Agendamiento',
  cobros: 'Cobros',
  links_pago: 'Links de Pago',
  calificacion: 'Calificación',
  campanas: 'Campañas',
  analytics: 'Analytics',
  alertas: 'Alertas',
  seguimientos: 'Seguimientos',
}

interface PromptGeneratorProps {
  agenteName: string
  tono: string
  idioma: string
  modulosActivos: string[]
  onApply: (prompt: string) => void
}

interface FormState {
  empresa: string
  industria: string
  descripcion: string
  servicios: string
  publico_objetivo: string
  reglas_especiales: string
}

export function PromptGenerator({ agenteName, tono, idioma, modulosActivos, onApply }: PromptGeneratorProps) {
  const [open, setOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState('')
  const [form, setForm] = useState<FormState>({
    empresa: '',
    industria: '',
    descripcion: '',
    servicios: '',
    publico_objetivo: '',
    reglas_especiales: '',
  })

  const canGenerate = form.empresa.trim() && form.industria.trim() && form.descripcion.trim() && form.servicios.trim()

  async function handleGenerate() {
    setGenerating(true)
    try {
      const res = await fetch('/api/generate-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre_agente: agenteName,
          tono,
          idioma,
          modulos: modulosActivos,
          ...form,
        }),
      })
      const data = await res.json() as { success: boolean; prompt?: string; error?: string }
      if (res.ok && data.success) {
        setGenerated(data.prompt ?? '')
      } else {
        alert(data.error ?? 'Error al generar el prompt')
      }
    } catch {
      alert('Error de red')
    } finally {
      setGenerating(false)
    }
  }

  function handleApply() {
    onApply(generated)
    setOpen(false)
    setGenerated('')
  }

  function handleClose() {
    if (generating) return
    setOpen(false)
    setGenerated('')
  }

  function updateForm(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-1.5 text-accent border-accent/30 hover:bg-accent/10"
      >
        <Sparkles className="h-3.5 w-3.5" />
        Generar con IA
      </Button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) handleClose() }}
        >
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-[#060D13] p-6 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/15">
                  <Sparkles className="h-4 w-4 text-accent" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">Generador de Prompt</h2>
                  <p className="text-xs text-text-secondary">
                    Para {agenteName} · {tono} · {idioma}
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                disabled={generating}
                className="text-text-muted hover:text-text-primary disabled:opacity-40"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Form step */}
            {!generated && (
              <div className="space-y-4">
                <p className="text-sm text-text-secondary">
                  Completa la información del negocio y la IA generará un system prompt optimizado para {agenteName}.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label>Nombre de la empresa *</Label>
                    <Input
                      value={form.empresa}
                      onChange={(e) => updateForm('empresa', e.target.value)}
                      placeholder="ej: TiendaMax Ecuador"
                      disabled={generating}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Industria / Sector *</Label>
                    <Input
                      value={form.industria}
                      onChange={(e) => updateForm('industria', e.target.value)}
                      placeholder="ej: Venta de ropa, Restaurante, SaaS..."
                      disabled={generating}
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label>Descripción del negocio *</Label>
                  <Textarea
                    value={form.descripcion}
                    onChange={(e) => updateForm('descripcion', e.target.value)}
                    placeholder="ej: Somos una tienda de ropa online con envíos a todo Ecuador, especializada en moda femenina..."
                    className="min-h-20"
                    disabled={generating}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>Productos / Servicios *</Label>
                  <Textarea
                    value={form.servicios}
                    onChange={(e) => updateForm('servicios', e.target.value)}
                    placeholder="ej: Vestidos $25-80, Blusas $15-40. Envío gratis sobre $50. Aceptamos tarjeta y transferencia..."
                    className="min-h-24"
                    disabled={generating}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>
                    Público objetivo{' '}
                    <span className="text-text-muted font-normal">(opcional)</span>
                  </Label>
                  <Input
                    value={form.publico_objetivo}
                    onChange={(e) => updateForm('publico_objetivo', e.target.value)}
                    placeholder="ej: Mujeres 18-45 años en Ecuador"
                    disabled={generating}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>
                    Reglas especiales{' '}
                    <span className="text-text-muted font-normal">(opcional)</span>
                  </Label>
                  <Textarea
                    value={form.reglas_especiales}
                    onChange={(e) => updateForm('reglas_especiales', e.target.value)}
                    placeholder="ej: No dar precios sin preguntar talla. Siempre ofrecer envío express. No mencionar a competidores..."
                    className="min-h-20"
                    disabled={generating}
                  />
                </div>

                {modulosActivos.length > 0 && (
                  <div className="rounded-lg bg-surface border border-border p-3">
                    <p className="text-xs text-text-secondary mb-2">
                      Módulos activos que se incluirán en el prompt:
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {modulosActivos.map((m) => (
                        <span
                          key={m}
                          className="text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20"
                        >
                          {MODULE_LABELS[m] ?? m}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={handleGenerate}
                    disabled={generating || !canGenerate}
                    className="gap-1.5"
                  >
                    {generating ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        Generando...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        Generar Prompt
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={handleClose} disabled={generating}>
                    Cancelar
                  </Button>
                </div>
              </div>
            )}

            {/* Result step */}
            {generated && (
              <div className="space-y-4">
                <div className="rounded-lg bg-success/10 border border-success/20 px-4 py-3 flex items-center gap-2">
                  <Check className="h-4 w-4 text-success shrink-0" />
                  <p className="text-sm text-success">
                    Prompt generado. Puedes editarlo antes de aplicarlo.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <Label>Prompt generado</Label>
                  <Textarea
                    value={generated}
                    onChange={(e) => setGenerated(e.target.value)}
                    className="min-h-72 font-mono text-xs"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button onClick={handleApply} className="gap-1.5">
                    <Check className="h-4 w-4" />
                    Aplicar
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleGenerate}
                    disabled={generating}
                    className="gap-1.5"
                  >
                    {generating ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        Regenerando...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4" />
                        Regenerar
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={handleClose}>
                    Cancelar
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
