'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Calendar } from 'lucide-react'
import { useState, useEffect } from 'react'

interface Cita {
  id: string
  usuario_nombre: string
  usuario_email: string
  fecha: string
  hora: string
  duracion_minutos: number
  estado: 'confirmada' | 'pendiente' | 'cancelada' | 'completada'
  descripcion: string
}

export default function CitasPage() {
  const [citas, setCitas] = useState<Cita[]>([])
  const [loading, setLoading] = useState(true)
  const [currentMonth, setCurrentMonth] = useState(new Date())

  useEffect(() => {
    loadCitas()
  }, [currentMonth])

  async function loadCitas() {
    try {
      const monthStart = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1)
      const monthEnd = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0)

      const response = await fetch(
        `/api/cliente/citas?start=${monthStart.toISOString().split('T')[0]}&end=${monthEnd.toISOString().split('T')[0]}`
      )
      if (!response.ok) throw new Error('Failed to load')
      const data = await response.json()
      setCitas(data.data || [])
    } catch (error) {
      console.error('Error loading citas:', error)
    } finally {
      setLoading(false)
    }
  }

  const proximasCitas = citas
    .filter(c => new Date(c.fecha) >= new Date())
    .sort((a, b) => new Date(a.fecha).getTime() - new Date(b.fecha).getTime())
    .slice(0, 10)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO', {
      weekday: 'long',
      day: 'numeric',
      month: 'long'
    })
  }

  const getEstadoBg = (estado: string) => {
    switch (estado) {
      case 'confirmada':
        return 'bg-success/10 text-success'
      case 'pendiente':
        return 'bg-warning/10 text-warning'
      case 'completada':
        return 'bg-info/10 text-info'
      default:
        return 'bg-error/10 text-error'
    }
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  const goToday = () => {
    setCurrentMonth(new Date())
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Citas</h1>
        <p className="text-text-secondary mt-2">Calendario integrado con Google Calendar</p>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={prevMonth}>
          ← Anterior
        </Button>
        <Button variant="outline" onClick={goToday}>
          Hoy
        </Button>
        <Button variant="outline" onClick={nextMonth}>
          Siguiente →
        </Button>
        <span className="px-4 py-2 text-text-primary font-medium">
          {currentMonth.toLocaleDateString('es-CO', { month: 'long', year: 'numeric' })}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Todas las Citas</CardTitle>
              <CardDescription>{citas.length} citas en este mes</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-12">
                  <p className="text-text-secondary">Cargando citas...</p>
                </div>
              ) : citas.length === 0 ? (
                <div className="flex items-center justify-center py-32 bg-border/20 rounded-lg">
                  <p className="text-text-secondary">No hay citas en este mes</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {citas.map((cita) => (
                    <div key={cita.id} className="p-4 border rounded-lg hover:bg-surface">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-medium text-text-primary">{cita.usuario_nombre}</p>
                          <p className="text-sm text-text-secondary">{cita.descripcion}</p>
                          <p className="text-xs text-text-muted mt-1">
                            {formatDate(cita.fecha)} a las {cita.hora} ({cita.duracion_minutos} min)
                          </p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getEstadoBg(cita.estado)} capitalize`}>
                          {cita.estado}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
              {proximasCitas.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Calendar className="h-12 w-12 text-text-muted mb-4" />
                  <p className="text-text-secondary text-sm">No hay citas próximas</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {proximasCitas.map((cita) => (
                    <div key={cita.id} className="p-3 bg-surface rounded-lg">
                      <p className="font-medium text-text-primary text-sm">{cita.usuario_nombre}</p>
                      <p className="text-xs text-text-muted">{formatDate(cita.fecha)} {cita.hora}</p>
                      <span className={`text-xs font-medium mt-2 inline-block px-2 py-1 rounded ${getEstadoBg(cita.estado)}`}>
                        {cita.estado}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
