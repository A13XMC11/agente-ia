'use client'

import { cn } from '@/lib/utils'
import { useState } from 'react'

interface SwitchProps {
  checked?: boolean
  onChange?: (checked: boolean) => void
  disabled?: boolean
  className?: string
}

export const Switch = ({ checked = false, onChange, disabled = false, className }: SwitchProps) => {
  const [isChecked, setIsChecked] = useState(checked)

  const handleChange = () => {
    if (!disabled) {
      const newValue = !isChecked
      setIsChecked(newValue)
      onChange?.(newValue)
    }
  }

  return (
    <button
      onClick={handleChange}
      disabled={disabled}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        isChecked ? 'bg-accent' : 'bg-border',
        disabled && 'opacity-50 cursor-not-allowed',
        className,
      )}
      role="switch"
      aria-checked={isChecked}
    >
      <span
        className={cn(
          'inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform',
          isChecked ? 'translate-x-5' : 'translate-x-0.5',
        )}
      />
    </button>
  )
}
