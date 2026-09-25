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
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useSession } from '@/features/sessions/api'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type { OverlapStatus, PlannerDecision, Recommendation, SessionDetail } from '@/types/api'

import { DECISION_ICONS, DECISION_LABELS, formatScore, SCORE_PARTS } from './labels'

/** Green "New" or amber "Potential Duplicate": always icon + words, never colour alone. */
export function OverlapBadge({ status }: { status: OverlapStatus }) {
  return status === 'Potential Duplicate' ? (
    <Badge
      variant="outline"
      className="border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300"
    >
      <AlertTriangle aria-hidden="true" /> Potential Duplicate
    </Badge>
  ) : (
    <Badge
      variant="outline"
      className="border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
      title="No significant overlap with the NUC core"
    >
      <Sparkles aria-hidden="true" /> New
    </Badge>
  )
}

const DECISION_STYLES: Record<PlannerDecision, string> = {
  accepted: 'text-emerald-700 dark:text-emerald-400',
  rejected: 'text-destructive',
  flagged: 'text-amber-700 dark:text-amber-400',
}

export function DecisionBadge({ decision }: { decision: PlannerDecision | null }) {
  if (!decision) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        <CircleDashed aria-hidden="true" /> Undecided
      </Badge>
    )
  }
  const Icon = DECISION_ICONS[decision]
  return (
    <Badge variant="outline" className={DECISION_STYLES[decision]}>
      <Icon aria-hidden="true" /> {DECISION_LABELS[decision]}
    </Badge>
  )
}

/**
 * A 0–1 score as a thin meter: the filled part in the series colour on a lighter track of
 * the same hue, with the number beside it in text ink.
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
  const percent = Math.round(Math.min(Math.max(value, 0), 1) * 100)
  return (
    <div className="grid grid-cols-[7.5rem_1fr_2.5rem] items-center gap-2 text-xs">
      <span className={cn('text-muted-foreground', emphasis && 'font-medium text-foreground')}>
        {label}
      </span>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={Number(value.toFixed(2))}
        className="h-1.5 overflow-hidden rounded-full bg-viz-series/15"
      >
        <div
          className={cn('h-full rounded-full bg-viz-series', !emphasis && 'opacity-70')}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span
        className={cn('text-right tabular-nums', emphasis ? 'font-semibold' : 'text-foreground')}
      >
        {formatScore(value)}
      </span>
    </div>
  )
}

export function ScoreBreakdown({ recommendation }: { recommendation: Recommendation }) {
  return (
    <div className="space-y-1.5">
      <ScoreMeter label="Composite" value={recommendation.composite_score} emphasis />
      {SCORE_PARTS.map((part) => (
        <ScoreMeter key={part.key} label={part.label} value={recommendation[part.field]} />
      ))}
    </div>
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
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center">
      <Icon className="size-10 text-muted-foreground" aria-hidden="true" />
      <h3 className="text-lg font-semibold">{title}</h3>
      {children && <div className="max-w-md text-sm text-muted-foreground">{children}</div>}
    </div>
  )
}

export function LoadingBlock({ label }: { label: string }) {
  return (
    <div className="space-y-3" aria-label={label} role="status">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
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
    { to: `/sessions/${sessionId}/evidence`, label: 'Evidence' },
    { to: `/sessions/${sessionId}/recommendations`, label: 'Recommendations' },
    { to: `/sessions/${sessionId}/curriculum`, label: 'Proposed curriculum' },
  ]
  return (
    <div className="space-y-3">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={`/sessions/${sessionId}`}>
          <ArrowLeft aria-hidden="true" /> {sessionName ?? 'Analysis session'}
        </Link>
      </Button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        <nav aria-label="Session review" className="flex flex-wrap gap-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground',
                  isActive && 'bg-muted text-foreground',
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
