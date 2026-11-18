import { ArrowRight, BookOpenCheck, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/useAuth'
import { cn } from '@/lib/utils'
import type { PlannerDecision, Recommendation, ScoreWeights } from '@/types/api'

import { useDecide, useRecommendation } from './api'
import { KeywordsLine, OverlapBadge, ScoreContribution } from './components'
import { DecisionControl } from './DecisionControl'
import { DECISION_ACTIONS, DECISION_LABELS, DECISIONS, designCoursePath, toPoints } from './labels'
import { Description, ExampleQuote } from './RecommendationDetailPage'

/** Keyboard shortcuts for deciding: A accept, R reject, L discuss later. */
const KEYS: Record<PlannerDecision, string> = { accepted: 'A', rejected: 'R', flagged: 'L' }

const CHIP: Record<PlannerDecision | 'open', string> = {
  accepted: 'bg-green-tint text-green-ink',
  rejected: 'bg-red-tint text-red',
  flagged: 'bg-amber-tint text-amber-ink',
  open: 'bg-divider text-muted-ink',
}

function isTyping(target: EventTarget | null) {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
  )
}

/**
 * Review topics (step 3): the ranked list and the chosen topic side by side. Deciding (buttons
 * or the A / R / L keys) moves on to the next topic not yet reviewed; ↑ / ↓ (or K / J) move
 * through the list. The chosen topic is kept in the link (`?topic=`) so it can be shared.
 * On phones the chosen topic comes first and the list follows.
 */
export function TopicReview({
  items,
  weights,
}: {
  items: Recommendation[]
  weights: ScoreWeights
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = Number(searchParams.get('topic'))
  const index = Math.max(
    0,
    items.findIndex((item) => item.id === requested),
  )
  const current = items[index]

  const select = useCallback(
    (id: number) =>
      setSearchParams(
        (params) => {
          params.set('topic', String(id))
          return params
        },
        { replace: true },
      ),
    [setSearchParams],
  )

  /** After a decision: the next topic not yet reviewed (after this one, then from the top). */
  const advance = useCallback(
    (decidedId: number) => {
      const at = items.findIndex((item) => item.id === decidedId)
      const order = [...items.slice(at + 1), ...items.slice(0, at)]
      const next = order.find((item) => item.planner_decision === null) ?? items[at + 1]
      if (next) select(next.id)
    },
    [items, select],
  )

  const move = useCallback(
    (step: number) => {
      const next = items[Math.min(Math.max(index + step, 0), items.length - 1)]
      if (next && next.id !== current?.id) select(next.id)
    },
    [items, index, current, select],
  )

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || isTyping(event.target)) return
      const key = event.key.toLowerCase()
      if (key === 'arrowdown' || key === 'j') {
        event.preventDefault()
        move(1)
      } else if (key === 'arrowup' || key === 'k') {
        event.preventDefault()
        move(-1)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [move])

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)]">
      <ol
        aria-label="Ranked recommendations"
        className="flex flex-col gap-1.5 rounded-[18px] border border-line bg-white p-2 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto"
      >
        {items.map((item) => (
          <li key={item.id}>
            <TopicRow
              recommendation={item}
              selected={item.id === current?.id}
              onSelect={() => select(item.id)}
            />
          </li>
        ))}
      </ol>
      {current && (
        <TopicPanel
          key={current.id}
          recommendation={current}
          weights={weights}
          position={{ index, total: items.length }}
          onDecided={advance}
          onMove={move}
        />
      )}
    </div>
  )
}

function TopicRow({
  recommendation,
  selected,
  onSelect,
}: {
  recommendation: Recommendation
  selected: boolean
  onSelect: () => void
}) {
  const ref = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (selected) ref.current?.scrollIntoView?.({ block: 'nearest' })
  }, [selected])
  const decision = recommendation.planner_decision
  const duplicate = recommendation.overlap_status === 'Potential Duplicate'
  return (
    <button
      ref={ref}
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-sand focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none',
        selected && 'bg-[#fbefe8] shadow-[inset_3px_0_0_var(--color-primary)] hover:bg-[#fbefe8]',
      )}
    >
      <span className="w-7 shrink-0 num text-xs text-muted-ink">#{recommendation.rank}</span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate text-sm font-bold text-ink">{recommendation.topic_title}</span>
        <span className={cn('text-[11.5px]', duplicate ? 'text-amber-ink' : 'text-green-ink')}>
          {duplicate ? 'May already be in NUC core' : 'Not in NUC core'}
        </span>
      </span>
      <span className="num text-sm font-semibold text-ink">
        {toPoints(recommendation.composite_score)}
      </span>
      <span
        className={cn(
          'w-[78px] shrink-0 rounded-md py-1 text-center text-[11px] font-bold',
          CHIP[decision ?? 'open'],
        )}
      >
        {decision ? DECISION_LABELS[decision] : 'Open'}
      </span>
    </button>
  )
}

