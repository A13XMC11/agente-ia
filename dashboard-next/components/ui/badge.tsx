import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors', {
  variants: {
    variant: {
      default: 'border border-text-primary text-text-primary bg-transparent',
      secondary: 'border border-border text-text-secondary',
      destructive: 'border border-text-muted text-text-muted',
      outline: 'border border-border text-text-secondary',
      success: 'border border-success bg-success/10 text-success',
      warning: 'border border-text-secondary text-text-secondary',
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
