'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Link from 'next/link'
import { Users } from 'lucide-react'
import { useState, useEffect } from 'react'
import type { Cliente } from '@/lib/data/clientes-server'

interface ApiResponse {
  success: boolean
  data?: Cliente[]
  error?: string
}

const PLAN_PRECIOS: Record<string, number> = {
  basico: 149,
  profesional: 249,
  empresarial: 399,
}

const PLAN_LABELS: Record<string, string> = {
  basico: 'Plan Básico',
  profesional: 'Plan Profesional',
  empresarial: 'Plan Empresarial',
}

function formatPlan(plan: string): string {
  const label = PLAN_LABELS[plan.toLowerCase()] ?? plan
  const precio = PLAN_PRECIOS[plan.toLowerCase()]
  return precio ? `${label} - $${precio}/mes` : label
}

export default function ClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [filteredClientes, setFilteredClientes] = useState<Cliente[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadClientes = async () => {
      setLoading(true)
      try {
        const response = await fetch('/api/clientes')
        const data: ApiResponse = await response.json()
        const clientesList = data.data || []
        setClientes(clientesList)
        setFilteredClientes(clientesList)
      } catch (error) {
        console.error('Error loading clientes:', error)
      } finally {
        setLoading(false)
      }
    }

    loadClientes()
  }, [])

  useEffect(() => {
    const handleSearch = async () => {
      if (!searchQuery.trim()) {
        setFilteredClientes(clientes)
        return
      }

      try {
        const response = await fetch(`/api/clientes/search?q=${encodeURIComponent(searchQuery)}`)
        const data: ApiResponse = await response.json()
        setFilteredClientes(data.data || [])
      } catch (error) {
        console.error('Error searching clientes:', error)
      }
    }

    handleSearch()
  }, [searchQuery, clientes])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-EC', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  }

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
        <Input
          placeholder="Buscar cliente por nombre o email..."
          className="flex-1"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Clientes</CardTitle>
          <CardDescription>
            {filteredClientes.length} cliente{filteredClientes.length !== 1 ? 's' : ''} encontrado
            {filteredClientes.length !== 1 ? 's' : ''}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <p className="text-text-secondary">Cargando clientes...</p>
            </div>
          ) : filteredClientes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Users className="h-12 w-12 text-text-muted mb-4" />
              <p className="text-text-secondary">
                {searchQuery ? 'No se encontraron clientes' : 'No hay clientes aún'}
              </p>
              <p className="text-sm text-text-muted mt-2">
                {searchQuery ? 'Intenta con otros términos de búsqueda' : 'Crea tu primer cliente para empezar'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Nombre</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Email</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Industria</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Plan</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Estado</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Creado</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredClientes.map((cliente) => (
                    <tr key={cliente.id} className="border-b hover:bg-surface cursor-pointer">
                      <td className="py-3 px-4 text-text-primary font-medium">
                        <Link href={`/admin/clientes/${cliente.id}`}>
                          {cliente.nombre}
                        </Link>
                      </td>
                      <td className="py-3 px-4 text-text-secondary text-sm">{cliente.email}</td>
                      <td className="py-3 px-4 text-text-secondary text-sm capitalize">
                        {cliente.industria || <span className="text-text-muted">-</span>}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        <span className="text-text-primary font-medium">{formatPlan(cliente.plan)}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            cliente.estado === 'activo'
                              ? 'bg-success/10 text-success'
                              : cliente.estado === 'pausado'
                                ? 'bg-warning/10 text-warning'
                                : 'bg-error/10 text-error'
                          }`}
                        >
                          {cliente.estado}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-text-secondary text-sm">{formatDate(cliente.created_at)}</td>
                      <td className="py-3 px-4">
                        <Link href={`/admin/clientes/${cliente.id}`}>
                          <Button variant="outline" size="sm">Ver</Button>
                        </Link>
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
