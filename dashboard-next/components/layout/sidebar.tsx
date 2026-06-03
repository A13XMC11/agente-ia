'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useClerk } from '@clerk/nextjs'
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  TrendingUp,
  Calendar,
  Settings,
  LogOut,
  CreditCard,
  Bot,
  BarChart2,
  Receipt,
  Megaphone,
  ShoppingBag,
} from 'lucide-react'

interface SidebarProps {
  role: 'super_admin' | 'admin' | 'operador'
  clienteName?: string
  isOpen: boolean
  onClose: () => void
}

export const Sidebar = ({ role, clienteName, isOpen, onClose }: SidebarProps) => {
  const pathname = usePathname()
  const isAdmin = role === 'super_admin'
  const { signOut } = useClerk()

  const handleSignOut = () => {
    signOut()
  }

  const adminLinks = [
    { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/admin/clientes', label: 'Clientes', icon: Users },
  ]

  const clientLinks = [
    { href: '/cliente', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/cliente/conversaciones', label: 'Conversaciones', icon: MessageSquare },
    { href: '/cliente/leads', label: 'Leads', icon: TrendingUp },
    { href: '/cliente/citas', label: 'Citas', icon: Calendar },
    { href: '/cliente/pagos', label: 'Pagos', icon: CreditCard },
    { href: '/cliente/billing', label: 'Facturación', icon: Receipt },
    { href: '/cliente/catalogo', label: 'Catálogo', icon: ShoppingBag },
    { href: '/cliente/campanas', label: 'Campañas', icon: Megaphone },
    { href: '/cliente/analytics', label: 'Analytics', icon: BarChart2 },
    { href: '/cliente/configuracion', label: 'Configuración', icon: Settings },
  ]

  const links = isAdmin ? adminLinks : clientLinks

  return (
    <>
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen w-60 transition-transform duration-300',
          'border-r border-border glass',
          'md:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="px-5 py-4 h-16 flex items-center gap-3 border-b border-border">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/10 ring-1 ring-accent/20">
              <Bot className="h-4 w-4 text-accent" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-text-primary leading-none truncate">
                {isAdmin ? 'Agente IA' : (clienteName || 'Dashboard')}
              </p>
              <p className="text-xs text-text-muted mt-0.5">
                {isAdmin ? 'Super Admin' : 'Panel de control'}
              </p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
            {links.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href
              return (
                <Link key={href} href={href} onClick={onClose}>
                  <span
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm cursor-pointer',
                      'transition-all duration-150 relative group',
                      isActive
                        ? 'bg-accent/10 text-accent font-medium'
                        : 'text-text-secondary hover:bg-surface/60 hover:text-text-primary',
                    )}
                  >
                    {/* Active left border */}
                    {isActive && (
                      <span className="absolute left-0 inset-y-1 w-0.5 rounded-r-full bg-accent" />
                    )}
                    <Icon
                      className={cn(
                        'h-4 w-4 shrink-0 transition-colors duration-150',
                        isActive ? 'text-accent' : 'text-text-muted group-hover:text-text-secondary',
                      )}
                    />
                    <span>{label}</span>
                  </span>
                </Link>
              )
            })}
          </nav>

          {/* Logout */}
          <div className="border-t border-border p-3">
            <button
              onClick={handleSignOut}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm cursor-pointer',
                'text-text-muted hover:text-error hover:bg-error/8',
                'transition-all duration-150',
                'active:scale-[0.97]',
              )}
            >
              <LogOut className="h-4 w-4 shrink-0" />
              <span>Cerrar sesión</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}
    </>
  )
}
