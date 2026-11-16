import type { ComponentProps } from 'react'

import type { Badge } from '@/components/ui/badge'
import type { HarvestPhase, HarvestRun } from '@/types/api'

/** Plain-language label and badge colour for each phase of a job collection. */
export const HARVEST_PHASES: Record<
  HarvestPhase,
  { label: string; variant: NonNullable<ComponentProps<typeof Badge>['variant']> }
> = {
  queued: { label: 'Waiting to start', variant: 'neutral' },
  collecting: { label: 'Collecting adverts', variant: 'info' },
  preparing: { label: 'Preparing adverts', variant: 'warning' },
  ready: { label: 'Ready to analyse', variant: 'success' },
  failed: { label: 'Failed', variant: 'destructive' },
}

/** True while the collection or the processing of its adverts is still going on. */
export function isHarvestActive(run: HarvestRun | null | undefined): boolean {
  return run?.phase === 'queued' || run?.phase === 'collecting' || run?.phase === 'preparing'
}
