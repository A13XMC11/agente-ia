import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date): string {
  return new Date(date).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
  }).format(amount)
}

export function getScoreBadgeColor(score: number): string {
  if (score >= 8) return 'bg-green-900 text-green-200'
  if (score >= 5) return 'bg-yellow-900 text-yellow-200'
  return 'bg-red-900 text-red-200'
}

export function getStatusBadgeColor(status: string): string {
  const colors: Record<string, string> = {
    activo: 'bg-green-900 text-green-200',
    activa: 'bg-green-900 text-green-200',
    pausado: 'bg-yellow-900 text-yellow-200',
    pausada: 'bg-yellow-900 text-yellow-200',
    cancelado: 'bg-red-900 text-red-200',
    cerrada: 'bg-red-900 text-red-200',
    confirmada: 'bg-blue-900 text-blue-200',
    pendiente: 'bg-yellow-900 text-yellow-200',
    completada: 'bg-green-900 text-green-200',
  }
  return colors[status] || 'bg-gray-900 text-gray-200'
}
