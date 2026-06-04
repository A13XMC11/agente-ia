'use client'

import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'

interface HeaderProps {
  title: string
  userName?: string
  userEmail?: string
  onMenuClick?: () => void
}

const PATH_LABELS: Record<string, string> = {
  '/admin': 'Dashboard',
  '/admin/clientes': 'Clientes',
  '/admin/clientes/nuevo': 'Nuevo Cliente',
  '/cliente': 'Dashboard',
  '/cliente/conversaciones': 'Conversaciones',
  '/cliente/leads': 'Leads',
  '/cliente/citas': 'Citas',
  '/cliente/pagos': 'Pagos',
  '/cliente/billing': 'Facturación',
  '/cliente/catalogo': 'Catálogo',
  '/cliente/campanas': 'Campañas',
  '/cliente/analytics': 'Analytics',
  '/cliente/configuracion': 'Configuración',
}

const PATH_PARENTS: Record<string, string> = {
  '/admin/clientes': 'Admin',
  '/admin/clientes/nuevo': 'Clientes',
  '/cliente/conversaciones': 'Inicio',
  '/cliente/leads': 'Inicio',
  '/cliente/citas': 'Inicio',
  '/cliente/pagos': 'Inicio',
  '/cliente/billing': 'Inicio',
  '/cliente/catalogo': 'Inicio',
  '/cliente/campanas': 'Inicio',
  '/cliente/analytics': 'Inicio',
  '/cliente/configuracion': 'Inicio',
}

export const Header = ({ title, onMenuClick }: HeaderProps) => {
  const pathname = usePathname()

  const normalizedPath = pathname.split('?')[0]
  const pageTitle = PATH_LABELS[normalizedPath] ?? title
  const parentTitle = PATH_PARENTS[normalizedPath]

  return (
    <header
      className={[
        'fixed left-0 right-0 top-0 z-30 h-16 min-w-0',
        'border-b border-border',
        'flex items-center gap-3 px-3 sm:px-4 md:pl-[calc(16rem+1.5rem)] md:pr-6',
      ].join(' ')}
      style={{
        background: 'rgba(6,13,19,0.85)',
        backdropFilter: 'blur(20px) saturate(160%)',
        WebkitBackdropFilter: 'blur(20px) saturate(160%)',
        boxShadow: 'inset 0 -1px 0 var(--border)',
      }}
    >
      {/* Mobile menu trigger */}
      <button
        className={[
          'md:hidden shrink-0 h-9 w-9 flex items-center justify-center rounded-lg',
          'text-text-secondary hover:text-text-primary hover:bg-surface',
          'transition-all duration-150 active:scale-[0.96] cursor-pointer',
        ].join(' ')}
        onClick={onMenuClick}
        aria-label="Abrir menú"
      >
        <Menu className="h-5 w-5" strokeWidth={1.75} />
      </button>

      {/* Breadcrumb + title */}
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {parentTitle && (
          <>
            <span className="text-[13px] text-text-muted font-medium hidden sm:block select-none">
              {parentTitle}
            </span>
            <span className="text-text-muted/40 text-sm hidden sm:block select-none">/</span>
          </>
        )}
        <h1 className="text-[13px] font-semibold text-text-primary tracking-tight truncate">
          {pageTitle}
        </h1>
      </div>
    </header>
  )
}
