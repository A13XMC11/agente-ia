'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  TrendingUp,
  Calendar,
  Settings,
  LogOut,
  CreditCard,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SidebarProps {
  role: 'super_admin' | 'admin' | 'operador'
  clienteName?: string
  isOpen: boolean
  onClose: () => void
}

export const Sidebar = ({ role, clienteName, isOpen, onClose }: SidebarProps) => {
  const pathname = usePathname()
  const isAdmin = role === 'super_admin'

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
    { href: '/cliente/configuracion', label: 'Configuración', icon: Settings },
  ]

  const links = isAdmin ? adminLinks : clientLinks

  return (
    <>
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen w-60 border-r border-border bg-card-bg transition-transform duration-300',
          'md:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Title */}
          <div className="border-b border-border px-6 py-4 h-16 flex items-center">
            <h1 className="text-lg font-bold text-accent">
              {isAdmin ? 'Agente IA' : clienteName || 'Dashboard'}
            </h1>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 space-y-1 p-4 overflow-y-auto">
            {links.map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href} onClick={onClose}>
                <Button
                  variant={pathname === href ? 'default' : 'ghost'}
                  className="w-full justify-start gap-3"
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{label}</span>
                </Button>
              </Link>
            ))}
          </nav>

          {/* Logout */}
          <div className="border-t border-border p-4">
            <form action="/api/auth/logout" method="POST">
              <Button variant="outline" className="w-full justify-start gap-3">
                <LogOut className="h-4 w-4 shrink-0" />
                <span>Logout</span>
              </Button>
            </form>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}
    </>
  )
}
