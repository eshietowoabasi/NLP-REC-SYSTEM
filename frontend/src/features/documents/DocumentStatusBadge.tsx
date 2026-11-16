import { AlertCircle, Archive, CheckCircle2, Clock, Loader2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { DocumentStatus } from '@/types/api'

import { STATUS_LABELS } from './labels'

const ICONS = {
  uploaded: Clock,
  parsing: Loader2,
  ready: CheckCircle2,
  failed: AlertCircle,
  archived: Archive,
} as const

const VARIANTS = {
  uploaded: 'neutral',
  parsing: 'info',
  ready: 'success',
  failed: 'destructive',
  archived: 'neutral',
} as const satisfies Record<DocumentStatus, string>

interface DocumentStatusBadgeProps {
  status: DocumentStatus
  /** Shown as a tooltip on failed documents. */
  errorMessage?: string | null
}

export function DocumentStatusBadge({ status, errorMessage }: DocumentStatusBadgeProps) {
  const Icon = ICONS[status]
  const badge = (
    <Badge variant={VARIANTS[status]}>
      <Icon aria-hidden="true" className={status === 'parsing' ? 'animate-spin' : undefined} />
      {STATUS_LABELS[status]}
    </Badge>
  )
  if (status !== 'failed' || !errorMessage) return badge
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0} aria-label={`Failed: ${errorMessage}`}>
          {badge}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{errorMessage}</TooltipContent>
    </Tooltip>
  )
}
