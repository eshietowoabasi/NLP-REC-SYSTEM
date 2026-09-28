import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/**
 * A filter pill (e.g. "All · 56"): white with a border, the chosen one ink with white text.
 * `count` is shown after a middle dot.
 */
export function FilterChip({
  active,
  onClick,
  count,
  children,
}: {
  active: boolean
  onClick: () => void
  count?: number
  children: ReactNode
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'inline-flex h-[38px] cursor-pointer items-center gap-1 rounded-full border px-3.5 text-[13px] font-bold whitespace-nowrap transition-colors focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none',
        active
          ? 'border-ink bg-ink text-white'
          : 'border-input-line bg-white text-ink hover:bg-sand',
      )}
    >
      {children}
      {count !== undefined && (
        <span className="tabular-nums opacity-80">
          <span aria-hidden="true">· </span>
          {count}
        </span>
      )}
    </button>
  )
}
