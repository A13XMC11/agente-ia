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
  Menu,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

interface SidebarProps {
  role: 'super_admin' | 'admin' | 'operador'
  clienteName?: string
}

export const Sidebar = ({ role, clienteName }: SidebarProps) => {
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(true)

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
    { href: '/cliente/configuracion', label: 'Configuración', icon: Settings },
  ]

  const links = isAdmin ? adminLinks : clientLinks

  return (
    <>
      {/* Mobile Toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed left-4 top-4 z-50 lg:hidden"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
      </Button>

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen w-60 border-r border-border bg-card-bg transition-transform duration-300 lg:translate-x-0 pt-16 lg:pt-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Title */}
          <div className="border-b border-border px-6 py-4">
            <h1 className="text-lg font-bold text-accent">
              {isAdmin ? 'Agente IA' : clienteName || 'Dashboard'}
            </h1>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 space-y-1 p-4">
            {links.map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href}>
                <Button
                  variant={pathname === href ? 'default' : 'ghost'}
                  className="w-full justify-start gap-3"
                  onClick={() => {
                    if (window.innerWidth < 1024) {
                      setIsOpen(false)
                    }
                  }}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </Button>
              </Link>
            ))}
          </nav>

          {/* Logout */}
          <div className="border-t border-border p-4">
            <form action="/api/auth/logout" method="POST">
              <Button variant="outline" className="w-full justify-start gap-3">
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </Button>
            </form>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
