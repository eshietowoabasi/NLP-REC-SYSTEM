import { BriefcaseBusiness, Check, Loader2, RefreshCw, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { useAuth } from '@/features/auth/useAuth'
import { useHarvestState, useStartHarvest } from '@/features/labour-market/api'
import { isHarvestActive } from '@/features/labour-market/labels'
import { cn } from '@/lib/utils'
import type { HarvestRun } from '@/types/api'

/** Adverts collected per run, and how old the last run may be before a review collects again. */
/** How many adverts one collection gathers; planners pick from these. */
const SIZES = [50, 100, 200, 500] as const
const DEFAULT_SIZE = 100
const PAGES_PER_SEARCH = 2
const FRESH_FOR_MS = 6 * 60 * 60 * 1000

function isFresh(run: HarvestRun | null | undefined) {
  if (!run || run.phase === 'failed') return false
  return Date.now() - new Date(run.created_at).getTime() < FRESH_FOR_MS
}

/** "information-technology" → "Information Technology". */
function fieldLabel(slug: string) {
  return slug
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
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
  advertCount = 0,
  unusedAdverts = 0,
  onUseAll,
}: {
  programmeId: number
  programmeName: string | null
  onCollecting: () => void
  /** Ready job adverts of the programme (all collections so far). */
  advertCount?: number
  /** How many of them are not ticked yet. */
  unusedAdverts?: number
  onUseAll?: () => void
}) {
  const { canEdit } = useAuth()
  const state = useHarvestState(programmeId > 0 ? programmeId : null)
  const start = useStartHarvest()
  const autoStarted = useRef<number | null>(null)
  const run = state.data?.latest_run ?? null
  const profile = state.data?.profile
  const terms = profile?.search_titles ?? profile?.search_terms ?? []
  const fields = profile?.search_fields ?? []
  const [size, setSize] = useState<number>(DEFAULT_SIZE)
  const active = isHarvestActive(run)
  const [extra, setExtra] = useState('')
  const extraTerms = extra
    .split(',')
    .map((term) => term.trim())
    .filter((term) => term.length >= 2)

  const collect = (withExtra = false) => {
    onCollecting()
    start.mutate({
      programmeId,
      targetCount: size,
      pagesPerField: PAGES_PER_SEARCH,
      extraTerms: withExtra ? extraTerms : [],
    })
  }

  // Collect automatically once per programme when the step opens.
  useEffect(() => {
    if (!canEdit || !state.data || autoStarted.current === programmeId) return
    autoStarted.current = programmeId
    if (terms.length === 0 && fields.length === 0) return
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
  } else if (terms.length === 0 && fields.length === 0) {
    icon = <TriangleAlert className="size-5" aria-hidden="true" />
    detail = `Job collection is not set up for ${name} yet (an admin adds the job titles in Programmes). You can still upload documents below.`
  } else if (start.isPending || run?.phase === 'queued' || run?.phase === 'collecting') {
    icon = <Loader2 className="size-5 animate-spin" aria-hidden="true" />
    title = `Collecting ${run?.target_count ?? size} current ${name} job adverts`
    const how = fields.length
      ? `SkillBridge reads every ${fields.map(fieldLabel).join(' and ')} advert on MyJobMag and keeps the ones that ask for ${name} skills, and searches ${terms.length} ${name} job titles.`
      : `SkillBridge searches ${terms.length} ${name} job titles on MyJobMag.`
    detail = `${how} ${run?.imported_count ?? 0} collected so far (${ready} ready to analyse), ${run?.examined_count ?? 0} adverts looked at. They are ticked below as they become ready.`
    progress = run ? Math.min(97, (run.imported_count / Math.max(run.target_count, 1)) * 100) : 3
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
        ? `${total} new job advert${total === 1 ? '' : 's'} collected ${minutesAgo(run.completed_at)}`
        : 'No new adverts this time'
    detail = `${advertCount} ${name} job adverts are ready to analyse in all${run.documents_processing > 0 ? ` (${run.documents_processing} more still being prepared)` : ''}. Collect more to analyse a bigger picture.`
  } else {
    detail = 'Collecting current adverts…'
  }

  const failed = run?.phase === 'failed' || start.isError
  const canCollect = canEdit && (terms.length > 0 || fields.length > 0)
  const busy = active || start.isPending

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
      </div>
      {progress !== null && (
        <Progress value={progress} aria-label="Job collection progress" className="h-1.5" />
      )}
      {(canCollect || (onUseAll && unusedAdverts > 0)) && (
        <div className="flex flex-col gap-2 border-t border-line pt-3 sm:flex-row sm:flex-wrap sm:items-center">
          {canCollect && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[13px] font-semibold text-ink">Collect</span>
              <div
                role="radiogroup"
                aria-label="How many adverts to collect"
                className="flex gap-1"
              >
                {SIZES.map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={size === value}
                    disabled={busy}
                    onClick={() => setSize(value)}
                    className={cn(
                      'rounded-lg border px-2.5 py-1 num text-xs font-bold transition-colors',
                      size === value
                        ? 'border-ink bg-ink text-white'
                        : 'border-line bg-white text-ink hover:bg-sand',
                    )}
                  >
                    {value}
                  </button>
                ))}
              </div>
              <span className="text-[13px] font-semibold text-ink">more adverts</span>
              <Button type="button" size="sm" disabled={busy} onClick={() => collect()}>
                <RefreshCw aria-hidden="true" /> {busy ? 'Collecting…' : 'Collect'}
              </Button>
            </div>
          )}
          {onUseAll && unusedAdverts > 0 && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="sm:ml-auto"
              onClick={onUseAll}
            >
              Use all {advertCount} job adverts
            </Button>
          )}
        </div>
      )}
      {canCollect && (
        <form
          className="flex flex-col gap-2 border-t border-line pt-3 sm:flex-row sm:items-center"
          onSubmit={(event) => {
            event.preventDefault()
            if (extraTerms.length > 0 && !busy) collect(true)
          }}
        >
          <label
            htmlFor="extra-job-titles"
            className="text-[13px] font-semibold text-ink sm:shrink-0"
          >
            Other job titles to search
          </label>
          <Input
            id="extra-job-titles"
            value={extra}
            onChange={(event) => setExtra(event.target.value)}
            placeholder="e.g. business analyst, ERP consultant"
            className="h-9 bg-white"
          />
          <Button
            type="submit"
            size="sm"
            variant="outline"
            className="sm:shrink-0"
            disabled={busy || extraTerms.length === 0}
          >
            Search these too
          </Button>
        </form>
      )}
    </section>
  )
}
