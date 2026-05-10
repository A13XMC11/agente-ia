'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TrendingUp } from 'lucide-react'
import { useState, useEffect } from 'react'

interface Lead {
  id: string
  nombre: string
  email: string
  telefono: string
  score: number
  estado: 'nuevo' | 'contactado' | 'interesado' | 'descalificado'
  created_at: string
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [filtrados, setFiltrados] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterScore, setFilterScore] = useState('todos')

  useEffect(() => {
    loadLeads()
  }, [])

  async function loadLeads() {
    try {
      const response = await fetch('/api/cliente/leads')
      if (!response.ok) throw new Error('Failed to load')
      const data = await response.json()
      setLeads(data.data || [])
      setFiltrados(data.data || [])
    } catch (error) {
      console.error('Error loading leads:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let resultado = leads

    if (search.trim()) {
      const query = search.toLowerCase()
      resultado = resultado.filter(l =>
        l.nombre.toLowerCase().includes(query) ||
        l.email.toLowerCase().includes(query) ||
        l.telefono.includes(query)
      )
    }

    if (filterScore !== 'todos') {
      const score = parseInt(filterScore)
      if (filterScore === 'alto') {
        resultado = resultado.filter(l => l.score >= 8)
      } else if (filterScore === 'medio') {
        resultado = resultado.filter(l => l.score >= 5 && l.score < 8)
      } else if (filterScore === 'bajo') {
        resultado = resultado.filter(l => l.score < 5)
      }
    }

    setFiltrados(resultado)
  }, [search, filterScore, leads])

  const getScoreBg = (score: number) => {
    if (score >= 8) return 'bg-success/10 text-success'
    if (score >= 5) return 'bg-warning/10 text-warning'
    return 'bg-error/10 text-error'
  }

  const getEstadoBg = (estado: string) => {
    switch (estado) {
      case 'interesado':
        return 'bg-success/10 text-success'
      case 'contactado':
        return 'bg-info/10 text-info'
      case 'descalificado':
        return 'bg-error/10 text-error'
      default:
        return 'bg-text-muted/10 text-text-muted'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Leads</h1>
        <p className="text-text-secondary mt-2">Calificación automática de leads con inteligencia artificial</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        <Input
          placeholder="Buscar por nombre, email o teléfono..."
          className="flex-1 min-w-64"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={filterScore}
          onChange={(e) => setFilterScore(e.target.value)}
          className="px-3 py-2 border rounded-lg bg-background text-text-primary"
        >
          <option value="todos">Todos los scores</option>
          <option value="alto">Score Alto (8+)</option>
          <option value="medio">Score Medio (5-7)</option>
          <option value="bajo">Score Bajo (&lt;5)</option>
        </select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Leads Calificados</CardTitle>
          <CardDescription>{filtrados.length} leads encontrados</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-text-secondary">Cargando leads...</p>
            </div>
          ) : filtrados.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <TrendingUp className="h-12 w-12 text-text-muted mb-4" />
              <p className="text-text-secondary">No hay leads</p>
              <p className="text-sm text-text-muted mt-2">Los leads se mostrarán aquí conforme tu agente califique contactos</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Nombre</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Email</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Teléfono</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Score</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map((lead) => (
                    <tr key={lead.id} className="border-b hover:bg-surface">
                      <td className="py-3 px-4 text-text-primary font-medium">{lead.nombre}</td>
                      <td className="py-3 px-4 text-text-secondary">{lead.email}</td>
                      <td className="py-3 px-4 text-text-secondary">{lead.telefono}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreBg(lead.score)}`}>
                          {lead.score}/10
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${getEstadoBg(lead.estado)}`}>
                          {lead.estado}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
