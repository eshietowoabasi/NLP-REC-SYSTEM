import { AlertCircle, CheckCircle2, Circle, Loader2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import type { SessionStage, SessionStatus } from '@/types/api'

import { PIPELINE_STAGES, STATUS_LABELS } from './stages'

const VARIANTS = {
  pending: 'neutral',
  processing: 'info',
  completed: 'success',
  failed: 'destructive',
} as const satisfies Record<SessionStatus, string>

const ICONS = {
  pending: Circle,
  processing: Loader2,
  completed: CheckCircle2,
  failed: AlertCircle,
} as const

export function SessionStatusBadge({
  status,
  stage,
}: {
  status: SessionStatus
  /** Shown while running, e.g. "Running · Themes". */
  stage?: SessionStage | null
}) {
  const Icon = ICONS[status]
  const stageLabel =
    status === 'processing'
      ? (PIPELINE_STAGES.find((s) => s.id === stage)?.label ?? 'Queued')
      : null
  return (
    <Badge variant={VARIANTS[status]}>
      <Icon aria-hidden="true" className={status === 'processing' ? 'animate-spin' : undefined} />
      {STATUS_LABELS[status]}
      {stageLabel && <span className="font-semibold opacity-80">· {stageLabel}</span>}
    </Badge>
  )
}
