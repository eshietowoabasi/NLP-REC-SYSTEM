import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from 'cn'

/*
 * Banners (design spec): white card by default; tinted, borderless banners for success
 * (green), warnings and tips (amber), information (teal) and errors (red).
 */
const alertVariants = cva(
  "group/alert relative grid w-full gap-0.5 rounded-2xl border px-4 py-3.5 text-left text-sm has-data-[slot=alert-action]:relative has-data-[slot=alert-action]:pr-18 has-[>svg]:grid-cols-[auto_1fr] has-[>svg]:gap-x-3 *:[svg]:row-span-2 *:[svg]:translate-y-0.5 *:[svg]:text-current *:[svg:not([class*='size-'])]:size-[18px]",
  {
    variants: {
      variant: {
        default: 'border-line bg-card text-ink',
        destructive:
          'border-transparent bg-red-tint text-red *:data-[slot=alert-description]:text-red/90',
        success:
          'border-transparent bg-green-tint text-green-ink *:data-[slot=alert-description]:text-green-ink',
        warning:
          'border-transparent bg-amber-tint text-amber-ink *:data-[slot=alert-description]:text-amber-ink',
        info: 'border-transparent bg-teal-tint text-teal-ink *:data-[slot=alert-description]:text-teal-ink',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof alertVariants>) {
  return (
    <div
      data-slot="alert"
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-title"
      className={cn(
        'font-extrabold group-has-[>svg]/alert:col-start-2 [&_a]:underline [&_a]:underline-offset-3',
        className,
      )}
      {...props}
    />
  )
}

function AlertDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-description"
      className={cn(
        'text-sm leading-relaxed text-balance text-body md:text-pretty [&_a]:font-bold [&_a]:text-primary [&_a]:hover:underline [&_p:not(:last-child)]:mb-3',
        className,
      )}
      {...props}
    />
  )
}

function AlertAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div data-slot="alert-action" className={cn('absolute top-2 right-2', className)} {...props} />
  )
}

export { Alert, AlertTitle, AlertDescription, AlertAction }
