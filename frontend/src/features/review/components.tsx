import {
  AlertTriangle,
  ArrowLeft,
  CircleDashed,
  Hourglass,
  type LucideIcon,
  Sparkles,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useSession } from '@/features/sessions/api'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type {
  OverlapStatus,
  PlannerDecision,
  Recommendation,
  ScoreWeights,
  SessionDetail,
  WeightedTerm,
} from '@/types/api'

import { SessionProgress } from './SessionProgress'
import {
  contributionPoints,
  DECISION_ICONS,
  DECISION_LABELS,
  formatOutOf100,
  formatWeight,
  SCORE_PARTS,
  type ScoreLevel,
  scoreLevel,
  toPoints,
} from './labels'

/** "Keywords: problem solving, Selenium, test cases" (as written in the documents). */
export function KeywordsLine({
  keywords,
  limit = 8,
}: {
  keywords: WeightedTerm[]
  limit?: number
}) {
  if (keywords.length === 0) return null
  const shown = keywords.slice(0, limit).map((k) => k.label ?? k.term)
  return (
    <p className="text-xs leading-relaxed text-muted-ink">
      <span className="font-bold text-body">Keywords:</span> {shown.join(', ')}
    </p>
  )
}

/** "Not in NUC core" or amber "May already be in NUC core": icon + words, never colour alone. */
export function OverlapBadge({ status }: { status: OverlapStatus }) {
  return status === 'Potential Duplicate' ? (
    <Badge variant="warning">
      <AlertTriangle aria-hidden="true" /> May already be in NUC core
    </Badge>
  ) : (
    <Badge variant="info" title="Not similar to any NUC core course">
      <Sparkles aria-hidden="true" /> Not in NUC core
    </Badge>
  )
}

const DECISION_VARIANTS = {
  accepted: 'success',
  rejected: 'destructive',
  flagged: 'warning',
} as const satisfies Record<PlannerDecision, string>

/** Status chip (design spec §4): accepted green, rejected red, discuss later amber. */
export function DecisionBadge({ decision }: { decision: PlannerDecision | null }) {
  if (!decision) {
    return (
      <Badge variant="neutral">
        <CircleDashed aria-hidden="true" /> Not reviewed yet
      </Badge>
    )
  }
  const Icon = DECISION_ICONS[decision]
  return (
    <Badge variant={DECISION_VARIANTS[decision]}>
      <Icon aria-hidden="true" /> {DECISION_LABELS[decision]}
    </Badge>
  )
}

const LEVEL_STYLES: Record<ScoreLevel, string> = {
  High: 'text-ink font-bold',
  Medium: 'text-body',
  Low: 'text-muted-ink',
}

/** "High", "Medium" or "Low" for a 0–1 score (words, never colour alone). */
export function ScoreLevelText({ value, className }: { value: number; className?: string }) {
  const level = scoreLevel(value)
  return <span className={cn('text-xs', LEVEL_STYLES[level], className)}>{level}</span>
}

/**
 * A 0–1 score as a thin meter out of 100: the filled part in the series colour on a lighter
 * track of the same hue, with the points and the High/Medium/Low level beside it in text ink.
 */
export function ScoreMeter({
  label,
  value,
  emphasis = false,
}: {
  label: string
  value: number
  emphasis?: boolean
}) {
  const points = toPoints(value)
  return (
    <div className="grid grid-cols-[7.5rem_1fr_4.75rem] items-center gap-2 text-xs">
      <span className={cn('text-body-soft', emphasis && 'font-bold text-ink')}>{label}</span>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={points}
        aria-valuetext={`${points} out of 100, ${scoreLevel(value)}`}
        className="h-1.5 overflow-hidden rounded-full bg-viz-track"
      >
        <div className="h-full rounded-full bg-viz-series" style={{ width: `${points}%` }} />
      </div>
      <span className="flex items-baseline justify-end gap-1.5">
        <span className={cn('tabular-nums', emphasis ? 'font-extrabold' : 'font-bold text-ink')}>
          {points}
        </span>
        <ScoreLevelText value={value} className="w-12" />
      </span>
    </div>
  )
}

/**
 * The composite score out of 100 and its three weighted parts (Recommendations.dc.html and
 * RecommendationDetail.dc.html): a large figure, then one row per part with its points out of
 * 100 and High/Medium/Low in words. `detailed` adds each part's weight and a thin bar. The
 * figure's accessible name spells out how the parts add up.
 */
