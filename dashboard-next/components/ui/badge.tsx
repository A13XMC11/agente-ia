import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors', {
  variants: {
    variant: {
      default: 'border border-accent bg-accent/10 text-accent',
      secondary: 'border border-border bg-border text-text-primary',
      destructive: 'border border-error bg-error/10 text-error',
      outline: 'border border-border text-text-secondary',
      success: 'border border-success bg-success/10 text-success',
      warning: 'border border-warning bg-warning/10 text-warning',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = ({ className, variant, ...props }: BadgeProps) => (
  <div className={cn(badgeVariants({ variant }), className)} {...props} />
)
