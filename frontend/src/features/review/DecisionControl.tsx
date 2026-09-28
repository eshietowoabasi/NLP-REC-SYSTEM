import { ArrowRight, BookOpenCheck, Check, CircleDashed, Loader2, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'
import { cn } from '@/lib/utils'
import type { PlannerDecision, Recommendation } from '@/types/api'

import { useDecide } from './api'
import { DECISION_ACTIONS, DECISION_ICONS, DECISIONS, designCoursePath } from './labels'

const STATUS: Record<PlannerDecision, { text: string; icon: typeof Check; className: string }> = {
  accepted: { text: 'Accepted', icon: Check, className: 'bg-green-tint text-green-ink' },
  rejected: { text: 'Rejected', icon: X, className: 'bg-red-tint text-red' },
  flagged: {
    text: 'Discuss later',
    icon: DECISION_ICONS.flagged,
    className: 'bg-amber-tint text-amber-ink',
  },
}

/** The decision as words with an icon (never colour alone). */
export function DecisionStatus({ decision }: { decision: PlannerDecision | null }) {
  if (!decision) {
    return (
      <p className="inline-flex items-center gap-1.5 rounded-full bg-divider px-3 py-1.5 text-[13px] font-bold text-muted-ink">
        <CircleDashed className="size-4" aria-hidden="true" /> Not reviewed yet
      </p>
    )
  }
  const { text, icon: Icon, className } = STATUS[decision]
  return (
    <p
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] font-extrabold',
        className,
      )}
    >
      <Icon className="size-4" strokeWidth={2.6} aria-hidden="true" /> {text}
    </p>
  )
}

/**
 * Accept / Reject / Discuss later while undecided; once decided, the status with a
 * "Change decision" link. Accepted topics lead to "Design course", or show the course once it
 * has been designed.
 */
export function DecisionControl({
  recommendation,
  layout = 'card',
}: {
  recommendation: Recommendation
  /** "card": compact row in the list; "panel": stacked, full width (Recommendation Detail). */
  layout?: 'card' | 'panel'
}) {
  const { canEdit } = useAuth()
  const navigate = useNavigate()
  const decide = useDecide()
  const [changing, setChanging] = useState(false)
  const current = recommendation.planner_decision
  const course = recommendation.course
  const pending = decide.isPending ? decide.variables?.decision : undefined
  const showButtons = canEdit && (current === null || changing)
  const designPath = designCoursePath(recommendation.id)
  const panel = layout === 'panel'

  const choose = (decision: PlannerDecision) => {
    const next = current === decision ? null : decision
    decide.mutate(
      { id: recommendation.id, decision: next },
      {
        onSuccess: () => {
          setChanging(false)
          if (next === 'accepted') {
            toast.success('Accepted. Next: design this course', {
              action: { label: 'Design course', onClick: () => void navigate(designPath) },
            })
          } else if (next === null) {
            toast.success('Decision cleared.')
          } else {
            toast.success(`Marked “${STATUS[next].text}”.`)
          }
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <div className={cn('space-y-3', !panel && 'pt-1')}>
      {showButtons ? (
        <div className="space-y-2">
          <div
            role="group"
            aria-label={`Decision for ${recommendation.topic_title}`}
            className={cn('flex flex-wrap gap-2.5', panel && 'grid grid-cols-1 gap-2')}
          >
            {DECISIONS.map((decision) => (
              <Button
                key={decision}
                size={panel ? 'default' : 'sm'}
                variant={decision === 'accepted' ? 'default' : 'outline'}
                aria-pressed={current === decision}
                className={cn(
                  current === decision &&
                    decision !== 'accepted' &&
                    'border-ink bg-sand-deep hover:bg-sand-deep',
                  current === decision && decision === 'accepted' && 'ring-3 ring-primary/25',
                )}
                disabled={decide.isPending}
                onClick={() => choose(decision)}
              >
                {pending === decision && <Loader2 className="animate-spin" aria-hidden="true" />}
                {DECISION_ACTIONS[decision]}
              </Button>
            ))}
          </div>
          {changing && (
            <p className="text-xs text-muted-ink">
              Choose a new decision, click the current one again to clear it, or{' '}
              <button
                type="button"
                className="cursor-pointer font-bold text-primary hover:underline"
                onClick={() => setChanging(false)}
              >
                keep “{current ? STATUS[current].text : 'Not reviewed yet'}”
              </button>
              .
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <DecisionStatus decision={current} />
          {canEdit && current !== null && !course && (
            <button
              type="button"
              className="h-10 cursor-pointer text-[13px] font-semibold text-muted-ink underline underline-offset-2 hover:text-ink"
              onClick={() => setChanging(true)}
            >
              Change decision
            </button>
          )}
        </div>
      )}

      {current === 'accepted' && !changing && (
        <div>
          {course ? (
            <p className="inline-flex flex-wrap items-center gap-x-1.5 gap-y-1 rounded-[10px] border border-input-line bg-white px-3.5 py-2 text-sm">
              <BookOpenCheck className="size-4 text-green" aria-hidden="true" />
              <span>
                <span className="font-bold">Course:</span> {course.course_code} –{' '}
                {course.course_title}
              </span>
              {canEdit && (
                <>
                  <span aria-hidden="true" className="text-faint">
                    ·
                  </span>
                  <Link
                    to={designPath}
                    className="font-bold text-primary hover:underline"
                    aria-label={`Edit course ${course.course_code}`}
                  >
                    Edit
                  </Link>
                </>
              )}
            </p>
          ) : (
            canEdit && (
              <Button asChild size={panel ? 'default' : 'sm'} className={cn(panel && 'w-full')}>
                <Link to={designPath}>
                  Design course <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            )
          )}
        </div>
      )}
      {panel && canEdit && course && current === 'accepted' && !changing && (
        <p className="text-xs text-muted-ink">
          To change the decision, remove the course first (Edit → Remove course).
        </p>
      )}
    </div>
  )
}
