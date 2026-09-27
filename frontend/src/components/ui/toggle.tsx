'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from 'cn'
import { Toggle as TogglePrimitive } from 'radix-ui'

/*
 * chip: the filter pills of the mockups (white with a border; the chosen one ink with white
 * text). segment: buttons on a sand track, the chosen one terracotta (e.g. credit units).
 */
const toggleVariants = cva(
  "group/toggle inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-[10px] text-sm font-bold whitespace-nowrap transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/40 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          'bg-transparent text-body hover:bg-sand-deep hover:text-ink data-[state=on]:bg-sand-deep',
        outline:
          'border border-input-line bg-white text-ink hover:bg-sand data-[state=on]:border-ink data-[state=on]:bg-ink data-[state=on]:text-white',
        chip: 'rounded-full border border-input-line bg-white px-3.5! text-[13px] text-ink hover:bg-sand data-[state=on]:border-ink data-[state=on]:bg-ink data-[state=on]:text-white',
        segment:
          'bg-transparent text-body-soft hover:text-ink data-[state=on]:bg-primary data-[state=on]:font-extrabold data-[state=on]:text-primary-foreground',
      },
      size: {
        default:
          'h-10 min-w-10 px-3.5 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3',
        sm: "h-9 min-w-9 px-3 text-[13px] [&_svg:not([class*='size-'])]:size-3.5",
        lg: 'h-11 min-w-11 px-4',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

function Toggle({
  className,
  variant = 'default',
  size = 'default',
  ...props
}: React.ComponentProps<typeof TogglePrimitive.Root> & VariantProps<typeof toggleVariants>) {
  return (
    <TogglePrimitive.Root
      data-slot="toggle"
      className={cn(toggleVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Toggle, toggleVariants }
