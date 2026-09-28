import { Download, Inbox } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { DecisionFilter, Recommendation, ReviewCounts, ScoreWeights } from '@/types/api'

import { useRecommendations } from './api'
import {
  CompletedSessionGate,
  EmptyPanel,
  ErrorPanel,
  KeywordsLine,
  LoadingBlock,
  OverlapBadge,
  ScoreContribution,
  SessionReviewHeader,
} from './components'
import { DecisionControl } from './DecisionControl'
import { DECISION_LABELS, formatPercent, formatWeight } from './labels'

const FILTERS: { value: DecisionFilter; label: string; count: keyof ReviewCounts }[] = [
  { value: 'all', label: 'All', count: 'total' },
  { value: 'undecided', label: 'Not reviewed yet', count: 'undecided' },
  { value: 'accepted', label: DECISION_LABELS.accepted, count: 'accepted' },
  { value: 'rejected', label: DECISION_LABELS.rejected, count: 'rejected' },
  { value: 'flagged', label: DECISION_LABELS.flagged, count: 'flagged' },
]

export function RecommendationsPage() {
  const sessionId = Number(useParams().sessionId)
  return (
    <CompletedSessionGate sessionId={sessionId} title="Suggested topics">
      {(session) => (
        <div className="mx-auto max-w-6xl space-y-5">
          <SessionReviewHeader
            sessionId={session.id}
            sessionName={session.session_name}
            title="Suggested topics"
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

  if (counts.total === 0) {
    return (
      <EmptyPanel icon={Inbox} title="No recommendations">
        The analysis finished but found no topics to recommend. Try again with more documents.
      </EmptyPanel>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-3xl text-sm leading-relaxed text-body-soft">
          Suggested topics, best first. Each has a score out of 100: employer demand{' '}
          <span className="font-bold text-ink">{formatWeight(weights.ner)}</span>, how often it
          comes up <span className="font-bold text-ink">{formatWeight(weights.topic)}</span> and how
          new it is <span className="font-bold text-ink">{formatWeight(weights.novelty)}</span>.
          Open a topic to see its evidence and decide.
        </p>
        <Button variant="outline" size="sm" asChild>
          <a href={`/api/sessions/${sessionId}/recommendations/export`} download>
            <Download aria-hidden="true" /> Download CSV
          </a>
        </Button>
      </div>
      <p className="text-[13px] text-body-soft">
        <span className="font-bold text-ink">
          {counts.reviewed} of {counts.total}
        </span>{' '}
        reviewed ·{' '}
        <span>
          {counts.potential_duplicates} {counts.potential_duplicates === 1 ? 'topic' : 'topics'} may
          already be in the NUC core
        </span>
      </p>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ToggleGroup
          type="single"
          variant="chip"
          value={decision}
          onValueChange={(value) => value && setDecision(value as DecisionFilter)}
          aria-label="Filter by decision"
          className="flex-wrap"
        >
          {FILTERS.map((filter) => (
            <ToggleGroupItem key={filter.value} value={filter.value}>
              {filter.label}
              <span className="tabular-nums opacity-70 before:content-['·_']">
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
          <Label htmlFor="hide-duplicates" className="font-semibold text-body">
            Hide topics that may already be in the NUC core
          </Label>
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyPanel icon={Inbox} title="Nothing matches these filters">
          Choose another filter, or show the topics that may already be in the NUC core.
        </EmptyPanel>
      ) : (
        <ol className="space-y-3.5" aria-label="Ranked recommendations">
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

/** One suggested topic (Recommendations.dc.html): rank, name, why, decision and score. */
function RecommendationCard({
  recommendation,
  weights,
}: {
  recommendation: Recommendation
  weights: ScoreWeights
}) {
  return (
    <article className="flex flex-col gap-5 rounded-[20px] border border-line bg-white px-[22px] py-[18px] lg:flex-row lg:items-center lg:gap-[22px]">
      <div className="flex min-w-0 flex-1 gap-4 lg:gap-[22px]">
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-sand-deep font-extrabold text-ink tabular-nums"
          aria-label={`Rank ${recommendation.rank}`}
        >
          {recommendation.rank}
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className="flex flex-col gap-1">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
              <h3 className="text-lg leading-snug font-extrabold tracking-[-0.01em] text-ink">
                <Link
                  to={`/recommendations/${recommendation.id}`}
                  className="hover:text-primary focus-visible:rounded focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none"
                >
                  {recommendation.topic_title}
                </Link>
              </h3>
              <OverlapBadge status={recommendation.overlap_status} />
            </div>
            <KeywordsLine keywords={recommendation.keywords} limit={6} />
          </div>
          <p className="line-clamp-2 text-sm leading-normal text-body">
            {recommendation.topic_description}
          </p>
          {recommendation.skills.length > 0 && (
            <p className="text-xs text-muted-ink">
              <span className="font-bold text-body">Skills: </span>
              {recommendation.skills
                .slice(0, 6)
                .map((s) => s.name)
                .join(', ')}
            </p>
          )}
          {recommendation.closest_nuc_course && (
            <p className="text-[13px] text-muted-ink">
              Closest NUC course:{' '}
              <strong className="text-ink">
                {recommendation.closest_nuc_course.code} {recommendation.closest_nuc_course.title}
              </strong>{' '}
              · <span className="tabular-nums">{formatPercent(recommendation.max_similarity)}</span>{' '}
              similar
            </p>
          )}
          <DecisionControl recommendation={recommendation} />
        </div>
      </div>
      <div className="shrink-0 rounded-[14px] bg-sand px-4 py-3.5 lg:w-[250px]">
        <ScoreContribution recommendation={recommendation} weights={weights} />
      </div>
    </article>
  )
}
