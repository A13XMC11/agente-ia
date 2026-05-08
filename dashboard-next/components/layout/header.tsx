'use client'

import { Avatar } from '@/components/ui/avatar'
import { usePathname } from 'next/navigation'

interface HeaderProps {
  title: string
  userName?: string
  userEmail?: string
}

export const Header = ({ title, userName = 'Usuario', userEmail }: HeaderProps) => {
  const pathname = usePathname()

  const getTitleFromPath = () => {
    if (pathname === '/admin') return 'Dashboard'
    if (pathname === '/admin/clientes') return 'Clientes'
    if (pathname === '/admin/clientes/nuevo') return 'Nuevo Cliente'
    if (pathname === '/cliente') return 'Dashboard'
    if (pathname === '/cliente/conversaciones') return 'Conversaciones'
    if (pathname === '/cliente/leads') return 'Leads'
    if (pathname === '/cliente/citas') return 'Citas'
    if (pathname === '/cliente/configuracion') return 'Configuración'
    return title
  }

  return (
    <header className="fixed left-0 right-0 top-0 z-30 h-16 border-b border-border bg-card-bg flex items-center justify-between px-6 lg:pl-64">
      <h1 className="text-xl font-semibold text-text-primary">{getTitleFromPath()}</h1>

      <div className="flex items-center gap-4">
        <div className="hidden sm:block text-right text-sm">
          <p className="text-text-primary font-medium">{userName}</p>
          {userEmail && <p className="text-text-secondary text-xs">{userEmail}</p>}
        </div>
        <Avatar name={userName} />
      </div>
    </header>
  )
}
