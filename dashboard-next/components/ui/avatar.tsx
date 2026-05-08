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

  const colors = [
    'bg-purple-600',
    'bg-blue-600',
    'bg-pink-600',
    'bg-green-600',
    'bg-yellow-600',
    'bg-red-600',
    'bg-indigo-600',
    'bg-cyan-600',
  ]

  const colorIndex = name.charCodeAt(0) % colors.length
  const bgColor = colors[colorIndex]

  return (
    <div
      className={cn(
        'flex h-10 w-10 items-center justify-center rounded-full font-semibold text-white',
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
