import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from 'cn'
import { Slot } from 'radix-ui'

/*
 * SkillBridge buttons (design spec §4): primary = terracotta with white bold text; outline =
 * the "secondary" button (white, input border, ink text); link = terracotta bold text, no
 * underline until hover. Heights follow the spec: 46px page actions, 40px in cards.
 */
const buttonVariants = cva(
  "group/button inline-flex shrink-0 cursor-pointer items-center justify-center rounded-xl border border-transparent bg-clip-padding text-sm font-bold whitespace-nowrap transition-colors outline-none select-none focus-visible:ring-3 focus-visible:ring-ring/40 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-[18px]",
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-terracotta-dark',
        outline:
          'border-input-line bg-white text-ink hover:border-line hover:bg-sand aria-expanded:bg-sand',
        secondary: 'bg-sand-deep text-ink hover:bg-divider aria-expanded:bg-divider',
        ghost: 'text-body hover:bg-sand-deep hover:text-ink aria-expanded:bg-sand-deep',
        destructive: 'bg-red-tint text-red hover:bg-[#f9d9d5] focus-visible:ring-destructive/30',
        link: 'h-auto px-0 text-primary hover:text-terracotta-dark hover:underline',
      },
      size: {
        default:
          'h-[46px] gap-2 px-[18px] has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4',
        xs: "h-8 gap-1 rounded-lg px-2.5 text-xs [&_svg:not([class*='size-'])]:size-3.5",
        sm: "h-10 gap-1.5 rounded-[10px] px-4 text-[13px] [&_svg:not([class*='size-'])]:size-4",
        lg: 'h-[52px] gap-2.5 rounded-[14px] px-6 text-[15px]',
        icon: 'size-10 rounded-[10px]',
        'icon-xs': "size-7 rounded-lg [&_svg:not([class*='size-'])]:size-3.5",
        'icon-sm': 'size-8 rounded-lg',
        'icon-lg': 'size-11',
      },
    },
    compoundVariants: [{ variant: 'link', className: 'h-auto px-0' }],
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

function Button({
  className,
  variant = 'default',
  size = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : 'button'

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
