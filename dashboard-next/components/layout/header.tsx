'use client'

import { Avatar } from '@/components/ui/avatar'
import { useClerk } from '@clerk/nextjs'
import { LogOut, Menu } from 'lucide-react'
import { usePathname } from 'next/navigation'

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
  '/cliente/configuracion': 'Configuración',
}

export const Header = ({ title, userName = 'Usuario', userEmail, onMenuClick }: HeaderProps) => {
  const pathname = usePathname()
  const pageTitle = PATH_LABELS[pathname] ?? title
  const { signOut } = useClerk()

  const handleSignOut = async () => {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {})
    await signOut({ redirectUrl: '/sign-in' })
  }

  return (
    <header
      className={[
        'fixed left-0 right-0 top-0 z-30 h-16',
        'border-b border-border glass',
        'flex items-center justify-between px-4 md:pl-64 md:pr-6',
      ].join(' ')}
    >
      <div className="flex items-center gap-3">
        <button
          className={[
            'md:hidden shrink-0 h-9 w-9 flex items-center justify-center rounded-lg',
            'text-text-secondary hover:text-text-primary hover:bg-surface',
            'transition-all duration-150 active:scale-[0.97] cursor-pointer',
          ].join(' ')}
          onClick={onMenuClick}
          aria-label="Abrir menú"
        >
          <Menu className="h-5 w-5" />
        </button>

        <h1 className="text-base md:text-lg font-semibold text-text-primary tracking-tight">
          {pageTitle}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:block text-right">
          <p className="text-sm text-text-primary font-medium leading-none">{userName}</p>
          {userEmail && <p className="text-xs text-text-muted mt-0.5">{userEmail}</p>}
        </div>
        <Avatar name={userName} className="ring-1 ring-border-light" />
        <button
          onClick={handleSignOut}
          className={[
            'shrink-0 h-9 w-9 flex items-center justify-center rounded-lg',
            'text-text-secondary hover:text-red-400 hover:bg-surface',
            'transition-all duration-150 active:scale-[0.97] cursor-pointer',
          ].join(' ')}
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
