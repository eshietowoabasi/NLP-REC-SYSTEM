import { BriefcaseBusiness, Check, Loader2, RefreshCw, TriangleAlert } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useAuth } from '@/features/auth/useAuth'
import { useHarvestState, useStartHarvest } from '@/features/labour-market/api'
import { isHarvestActive } from '@/features/labour-market/labels'
import { cn } from '@/lib/utils'
import type { HarvestRun } from '@/types/api'

/** Adverts collected per run, and how old the last run may be before a review collects again. */
const TARGET_ADVERTS = 15
const PAGES_PER_SEARCH = 2
const FRESH_FOR_MS = 6 * 60 * 60 * 1000

function isFresh(run: HarvestRun | null | undefined) {
  if (!run || run.phase === 'failed') return false
  return Date.now() - new Date(run.created_at).getTime() < FRESH_FOR_MS
}

function minutesAgo(iso: string | null) {
  if (!iso) return ''
  const minutes = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60_000))
  return minutes < 60 ? `${minutes} min ago` : `${Math.round(minutes / 60)} h ago`
}

/**
 * Step 2 of New review: current job adverts for the programme, collected automatically from
 * MyJobMag when the step opens (unless a collection ran in the last few hours). New adverts
 * are ticked in the list below as soon as they are ready (``onCollecting`` lets the picker
 * remember what was there before). Planners can collect again at any time.
 */
export function JobCollectionPanel({
  programmeId,
  programmeName,
  onCollecting,
}: {
  programmeId: number
  programmeName: string | null
  onCollecting: () => void
}) {
  const { canEdit } = useAuth()
  const state = useHarvestState(programmeId > 0 ? programmeId : null)
  const start = useStartHarvest()
  const autoStarted = useRef<number | null>(null)
  const run = state.data?.latest_run ?? null
  const terms = state.data?.profile.search_terms ?? []
  const active = isHarvestActive(run)

  const collect = () => {
    onCollecting()
    start.mutate({ programmeId, targetCount: TARGET_ADVERTS, pagesPerField: PAGES_PER_SEARCH })
  }

  // Collect automatically once per programme when the step opens.
  useEffect(() => {
    if (!canEdit || !state.data || autoStarted.current === programmeId) return
    autoStarted.current = programmeId
    if (terms.length === 0) return
    if (isHarvestActive(run)) {
      onCollecting()
      return
    }
    if (!isFresh(run)) collect()
    // collect/onCollecting are stable enough for a once-per-programme effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canEdit, state.data, programmeId])

  const name = programmeName ?? 'this programme'
  const ready = run?.documents_ready ?? 0
  const total = run ? run.imported_count : 0

  let icon = <BriefcaseBusiness className="size-5" aria-hidden="true" />
  let title = `Current jobs for ${name}`
  let detail: string
  let progress: number | null = null
  if (state.isPending) {
    detail = 'Checking for recent job adverts…'
  } else if (terms.length === 0) {
    icon = <TriangleAlert className="size-5" aria-hidden="true" />
    detail = `Job collection is not set up for ${name} yet (an admin adds the job titles in Programmes). You can still upload documents below.`
  } else if (start.isPending || run?.phase === 'queued' || run?.phase === 'collecting') {
    icon = <Loader2 className="size-5 animate-spin" aria-hidden="true" />
    title = `Finding current jobs for ${name}`
    detail = `Searching MyJobMag for ${terms.slice(0, 4).join(', ')}${terms.length > 4 ? '…' : ''}. ${run?.examined_count ?? 0} adverts looked at, ${run?.found_count ?? 0} matching so far.`
    progress = run ? Math.min(95, (run.found_count / Math.max(run.target_count, 1)) * 100) : 5
  } else if (run?.phase === 'preparing') {
    icon = <Loader2 className="size-5 animate-spin" aria-hidden="true" />
    title = 'Preparing the adverts'
    detail = `${ready} of ${total} adverts ready. They are ticked below as soon as they are ready.`
    progress = total ? (ready / total) * 100 : 50
  } else if (run?.phase === 'failed') {
    icon = <TriangleAlert className="size-5" aria-hidden="true" />
    title = 'Job collection stopped'
    detail =
      run.error_message ?? 'The job site could not be reached. Try again, or upload documents.'
  } else if (run) {
    icon = <Check className="size-5" aria-hidden="true" />
    title =
      total > 0
        ? `${ready} current job advert${ready === 1 ? '' : 's'} collected ${minutesAgo(run.completed_at)}`
        : 'No new adverts this time'
    detail =
      total > 0
        ? 'New adverts are listed below as job adverts, newest first. Untick any you do not want.'
        : 'All matching adverts are already in the list below. Collect again later, or upload documents.'
  } else {
    detail = 'Collecting current adverts…'
  }

  const failed = run?.phase === 'failed' || start.isError

  return (
    <section
      aria-labelledby="jobs-title"
      className={cn(
        'flex flex-col gap-3 rounded-2xl border px-4 py-3.5',
        failed ? 'border-[#f0c9c2] bg-red-tint/40' : 'border-line bg-sand',
      )}
    >
      <div className="flex flex-wrap items-start gap-3">
        <span
          className={cn(
            'flex size-9 shrink-0 items-center justify-center rounded-xl',
            failed ? 'bg-red-tint text-red' : 'bg-white text-terracotta',
          )}
        >
          {icon}
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <h3 id="jobs-title" className="text-sm font-extrabold text-ink">
            {title}
          </h3>
          <p role="status" className="text-[13px] leading-relaxed text-body-soft">
            {start.isError ? start.error.message : detail}
          </p>
        </div>
        {canEdit && terms.length > 0 && !active && !start.isPending && (
          <Button type="button" variant="outline" size="sm" onClick={collect}>
            <RefreshCw aria-hidden="true" /> Collect {run ? 'again' : 'jobs'}
          </Button>
        )}
      </div>
      {progress !== null && (
        <Progress value={progress} aria-label="Job collection progress" className="h-1.5" />
      )}
    </section>
  )
}
