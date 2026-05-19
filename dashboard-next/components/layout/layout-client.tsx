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
    <div className="flex h-screen bg-background">
      <Sidebar
        role={role}
        clienteName={clienteName}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col md:ml-60">
        <Header
          title="Dashboard"
          userName={userName}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main className="flex-1 overflow-auto pt-16">
          <div className="p-4 md:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
