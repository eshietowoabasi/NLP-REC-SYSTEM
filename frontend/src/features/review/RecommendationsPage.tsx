import { BookOpenCheck, Inbox, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useAuth } from '@/features/auth/useAuth'
import type { DecisionFilter, PlannerDecision, Recommendation, ReviewCounts } from '@/types/api'

import { useDecide, useRecommendations } from './api'
import {
  CompletedSessionGate,
  DecisionBadge,
  EmptyPanel,
  ErrorPanel,
  LoadingBlock,
  OverlapBadge,
  ScoreBreakdown,
  SessionReviewHeader,
} from './components'
import { DECISION_ACTIONS, DECISION_ICONS, DECISION_LABELS, DECISIONS } from './labels'

const FILTERS: { value: DecisionFilter; label: string; count: keyof ReviewCounts }[] = [
  { value: 'all', label: 'All', count: 'total' },
  { value: 'undecided', label: 'Undecided', count: 'undecided' },
  { value: 'accepted', label: DECISION_LABELS.accepted, count: 'accepted' },
  { value: 'rejected', label: DECISION_LABELS.rejected, count: 'rejected' },
  { value: 'flagged', label: DECISION_LABELS.flagged, count: 'flagged' },
]

export function RecommendationsPage() {
  const sessionId = Number(useParams().sessionId)
  return (
    <CompletedSessionGate sessionId={sessionId} title="Recommendations">
      {(session) => (
        <div className="mx-auto max-w-5xl space-y-6">
          <SessionReviewHeader
            sessionId={session.id}
            sessionName={session.session_name}
            title="Recommendations"
          />
          <RecommendationReview sessionId={session.id} />
        </div>
      )}
    </CompletedSessionGate>
  )
}

function RecommendationReview({ sessionId }: { sessionId: number }) {
  const [decision, setDecision] = useState<DecisionFilter>('all')
  const [hideDuplicates, setHideDuplicates] = useState(false)
  const list = useRecommendations(sessionId, { decision, hide_duplicates: hideDuplicates })

  if (list.isPending) return <LoadingBlock label="Loading recommendations" />
  if (list.isError) {
    return (
      <ErrorPanel
        title="Could not load recommendations"
        error={list.error}
        onRetry={() => void list.refetch()}
      />
    )
  }
  const { items, counts } = list.data
  const reviewedPercent = counts.total ? (counts.reviewed / counts.total) * 100 : 0

  if (counts.total === 0) {
    return (
      <EmptyPanel icon={Inbox} title="No recommendations">
        The analysis completed but found no themes to recommend. Try a session with more documents
        or a smaller minimum theme size.
      </EmptyPanel>
    )
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
          <p>
            <span className="font-semibold">
              {counts.reviewed} of {counts.total}
            </span>{' '}
            reviewed
          </p>
          <p className="text-muted-foreground">
            {counts.potential_duplicates} potential duplicate
            {counts.potential_duplicates === 1 ? '' : 's'} of NUC core content
          </p>
        </div>
        <Progress value={reviewedPercent} aria-label="Review progress" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ToggleGroup
          type="single"
          variant="outline"
          value={decision}
          onValueChange={(value) => value && setDecision(value as DecisionFilter)}
          aria-label="Filter by decision"
          className="flex-wrap"
        >
          {FILTERS.map((filter) => (
            <ToggleGroupItem key={filter.value} value={filter.value}>
              {filter.label}
              <span className="text-muted-foreground tabular-nums">{counts[filter.count]}</span>
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <div className="flex items-center gap-2">
          <Checkbox
            id="hide-duplicates"
            checked={hideDuplicates}
            onCheckedChange={(checked) => setHideDuplicates(checked === true)}
          />
          <Label htmlFor="hide-duplicates">Hide potential duplicates</Label>
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyPanel icon={Inbox} title="Nothing matches these filters">
          Choose another decision filter or show potential duplicates.
        </EmptyPanel>
      ) : (
        <ol className="space-y-4" aria-label="Ranked recommendations">
          {items.map((recommendation) => (
            <li key={recommendation.id}>
              <RecommendationCard recommendation={recommendation} />
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const { canEdit } = useAuth()
  return (
    <Card>
      <CardContent className="grid gap-4 lg:grid-cols-[1fr_17rem]">
        <div className="min-w-0 space-y-2">
          <div className="flex items-start gap-3">
            <span
              className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold tabular-nums"
              aria-label={`Rank ${recommendation.rank}`}
            >
              {recommendation.rank}
            </span>
            <div className="min-w-0 space-y-1.5">
              <h3 className="text-base leading-tight font-semibold">
                <Link to={`/recommendations/${recommendation.id}`} className="hover:underline">
                  {recommendation.topic_title}
                </Link>
              </h3>
              <div className="flex flex-wrap gap-1.5">
                <OverlapBadge status={recommendation.overlap_status} />
                <DecisionBadge decision={recommendation.planner_decision} />
                {recommendation.has_mapping && (
                  <Badge variant="secondary">
                    <BookOpenCheck aria-hidden="true" /> Mapped to a course
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <p className="line-clamp-2 text-sm text-muted-foreground">
            {recommendation.topic_description}
          </p>
          {recommendation.skills.length > 0 && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Skills: </span>
              {recommendation.skills
                .slice(0, 6)
                .map((s) => s.name)
                .join(', ')}
            </p>
          )}
          {canEdit && <QuickDecision recommendation={recommendation} />}
        </div>
        <ScoreBreakdown recommendation={recommendation} />
      </CardContent>
    </Card>
  )
}

/** Accept / Reject / Flag in one click; clicking the current decision clears it. */
function QuickDecision({ recommendation }: { recommendation: Recommendation }) {
  const decide = useDecide()
  const current = recommendation.planner_decision
  const pending = decide.isPending ? decide.variables?.decision : undefined

  const choose = (decision: PlannerDecision) => {
    const next = current === decision ? null : decision
    decide.mutate(
      { id: recommendation.id, decision: next, notes: recommendation.planner_notes },
      {
        onSuccess: () =>
          toast.success(
            next
              ? `${DECISION_LABELS[next]}: ${recommendation.topic_title}`
              : `Decision cleared: ${recommendation.topic_title}`,
          ),
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <div
      className="flex flex-wrap gap-2 pt-1"
      role="group"
      aria-label={`Decision for ${recommendation.topic_title}`}
    >
      {DECISIONS.map((decision) => {
        const Icon = DECISION_ICONS[decision]
        const active = current === decision
        const locked = recommendation.has_mapping && decision !== 'accepted'
        return (
          <Button
            key={decision}
            size="sm"
            variant={active ? 'default' : 'outline'}
            aria-pressed={active}
            disabled={decide.isPending || locked || (recommendation.has_mapping && active)}
            title={
              locked || (recommendation.has_mapping && active)
                ? 'Remove the course mapping before changing this decision.'
                : undefined
            }
            onClick={() => choose(decision)}
          >
            {pending === decision ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
            ) : (
              <Icon aria-hidden="true" />
            )}
            {DECISION_ACTIONS[decision]}
          </Button>
        )
      })}
    </div>
  )
}
