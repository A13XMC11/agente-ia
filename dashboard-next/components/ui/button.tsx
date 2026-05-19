import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium',
    'transition-all duration-150 cursor-pointer select-none',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background',
    'disabled:pointer-events-none disabled:opacity-40',
    'active:scale-[0.97]',
  ].join(' '),
  {
    variants: {
      variant: {
        default: [
          'bg-accent text-background font-semibold',
          'hover:bg-accent-hover',
          'shadow-[0_0_0_1px_rgba(56,189,248,0.3),0_2px_12px_rgba(56,189,248,0.2)]',
          'hover:shadow-[0_0_0_1px_rgba(56,189,248,0.5),0_4px_20px_rgba(56,189,248,0.3)]',
        ].join(' '),
        destructive: 'bg-error text-white hover:bg-red-500 shadow-[0_2px_12px_rgba(248,113,113,0.2)]',
        outline: [
          'border border-border-light bg-transparent text-text-secondary',
          'hover:bg-surface hover:text-text-primary hover:border-accent/30',
        ].join(' '),
        ghost: 'text-text-secondary hover:bg-surface hover:text-text-primary',
        link: 'text-accent underline-offset-4 hover:underline p-0 h-auto',
        secondary: 'bg-surface text-text-primary border border-border hover:bg-card-bg hover:border-border-light',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-12 px-8 text-base',
        icon: 'h-10 w-10 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    children?: ReactNode
  }

export const Button = ({ className, variant, size, ...props }: ButtonProps) => (
  <button className={cn(buttonVariants({ variant, size, className }))} {...props} />
)
