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
    <div className="flex min-h-screen bg-background">
      <Sidebar
        role={role}
        clienteName={clienteName}
        userName={userName}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col md:ml-64 min-w-0">
        <Header
          title="Dashboard"
          userName={userName}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main className="flex-1 overflow-auto pt-16">
          <div className="p-5 md:p-8 max-w-[1400px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