export function ScoreContribution({
  recommendation,
  weights,
  detailed = false,
}: {
  recommendation: Recommendation
  weights: ScoreWeights
  /** Show each part's weight and a bar (Recommendation Detail). */
  detailed?: boolean
}) {
  const composite = recommendation.composite_score
  const raw = SCORE_PARTS.map((part) => {
    const value = recommendation[part.field]
    const weight = weights[part.key]
    return { ...part, value, weight, contribution: weight * value }
  })
  const points = contributionPoints(
    raw.map((p) => p.contribution),
    composite,
  )
  const parts = raw.map((part, index) => ({ ...part, points: points[index] }))
  const summary = parts
    .map(
      (p) =>
        `${p.label} ${toPoints(p.value)} (${scoreLevel(p.value)}, ${formatWeight(p.weight)}) adds ${p.points} points`,
    )
    .join('; ')
  return (
    <figure
      className={cn('flex flex-col', detailed ? 'gap-3' : 'gap-2')}
      aria-label={`Score ${formatOutOf100(composite)}. ${summary}.`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <figcaption
          className={cn(
            'font-bold text-muted-ink',
            detailed ? 'text-[13px]' : 'text-xs tracking-[0.04em] uppercase',
          )}
        >
          Score
        </figcaption>
        <span
          className={cn(
            'leading-none font-extrabold tracking-[-0.02em] text-ink tabular-nums',
            detailed ? 'text-[38px]' : 'text-[26px]',
          )}
          aria-hidden="true"
        >
          {toPoints(composite)}
          <span
            className={cn(
              'font-semibold tracking-normal text-muted-ink',
              detailed ? 'text-[15px]' : 'text-[13px]',
            )}
          >
            /100
          </span>
        </span>
      </div>
      <ul className={cn(detailed ? 'space-y-3' : 'space-y-1.5')} aria-hidden="true">
        {parts.map((part) => (
          <li key={part.key} className="flex flex-col gap-[5px]">
            <div
              className={cn(
                'flex items-baseline justify-between gap-2',
                detailed ? 'text-[13px]' : 'text-xs',
              )}
            >
              <span className="text-ink">
                {part.label}
                {detailed && (
                  <span className="text-faint"> · {Math.round(part.weight * 100)}%</span>
                )}
              </span>
              <span className="flex items-baseline gap-1 whitespace-nowrap tabular-nums">
                <strong className="font-extrabold text-ink">{toPoints(part.value)}</strong>
                {!detailed && <span className="text-faint">·</span>}
                <ScoreLevelText value={part.value} className={detailed ? 'text-[13px]' : ''} />
              </span>
            </div>
            {detailed && (
              <div className="h-1.5 rounded-full bg-viz-track">
                <div
                  className="h-1.5 rounded-full bg-viz-series"
                  style={{ width: `${toPoints(part.value)}%` }}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
    </figure>
  )
}

export function ErrorPanel({
  title,
  error,
  onRetry,
}: {
  title: string
  error: Error
  onRetry: () => void
}) {
  return (
    <Alert variant="destructive">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="space-y-2">
        <p>{error.message}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </AlertDescription>
    </Alert>
  )
}

export function EmptyPanel({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon
  title: string
  children?: ReactNode
}) {
  return (
    <EmptyState icon={Icon} title={title}>
      {children}
    </EmptyState>
  )
}

export function LoadingBlock({ label }: { label: string }) {
  return (
    <div className="space-y-4" aria-label={label} role="status">
      <Skeleton className="h-9 w-1/3 rounded-xl" />
      <Skeleton className="h-40 w-full rounded-[20px]" />
      <Skeleton className="h-40 w-full rounded-[20px]" />
    </div>
  )
}

/**
 * Loads a session and renders `children` only once its analysis has completed; otherwise
 * shows the 404 page, a loading state, an error or a "not ready yet" message.
 */
export function CompletedSessionGate({
  sessionId,
  title,
  children,
}: {
  sessionId: number
  title: string
  children: (session: SessionDetail) => ReactNode
}) {
  const session = useSession(sessionId)
  if (
    !Number.isInteger(sessionId) ||
    (session.error instanceof ApiError && session.error.status === 404)
  ) {
    return <NotFoundPage />
  }
  if (session.isPending) return <LoadingBlock label="Loading session" />
  if (session.isError) {
    return (
      <ErrorPanel
        title="Could not load the session"
        error={session.error}
        onRetry={() => void session.refetch()}
      />
    )
  }
  if (session.data.status !== 'completed') {
    return (
      <div className="space-y-6">
        <SessionReviewHeader
          sessionId={sessionId}
          sessionName={session.data.session_name}
          title={title}
        />
        <EmptyPanel icon={Hourglass} title="Results are not ready">
          Evidence and recommendations appear once the analysis has completed. The session is
          currently {session.data.status}.
        </EmptyPanel>
      </div>
    )
  }
  return children(session.data)
}

/** Header shared by the session review screens: back link, name and section links. */
export function SessionReviewHeader({
  sessionId,
  sessionName,
  title,
}: {
  sessionId: number
  sessionName?: string
  title: string
}) {
  const links = [
    { to: `/sessions/${sessionId}/recommendations`, label: 'Suggested topics' },
    { to: `/sessions/${sessionId}/evidence`, label: 'Evidence' },
    { to: `/sessions/${sessionId}/curriculum`, label: 'Proposed courses' },
  ]
  return (
    <div className="space-y-4">
      <Link
        to={`/sessions/${sessionId}`}
        className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> {sessionName ?? 'Analysis session'}
      </Link>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="page-title">{title}</h2>
        <nav
          aria-label="Session review"
          className="flex flex-wrap gap-1.5 rounded-[14px] bg-sand-deep p-1"
        >
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  'flex h-10 items-center rounded-[10px] px-[18px] text-sm font-semibold text-body-soft hover:text-ink focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none',
                  isActive && 'bg-white font-extrabold text-ink',
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <SessionProgress sessionId={sessionId} />
    </div>
  )
}
