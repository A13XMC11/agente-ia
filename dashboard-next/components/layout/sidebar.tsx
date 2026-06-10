'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useClerk } from '@clerk/nextjs'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  TrendingUp,
  Calendar,
  Settings,
  CreditCard,
  Bot,
  BarChart2,
  Receipt,
  Megaphone,
  ShoppingBag,
  Bell,
  LogOut,
  ChevronRight,
} from 'lucide-react'

interface SidebarProps {
  role: 'super_admin' | 'admin' | 'operador'
  clienteName?: string
  userName?: string
  isOpen: boolean
  onClose: () => void
}

const adminLinks = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/clientes', label: 'Clientes', icon: Users },
]

const clientSections = [
  {
    label: null,
    links: [{ href: '/cliente', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Gestión',
    links: [
      { href: '/cliente/conversaciones', label: 'Conversaciones', icon: MessageSquare },
      { href: '/cliente/leads', label: 'Leads', icon: TrendingUp },
      { href: '/cliente/citas', label: 'Citas', icon: Calendar },
      { href: '/cliente/pagos', label: 'Pagos', icon: CreditCard },
    ],
  },
  {
    label: 'Crecimiento',
    links: [
      { href: '/cliente/campanas', label: 'Campañas', icon: Megaphone },
      { href: '/cliente/seguimientos', label: 'Seguimientos', icon: Bell },
      { href: '/cliente/catalogo', label: 'Catálogo', icon: ShoppingBag },
      { href: '/cliente/analytics', label: 'Analytics', icon: BarChart2 },
    ],
  },
  {
    label: 'Cuenta',
    links: [
      { href: '/cliente/billing', label: 'Facturación', icon: Receipt },
      { href: '/cliente/configuracion', label: 'Configuración', icon: Settings },
    ],
  },
]

interface NavLinkProps {
  href: string
  label: string
  icon: React.ElementType
  isActive: boolean
  onClick: () => void
}

function NavLink({ href, label, icon: Icon, isActive, onClick }: NavLinkProps) {
  return (
    <Link href={href} onClick={onClick} className="block">
      <span
        className={cn(
          'group relative flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm cursor-pointer select-none',
          'transition-all duration-200',
          isActive
            ? 'bg-accent/8 text-accent font-medium'
            : 'text-text-secondary hover:bg-white/[0.04] hover:text-text-primary',
        )}
      >
        {isActive && (
          <span
            className="absolute left-0 top-1 bottom-1 w-0.5 rounded-r-full bg-accent"
            style={{ boxShadow: '0 0 8px rgba(56,189,248,0.6)' }}
          />
        )}
        <Icon
          className={cn(
            'h-[15px] w-[15px] shrink-0 transition-colors duration-200',
            isActive
              ? 'text-accent'
              : 'text-text-muted group-hover:text-text-secondary',
          )}
          strokeWidth={isActive ? 2.1 : 1.75}
        />
        <span className="flex-1 leading-none">{label}</span>
        {isActive && (
          <ChevronRight
            className="h-3 w-3 text-accent/40 shrink-0"
            strokeWidth={2.5}
          />
        )}
      </span>
    </Link>
  )
}

function getInitials(str: string): string {
  const local = str.split('@')[0]
  const parts = local.split(/[._-]/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return local.slice(0, 2).toUpperCase()
}

export const Sidebar = ({
  role,
  clienteName,
  userName,
  isOpen,
  onClose,
}: SidebarProps) => {
  const pathname = usePathname()
  const { signOut } = useClerk()
  const isAdmin = role === 'super_admin'

  const handleSignOut = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    signOut({ redirectUrl: '/sign-in' })
  }

  return (
    <>
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 flex h-[100dvh] w-[min(16rem,calc(100vw-2rem))] flex-col',
          'transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
          'border-r border-border bg-background',
          'md:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo + status */}
        <div className="h-16 flex items-center gap-3 px-5 border-b border-border shrink-0">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl"
            style={{
              background: 'rgba(56,189,248,0.10)',
              border: '1px solid rgba(56,189,248,0.22)',
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
            }}
          >
            <Bot className="h-[15px] w-[15px] text-accent" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-text-primary leading-none truncate">
              {isAdmin ? 'Agente IA' : (clienteName || 'Mi Agente')}
            </p>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="relative inline-flex h-1.5 w-1.5">
                <span
                  className="absolute inline-flex h-full w-full rounded-full bg-success opacity-70"
                  style={{ animation: 'ping-slow 2.4s cubic-bezier(0,0,0.2,1) infinite' }}
                />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
              </span>
              <p className="text-[10px] text-text-muted leading-none">Agente activo</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2 px-2 min-h-0">
          {isAdmin ? (
            <div className="space-y-0.5 p-1">
              {adminLinks.map(({ href, label, icon }) => (
                <NavLink
                  key={href}
                  href={href}
                  label={label}
                  icon={icon}
                  isActive={pathname === href}
                  onClick={onClose}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-0.5">
              {clientSections.map((section, i) => (
                <div key={i}>
                  {section.label && (
                    <span className="nav-section-label">{section.label}</span>
                  )}
                  <div className={cn('space-y-0.5 px-1', i === 0 && 'px-1 py-1')}>
                    {section.links.map(({ href, label, icon }) => (
                      <NavLink
                        key={href}
                        href={href}
                        label={label}
                        icon={icon}
                        isActive={pathname === href || pathname.startsWith(href + '/')}
                        onClick={onClose}
                      />
                    ))}
                  </div>
                  {i < clientSections.length - 1 && (
                    <div className="mx-3 mt-2 border-t border-border/50" />
                  )}
                </div>
              ))}
            </div>
          )}
        </nav>

        {/* User footer */}
        <div
          className="shrink-0 border-t border-border p-3"
          style={{ background: 'rgba(255,255,255,0.015)' }}
        >
          <div className="flex items-center gap-2.5 px-1 py-1">
            <div
              className="h-7 w-7 rounded-lg shrink-0 flex items-center justify-center text-[11px] font-bold select-none"
              style={{
                background: 'rgba(56,189,248,0.10)',
                color: 'var(--accent)',
                border: '1px solid rgba(56,189,248,0.18)',
              }}
            >
              {userName ? getInitials(userName) : 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-text-secondary truncate leading-none">
                {userName || 'Usuario'}
              </p>
              <p className="text-[10px] text-text-muted mt-0.5 capitalize leading-none">
                {role === 'super_admin' ? 'Super Admin' : role}
              </p>
            </div>
            <button
              onClick={handleSignOut}
              className={[
                'shrink-0 h-7 w-7 flex items-center justify-center rounded-lg cursor-pointer',
                'text-text-muted hover:text-error hover:bg-error/8',
                'transition-all duration-150 active:scale-[0.94]',
              ].join(' ')}
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
            >
              <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}
    </>
  )
}
