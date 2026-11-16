import { cn } from '@/lib/utils'

import { useSystemHealth } from './api'

type Tone = 'ok' | 'warn' | 'down' | 'pending'

const DOT: Record<Tone, string> = {
  ok: 'bg-green',
  warn: 'bg-amber',
  down: 'bg-red',
  pending: 'bg-faint/50 animate-pulse',
}

/** Compact status dot + label for the top bar, polling GET /api/health. */
export function ApiStatusIndicator() {
  const { data, isPending, isError } = useSystemHealth()

  let tone: Tone = 'pending'
  let label = 'Checking API…'
  if (isError) {
    tone = 'down'
    label = 'API unreachable'
  } else if (data?.status === 'ok') {
    tone = 'ok'
    label = 'API connected'
  } else if (data?.status === 'degraded') {
    tone = 'warn'
    label = 'API degraded'
  }

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy={isPending}
      className="flex items-center gap-2 text-xs text-muted-ink"
    >
      <span aria-hidden="true" className={cn('size-2 rounded-full', DOT[tone])} />
      <span className="sr-only lg:not-sr-only">{label}</span>
    </div>
  )
}
