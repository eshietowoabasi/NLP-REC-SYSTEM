import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/**
 * Empty and "not available" states (design spec §4): a centred picture, a title, one or two
 * sentences and at most one primary action.
 */
export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
  className,
}: {
  icon: LucideIcon
  title: string
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-3 rounded-[20px] border border-dashed border-input-line bg-white px-6 py-14 text-center',
        className,
      )}
    >
      <span className="flex size-16 items-center justify-center rounded-[18px] bg-terracotta-tint">
        <Icon className="size-7 text-terracotta" strokeWidth={1.7} aria-hidden="true" />
      </span>
      <h3 className="text-lg font-extrabold tracking-[-0.01em] text-ink">{title}</h3>
      {children && (
        <div className="max-w-md text-sm leading-relaxed text-body-soft">{children}</div>
      )}
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}
