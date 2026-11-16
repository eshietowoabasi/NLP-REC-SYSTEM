import { ArrowRight, Check, PartyPopper } from 'lucide-react'
import { Link } from 'react-router'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'
import { DownloadReportButton } from '@/features/reports/DownloadReportButton'
import { cn } from '@/lib/utils'
import type { SessionProgress as Progress } from '@/types/api'

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
  to: string
  done: boolean
}

function steps(sessionId: number, p: Progress): Step[] {
  const reviewDone = p.total > 0 && p.reviewed === p.total
  const designDone = p.accepted > 0 && p.accepted_with_courses === p.accepted
  const report = p.latest_report?.status ?? 'none'
  return [
    {
      label: 'Review',
      detail: `${p.reviewed} of ${p.total} reviewed`,
      to: `/sessions/${sessionId}/recommendations${reviewDone ? '' : '?decision=undecided'}`,
      done: reviewDone,
    },
    {
      label: 'Design courses',
      detail:
        p.accepted > 0
          ? `${plural(p.courses, 'course')} designed · ${p.accepted} accepted`
          : `${plural(p.courses, 'course')} designed`,
      to: `/sessions/${sessionId}/recommendations?decision=accepted`,
      done: designDone,
    },
    {
      label: 'Report',
      detail: REPORT_TEXT[report],
      to: `/reports?session=${sessionId}`,
      done: report === 'completed',
    },
  ]
}

/**
 * The review workflow of a completed session: ① Review → ② Design courses → ③ Report, with
 * live counts, links to each step and a banner suggesting the next one.
 */
export function SessionProgress({ sessionId }: { sessionId: number }) {
  const progress = useSessionProgress(sessionId)
  const { canEdit } = useAuth()
  if (!progress.data || progress.data.session_status !== 'completed') return null
  const p = progress.data
  const list = steps(sessionId, p)
  const current = list.findIndex((step) => !step.done)
  const allReviewed = p.total > 0 && p.reviewed === p.total
  const coursesMissing = p.accepted - p.accepted_with_courses

  return (
    <div className="space-y-3">
      <nav aria-label="Session progress">
        <ol className="grid gap-3 sm:grid-cols-3">
          {list.map((step, index) => (
            <li key={step.label}>
              <Link
                to={step.to}
                aria-label={`Step ${index + 1}: ${step.label}, ${step.detail}${step.done ? ' (done)' : ''}`}
                aria-current={index === current ? 'step' : undefined}
                className={cn(
                  'flex h-full items-center gap-3 rounded-2xl border border-line bg-white px-4 py-3 transition-colors hover:border-input-line focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none',
                  index === current && 'border-2 border-primary px-[15px] py-[11px]',
                )}
              >
                <span
                  className={cn(
                    'flex size-8 shrink-0 items-center justify-center rounded-full bg-divider text-sm font-extrabold text-ink',
                    step.done && 'bg-green-tint text-green',
                    index === current && 'bg-primary text-primary-foreground',
                  )}
                  aria-hidden="true"
                >
                  {step.done ? <Check className="size-4" strokeWidth={2.6} /> : index + 1}
                </span>
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="block text-sm font-extrabold text-ink">{step.label}</span>
                  {index === 0 && p.total > 0 && (
                    <span className="block h-1.5 rounded-full bg-divider" aria-hidden="true">
                      <span
                        className="block h-1.5 rounded-full bg-primary"
                        style={{ width: `${Math.round((p.reviewed / p.total) * 100)}%` }}
                      />
                    </span>
                  )}
                  <span className="block text-xs text-body-soft">{step.detail}</span>
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </nav>

      {allReviewed && coursesMissing > 0 && (
        <Alert variant="success">
          <PartyPopper aria-hidden="true" />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
            <span>
              <strong>All reviewed.</strong> You accepted {p.accepted}
              {p.accepted_with_courses > 0 && ` (${p.accepted_with_courses} already designed)`}.
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
