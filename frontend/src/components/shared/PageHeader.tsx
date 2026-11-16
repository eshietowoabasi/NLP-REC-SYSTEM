import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/**
 * The heading block of a page (design spec §2): a 28px/800 title, one line of plain text
 * underneath and the page's actions on the right.
 */
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="flex min-w-0 flex-col gap-1">
        <h2 className="page-title break-words">{title}</h2>
        {description && <div className="max-w-3xl page-lead">{description}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </div>
  )
}
