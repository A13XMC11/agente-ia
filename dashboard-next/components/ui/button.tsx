import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-accent text-accent-light hover:bg-accent-hover',
        destructive: 'bg-error text-white hover:bg-red-600',
        outline: 'border border-border bg-transparent hover:bg-border-light',
        ghost: 'hover:bg-border-light',
        link: 'text-accent underline-offset-4 hover:underline',
        secondary: 'bg-border-light text-primary hover:bg-border',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-12 px-8',
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

export const Button = ({
  className,
  variant,
  size,
  ...props
}: ButtonProps) => {
  return <button className={cn(buttonVariants({ variant, size, className }))} {...props} />
}
