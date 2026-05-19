'use client'

import { Avatar } from '@/components/ui/avatar'
import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface HeaderProps {
  title: string
  userName?: string
  userEmail?: string
  onMenuClick?: () => void
}

export const Header = ({ title, userName = 'Usuario', userEmail, onMenuClick }: HeaderProps) => {
  const pathname = usePathname()

  const getTitleFromPath = () => {
    if (pathname === '/admin') return 'Dashboard'
    if (pathname === '/admin/clientes') return 'Clientes'
    if (pathname === '/admin/clientes/nuevo') return 'Nuevo Cliente'
    if (pathname === '/cliente') return 'Dashboard'
    if (pathname === '/cliente/conversaciones') return 'Conversaciones'
    if (pathname === '/cliente/leads') return 'Leads'
    if (pathname === '/cliente/citas') return 'Citas'
    if (pathname === '/cliente/pagos') return 'Pagos'
    if (pathname === '/cliente/configuracion') return 'Configuración'
    return title
  }

  return (
    <header className="fixed left-0 right-0 top-0 z-30 h-16 border-b border-border bg-background flex items-center justify-between px-4 md:pl-64 md:pr-6">
      <div className="flex items-center gap-3">
        {/* Hamburger — visible only on mobile */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden shrink-0"
          onClick={onMenuClick}
          aria-label="Abrir menú"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <h1 className="text-lg md:text-xl font-semibold text-text-primary truncate">
          {getTitleFromPath()}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:block text-right text-sm">
          <p className="text-text-primary font-medium leading-tight">{userName}</p>
          {userEmail && <p className="text-text-secondary text-xs">{userEmail}</p>}
        </div>
        <Avatar name={userName} className="bg-surface text-text-primary" />
      </div>
    </header>
  )
}
