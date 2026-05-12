'use client'

import { cn } from '@/lib/utils'
import { ReactNode, createContext, useContext, useState } from 'react'

interface TabsContextType {
  value: string
  onValueChange: (value: string) => void
}

const TabsContext = createContext<TabsContextType | undefined>(undefined)

const useTabsContext = () => {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('useTabsContext must be used within Tabs')
  }
  return context
}

interface TabsProps {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  children: ReactNode
  className?: string
}

export const Tabs = ({
  value,
  defaultValue,
  onValueChange,
  children,
  className
}: TabsProps) => {
  const [internalValue, setInternalValue] = useState(defaultValue || '')
  const isControlled = value !== undefined
  const currentValue = isControlled ? value : internalValue

  const handleValueChange = (newValue: string) => {
    if (!isControlled) {
      setInternalValue(newValue)
    }
    onValueChange?.(newValue)
  }

  return (
    <TabsContext.Provider value={{ value: currentValue, onValueChange: handleValueChange }}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsContext.Provider>
  )
}

interface TabsListProps {
  children: ReactNode
  className?: string
}

export const TabsList = ({ children, className }: TabsListProps) => (
  <div
    className={cn(
      'inline-flex h-10 items-center justify-center rounded-md bg-slate-100 p-1 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
      className
    )}
    role="tablist"
  >
    {children}
  </div>
)

interface TabsTriggerProps {
  value: string
  children: ReactNode
  className?: string
  disabled?: boolean
}

export const TabsTrigger = ({ value, children, className, disabled }: TabsTriggerProps) => {
  const { value: selectedValue, onValueChange } = useTabsContext()
  const isSelected = selectedValue === value

  return (
    <button
      role="tab"
      aria-selected={isSelected}
      disabled={disabled}
      onClick={() => !disabled && onValueChange(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
        isSelected
          ? 'bg-background text-foreground shadow-sm'
          : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-50',
        className
      )}
    >
      {children}
    </button>
  )
}

interface TabsContentProps {
  value: string
  children: ReactNode
  className?: string
}

export const TabsContent = ({ value, children, className }: TabsContentProps) => {
  const { value: selectedValue } = useTabsContext()
  const isSelected = selectedValue === value

  if (!isSelected) {
    return null
  }

  return (
    <div
      role="tabpanel"
      className={cn(
        'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className
      )}
    >
      {children}
    </div>
  )
}
