'use client'

import { useState } from 'react'
import { Sidebar } from './sidebar'
import { Header } from './header'

interface LayoutClientProps {
  role: 'super_admin' | 'admin' | 'operador'
  clienteName?: string
  userName: string
  children: React.ReactNode
}

export function LayoutClient({ role, clienteName, userName, children }: LayoutClientProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-[100dvh] overflow-x-hidden bg-background">
      <Sidebar
        role={role}
        clienteName={clienteName}
        userName={userName}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col md:ml-64">
        <Header
          title="Dashboard"
          userName={userName}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main className="flex-1 overflow-x-hidden overflow-y-auto pt-16">
          <div className="mx-auto w-full max-w-[1400px] min-w-0 px-4 py-5 sm:px-5 md:px-8 md:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