function TopicPanel({
  recommendation,
  weights,
  position,
  onDecided,
  onMove,
}: {
  recommendation: Recommendation
  weights: ScoreWeights
  position: { index: number; total: number }
  onDecided: (id: number) => void
  onMove: (step: number) => void
}) {
  const { canEdit } = useAuth()
  const detail = useRecommendation(recommendation.id)
  const decide = useDecide()
  const current = recommendation.planner_decision
  // A topic with a designed course keeps its decision until the course is removed.
  const locked = current === 'accepted' && recommendation.course !== null
  const pending = decide.isPending ? decide.variables?.decision : undefined

  const choose = useCallback(
    (decision: PlannerDecision) => {
      if (decide.isPending) return
      const next = current === decision ? null : decision
      decide.mutate(
        { id: recommendation.id, decision: next },
        {
          onSuccess: () => {
            if (next === null) {
              toast.success('Decision cleared.')
              return
            }
            toast.success(`“${recommendation.topic_title}”: ${DECISION_LABELS[next]}.`)
            onDecided(recommendation.id)
          },
          onError: (error) => toast.error(error.message),
        },
      )
    },
    [decide, current, recommendation, onDecided],
  )

  useEffect(() => {
    if (!canEdit || locked) return
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || isTyping(event.target)) return
      const decision = DECISIONS.find((d) => KEYS[d].toLowerCase() === event.key.toLowerCase())
      if (decision) {
        event.preventDefault()
        choose(decision)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [canEdit, locked, choose])

  const evidence = detail.data?.evidence ?? []

  return (
    <section
      aria-labelledby="topic-title"
      className="order-first flex min-w-0 animate-slide-in flex-col gap-4 rounded-[18px] border border-line bg-white px-5 py-5 sm:px-6 lg:order-none"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-2">
          <span className="num text-xs text-muted-ink">
            Topic {position.index + 1} of {position.total} · rank #{recommendation.rank}
          </span>
          <h3
            id="topic-title"
            className="text-xl leading-snug font-extrabold tracking-[-0.01em] text-ink"
          >
            {recommendation.topic_title}
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            <OverlapBadge status={recommendation.overlap_status} />
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Previous topic"
            disabled={position.index === 0}
            onClick={() => onMove(-1)}
          >
            <ChevronUp aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Next topic"
            disabled={position.index >= position.total - 1}
            onClick={() => onMove(1)}
          >
            <ChevronDown aria-hidden="true" />
          </Button>
        </div>
      </div>

      <div className="rounded-[14px] bg-sand px-4 py-3.5">
        <ScoreContribution recommendation={recommendation} weights={weights} />
      </div>

      <Description text={recommendation.topic_description} />
      <KeywordsLine keywords={recommendation.keywords} limit={8} />

      <div className="flex flex-col gap-2.5">
        <h4 className="text-[11px] font-extrabold tracking-[0.08em] text-muted-ink">
          WHAT THE DOCUMENTS SAY
        </h4>
        {detail.isPending ? (
          <Skeleton className="h-20 w-full rounded-[14px]" />
        ) : evidence.length > 0 ? (
          evidence.slice(0, 2).map((item) => <ExampleQuote key={item.passage_id} evidence={item} />)
        ) : (
          <p className="text-sm text-body-soft">No extracts were stored for this topic.</p>
        )}
        {recommendation.closest_nuc_course && (
          <p className="text-[13px] text-muted-ink">
            Closest NUC course:{' '}
            <strong className="text-ink">
              {recommendation.closest_nuc_course.code} {recommendation.closest_nuc_course.title}
            </strong>
          </p>
        )}
        <Link
          to={`/recommendations/${recommendation.id}`}
          className="inline-flex items-center gap-1 self-start text-[13px] font-bold text-primary hover:underline"
        >
          All {evidence.length > 2 ? evidence.length : ''} extracts, notes and title edit
          <ArrowRight className="size-3.5" aria-hidden="true" />
        </Link>
      </div>

      <div className="flex flex-col gap-2.5 border-t border-divider pt-4">
        {canEdit && !locked ? (
          <>
            <div
              role="group"
              aria-label={`Decision for ${recommendation.topic_title}`}
              className="grid grid-cols-1 gap-2 sm:grid-cols-3"
            >
              {DECISIONS.map((decision) => (
                <Button
                  key={decision}
                  variant={decision === 'accepted' ? 'default' : 'outline'}
                  aria-pressed={current === decision}
                  aria-keyshortcuts={KEYS[decision]}
                  className={cn(
                    'justify-between',
                    current === decision &&
                      decision !== 'accepted' &&
                      'border-ink bg-sand-deep hover:bg-sand-deep',
                    current === decision && decision === 'accepted' && 'ring-3 ring-primary/30',
                  )}
                  disabled={decide.isPending}
                  onClick={() => choose(decision)}
                >
                  <span className="inline-flex items-center gap-2">
                    {pending === decision && (
                      <Loader2 className="animate-spin" aria-hidden="true" />
                    )}
                    {DECISION_ACTIONS[decision]}
                  </span>
                  <kbd
                    aria-hidden="true"
                    className={cn(
                      'rounded border px-1.5 num text-[11px] font-semibold',
                      decision === 'accepted'
                        ? 'border-white/40 text-white/90'
                        : 'border-line text-muted-ink',
                    )}
                  >
                    {KEYS[decision]}
                  </kbd>
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-ink">
              Deciding moves to the next topic not yet reviewed. Choose the current decision again
              to clear it.
            </p>
          </>
        ) : (
          <DecisionControl recommendation={recommendation} layout="panel" />
        )}
        {canEdit && current === 'accepted' && !locked && (
          <Button asChild variant="outline" size="sm" className="self-start">
            <Link to={designCoursePath(recommendation.id)}>
              <BookOpenCheck aria-hidden="true" /> Design this course now
            </Link>
          </Button>
        )}
      </div>
    </section>
  )
}
