'use client'

import { cn } from '@/lib/utils'

interface SwitchProps {
  checked?: boolean
  onChange?: (checked: boolean) => void
  onCheckedChange?: (checked: boolean) => void
  disabled?: boolean
  className?: string
}

export const Switch = ({ checked = false, onChange, onCheckedChange, disabled = false, className }: SwitchProps) => {
  const handleChange = () => {
    if (!disabled) {
      const newValue = !checked
      onCheckedChange?.(newValue)
      onChange?.(newValue)
    }
  }

  return (
    <button
      onClick={handleChange}
      disabled={disabled}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        checked ? 'bg-accent' : 'bg-border',
        disabled && 'opacity-50 cursor-not-allowed',
        className,
      )}
      role="switch"
      aria-checked={checked}
    >
      <span
        className={cn(
          'inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform',
          checked ? 'translate-x-5' : 'translate-x-0.5',
        )}
      />
    </button>
  )
}
