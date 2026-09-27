import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from 'cn'
import { Slot } from 'radix-ui'

/*
 * Status chips (design spec §4): pills, 12px bold. success = accepted, warning = needs review /
 * "may already be in NUC core", destructive = rejected / errors, info = compared / viewer,
 * neutral = left out. Pair colour with an icon or words, never colour alone.
 */
const badgeVariants = cva(
  'group/badge inline-flex min-h-6 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border border-transparent px-2.5 py-0.5 text-xs font-bold whitespace-nowrap transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/40 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 aria-invalid:border-destructive [&>svg]:pointer-events-none [&>svg]:size-3.5!',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground [a]:hover:bg-terracotta-dark',
        secondary: 'bg-sand-deep text-ink [a]:hover:bg-divider',
        destructive: 'bg-red-tint text-red [a]:hover:bg-[#f9d9d5]',
        outline: 'border-input-line bg-white text-ink [a]:hover:bg-sand',
        ghost: 'hover:bg-sand-deep hover:text-ink',
        link: 'text-primary underline-offset-4 hover:underline',
        success: 'bg-green-tint text-green-ink',
        warning: 'bg-amber-tint text-amber-ink',
        info: 'bg-teal-tint text-teal-ink',
        neutral: 'bg-divider text-muted-ink',
        brand: 'bg-terracotta-tint text-terracotta-dark',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

function Badge({
  className,
  variant = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : 'span'

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
