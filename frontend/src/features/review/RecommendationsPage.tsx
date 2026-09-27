import { Download, Inbox } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { DecisionFilter, Recommendation, ReviewCounts, ScoreWeights } from '@/types/api'

import { useRecommendations } from './api'
import {
  CompletedSessionGate,
  EmptyPanel,
  ErrorPanel,
  LoadingBlock,
  OverlapBadge,
  ScoreContribution,
  SessionReviewHeader,
} from './components'
import { DecisionControl } from './DecisionControl'
import { DECISION_LABELS, formatPercent, formatWeight } from './labels'

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
          <RecommendationReview sessionId={session.id} weights={session.parameter_config.weights} />
        </div>
      )}
    </CompletedSessionGate>
  )
}

function RecommendationReview({
  sessionId,
  weights,
}: {
  sessionId: number
  weights: ScoreWeights
}) {
  // The decision filter lives in the URL (?decision=undecided) so dashboard links can open it.
  const [searchParams, setSearchParams] = useSearchParams()
  const fromUrl = searchParams.get('decision')
  const decision: DecisionFilter = FILTERS.some((f) => f.value === fromUrl)
    ? (fromUrl as DecisionFilter)
    : 'all'
  const setDecision = (value: DecisionFilter) =>
    setSearchParams(
      (params) => {
        if (value === 'all') params.delete('decision')
        else params.set('decision', value)
        return params
      },
      { replace: true },
    )
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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-prose text-sm text-muted-foreground">
          Candidate course topics ranked by a score out of 100: skill demand{' '}
          <span className="text-foreground">{formatWeight(weights.ner)}</span>, theme strength{' '}
          <span className="text-foreground">{formatWeight(weights.topic)}</span> and novelty{' '}
          <span className="text-foreground">{formatWeight(weights.novelty)}</span>. Open a topic to
          see its evidence and decide.
        </p>
        <Button variant="outline" size="sm" asChild>
          <a href={`/api/sessions/${sessionId}/recommendations/export`} download>
            <Download aria-hidden="true" /> Download CSV
          </a>
        </Button>
      </div>
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
              <span className="text-muted-foreground tabular-nums">
                {counts[filter.count]}
                {filter.value === 'accepted' &&
                  ` · ${counts.accepted_with_courses} with course${counts.accepted_with_courses === 1 ? '' : 's'}`}
              </span>
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
              <RecommendationCard recommendation={recommendation} weights={weights} />
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function RecommendationCard({
  recommendation,
  weights,
}: {
  recommendation: Recommendation
  weights: ScoreWeights
}) {
  return (
    <Card>
      <CardContent className="grid gap-5 lg:grid-cols-[1fr_16rem]">
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
          {recommendation.closest_nuc_course && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground tabular-nums">
                {formatPercent(recommendation.max_similarity)} similar
              </span>{' '}
              to {recommendation.closest_nuc_course.code} {recommendation.closest_nuc_course.title}{' '}
              (closest NUC course)
            </p>
          )}
          <DecisionControl recommendation={recommendation} />
        </div>
        <div className="lg:border-l lg:pl-5">
          <ScoreContribution recommendation={recommendation} weights={weights} />
        </div>
      </CardContent>
    </Card>
  )
}
