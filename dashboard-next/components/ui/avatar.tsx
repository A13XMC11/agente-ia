'use client'

import { cn } from '@/lib/utils'
import { useState } from 'react'

interface AvatarProps {
  name: string
  src?: string
  className?: string
}

export const Avatar = ({ name, src, className }: AvatarProps) => {
  const [hasError, setHasError] = useState(!src)

  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const shades = [
    'bg-[#253745]',
    'bg-[#1a3040]',
    'bg-[#2a4050]',
    'bg-[#1e2d38]',
    'bg-[#203545]',
    'bg-[#162838]',
    'bg-[#2d4355]',
    'bg-[#1c3040]',
  ]

  const colorIndex = name.charCodeAt(0) % shades.length
  const bgColor = className?.includes('bg-') ? '' : shades[colorIndex]

  return (
    <div
      className={cn(
        'flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold text-text-primary shrink-0',
        bgColor,
        className,
      )}
      title={name}
    >
      {!hasError && src ? (
        <img
          src={src}
          alt={name}
          className="h-full w-full rounded-full object-cover"
          onError={() => setHasError(true)}
        />
      ) : (
        initials
      )}
    </div>
  )
}
