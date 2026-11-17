import { ArrowRight, Check, PartyPopper } from 'lucide-react'
import { Link } from 'react-router'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'
import { DownloadReportButton } from '@/features/reports/DownloadReportButton'
import { cn } from '@/lib/utils'
import { useSession } from '@/features/sessions/api'
import type { SessionProgress as Progress, SessionStatus, SessionSummary } from '@/types/api'

import { useSessionProgress } from './api'

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`

const REPORT_TEXT = {
  none: 'report not generated',
  queued: 'report being generated',
  processing: 'report being generated',
  completed: 'report ready',
  failed: 'report failed',
} as const

interface Step {
  label: string
  detail: string
  /** Where the step leads; null while it cannot be opened yet. */
  to: string | null
  done: boolean
}

const ANALYSIS_TEXT: Record<SessionStatus, (s: SessionSummary) => string> = {
  pending: () => 'not started',
  processing: (s) => `${s.progress_percent}% done`,
  completed: (s) => plural(s.recommendation_count, 'topic') + ' found',
  failed: () => 'stopped, see why',
}

function steps(session: SessionSummary, p: Progress | undefined): Step[] {
  const id = session.id
  const ready = session.status === 'completed' && p !== undefined
  const evidence: Step = {
    label: 'Evidence',
    detail: plural(session.document_count, 'document'),
    to: `/sessions/${id}`,
    done: session.document_count > 0,
  }
  const analyse: Step = {
    label: 'Analyse',
    detail: ANALYSIS_TEXT[session.status](session),
    to: session.status === 'completed' ? `/sessions/${id}/evidence` : `/sessions/${id}`,
    done: session.status === 'completed',
  }
  if (!ready) {
    return [
      evidence,
      analyse,
      { label: 'Review', detail: 'after the analysis', to: null, done: false },
      { label: 'Design courses', detail: 'after reviewing', to: null, done: false },
      { label: 'Report', detail: 'at the end', to: null, done: false },
    ]
  }
  const reviewDone = p.total > 0 && p.reviewed === p.total
  const designDone = p.accepted > 0 && p.accepted_with_courses === p.accepted
  const report = p.latest_report?.status ?? 'none'
  return [
    evidence,
    analyse,
    {
      label: 'Review',
      detail: `${p.reviewed} of ${p.total} reviewed`,
      to: `/sessions/${id}/recommendations${reviewDone ? '' : '?decision=undecided'}`,
      done: reviewDone,
    },
    {
      label: 'Design courses',
      detail:
        p.accepted > 0
          ? `${plural(p.courses, 'course')} designed · ${p.accepted} accepted`
          : `${plural(p.courses, 'course')} designed`,
      to: `/sessions/${id}/recommendations?decision=accepted`,
      done: designDone,
    },
    {
      label: 'Report',
      detail: REPORT_TEXT[report],
      to: `/reports?session=${id}`,
      done: report === 'completed',
    },
  ]
}

/**
 * The five steps of a review: ① Evidence → ② Analyse → ③ Review → ④ Design courses →
 * ⑤ Report, with live counts and links, shown on every page of a review. Once the analysis is
 * complete a banner suggests the next step. On phones only the current step is spelled out.
 */
export function SessionProgress({ sessionId }: { sessionId: number }) {
  const session = useSession(sessionId)
  const completed = session.data?.status === 'completed'
  const progress = useSessionProgress(sessionId, completed)
  const { canEdit } = useAuth()
  if (!session.data) return null
  const p = progress.data
  const list = steps(session.data, completed ? p : undefined)
  const current = list.findIndex((step) => !step.done)
  const allReviewed = completed && p !== undefined && p.total > 0 && p.reviewed === p.total
  const coursesMissing = p ? p.accepted - p.accepted_with_courses : 0

  return (
    <div className="space-y-3">
      <nav
        aria-label="Session progress"
        className="animate-rise overflow-hidden rounded-[18px] night-grid px-3 py-3 text-white sm:px-4"
      >
        <ol className="grid grid-cols-5 gap-1.5">
          {list.map((step, index) => {
            const isCurrent = index === current
            const label = `Step ${index + 1}: ${step.label}, ${step.detail}${step.done ? ' (done)' : ''}`
            const body = (
              <>
                <span
                  className={cn(
                    'relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full border border-night-line bg-night-raised num text-[13px] font-semibold text-night-text',
                    step.done && 'border-transparent bg-emerald-500/20 text-emerald-300',
                    isCurrent &&
                      'border-transparent bg-terracotta text-white shadow-[0_0_0_4px_rgba(214,98,58,0.25)]',
                  )}
                  aria-hidden="true"
                >
                  {step.done ? <Check className="size-4" strokeWidth={2.6} /> : index + 1}
                </span>
                <span
                  className={cn(
                    'hidden min-w-0 flex-1 flex-col gap-0.5 text-center md:flex lg:text-left',
                  )}
                >
                  <span className="truncate text-[13px] font-bold text-white">{step.label}</span>
                  <span className="truncate text-[11.5px] text-night-muted">{step.detail}</span>
                </span>
              </>
            )
            const shape = cn(
              'relative flex h-full flex-col items-center gap-2 rounded-xl px-1.5 py-2 lg:flex-row lg:gap-3 lg:px-3',
              isCurrent && 'bg-night-hover',
              !step.to && 'opacity-55',
            )
            return (
              <li key={step.label} className="relative">
                {index > 0 && (
                  <span
                    aria-hidden="true"
                    className={cn(
                      'absolute top-[23px] right-1/2 left-[-50%] h-px bg-night-line lg:hidden',
                      list[index - 1].done && 'bg-emerald-400/50',
                    )}
                  />
                )}
                {step.to ? (
                  <Link
                    to={step.to}
                    aria-label={label}
                    aria-current={isCurrent ? 'step' : undefined}
                    className={cn(
                      shape,
                      'transition-colors hover:bg-night-hover focus-visible:ring-3 focus-visible:ring-ember/50 focus-visible:outline-none',
                    )}
                  >
                    {body}
                  </Link>
                ) : (
                  <span aria-label={label} role="group" className={shape}>
                    {body}
                  </span>
                )}
              </li>
            )
          })}
        </ol>
        {current >= 0 && (
          <p className="mt-2 text-center text-[12px] text-night-muted md:hidden">
            Step {current + 1} of 5:{' '}
            <span className="font-bold text-white">{list[current].label}</span> ·{' '}
            {list[current].detail}
          </p>
        )}
      </nav>

      {allReviewed && coursesMissing > 0 && (
        <Alert variant="success">
          <PartyPopper aria-hidden="true" />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
            <span>
              <strong>All reviewed.</strong> You accepted {p?.accepted}
              {p && p.accepted_with_courses > 0 && ` (${p.accepted_with_courses} already designed)`}
              .
            </span>
            {canEdit && (
              <Button size="sm" asChild>
                <Link to={`/sessions/${sessionId}/recommendations?decision=accepted`}>
                  Design their courses <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}
      {allReviewed && coursesMissing === 0 && (
        <Alert variant="success">
          <Check aria-hidden="true" />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
            <span>
              <strong>Ready.</strong>{' '}
              {p.accepted > 0
                ? `Every accepted topic has a course (${plural(p.courses, 'course')}).`
                : 'Every recommendation has been reviewed.'}
            </span>
            {canEdit ? (
              <DownloadReportButton sessionId={sessionId} size="sm">
                Download your report
              </DownloadReportButton>
            ) : (
              <Button size="sm" variant="outline" asChild>
                <Link to={`/reports?session=${sessionId}`}>
                  View reports <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
