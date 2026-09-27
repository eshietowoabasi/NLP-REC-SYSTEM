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
  accepted: { text: 'Accepted', icon: Check, className: 'text-emerald-700 dark:text-emerald-400' },
  rejected: { text: 'Rejected', icon: X, className: 'text-destructive' },
  flagged: {
    text: 'Discuss later',
    icon: DECISION_ICONS.flagged,
    className: 'text-amber-700 dark:text-amber-400',
  },
}

/** The decision as words with an icon (never colour alone). */
export function DecisionStatus({ decision }: { decision: PlannerDecision | null }) {
  if (!decision) {
    return (
      <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <CircleDashed className="size-4" aria-hidden="true" /> Not reviewed yet
      </p>
    )
  }
  const { text, icon: Icon, className } = STATUS[decision]
  return (
    <p className={cn('flex items-center gap-1.5 text-sm font-semibold', className)}>
      <Icon className="size-4" aria-hidden="true" /> {text}
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
            className={cn('flex flex-wrap gap-2', panel && 'grid grid-cols-1 sm:grid-cols-3')}
          >
            {DECISIONS.map((decision) => {
              const Icon = DECISION_ICONS[decision]
              return (
                <Button
                  key={decision}
                  size="sm"
                  variant="outline"
                  aria-pressed={current === decision}
                  className={cn(current === decision && 'border-foreground/40 bg-muted')}
                  disabled={decide.isPending}
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
          {changing && (
            <p className="text-xs text-muted-foreground">
              Choose a new decision, click the current one again to clear it, or{' '}
              <button
                type="button"
                className="underline underline-offset-2 hover:text-foreground"
                onClick={() => setChanging(false)}
              >
                keep “{current ? STATUS[current].text : 'Not reviewed yet'}”
              </button>
              .
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <DecisionStatus decision={current} />
          {canEdit && current !== null && !course && (
            <button
              type="button"
              className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
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
            <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
              <BookOpenCheck
                className="size-4 text-emerald-700 dark:text-emerald-400"
                aria-hidden="true"
              />
              <span>
                <span className="font-medium">Course:</span> {course.course_code} –{' '}
                {course.course_title}
              </span>
              {canEdit && (
                <>
                  <span aria-hidden="true" className="text-muted-foreground">
                    ·
                  </span>
                  <Link
                    to={designPath}
                    className="font-medium underline-offset-4 hover:underline"
                    aria-label={`Edit course ${course.course_code}`}
                  >
                    Edit
                  </Link>
                </>
              )}
            </p>
          ) : (
            canEdit && (
              <Button asChild className={cn(panel && 'w-full')}>
                <Link to={designPath}>
                  Design course <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            )
          )}
        </div>
      )}
      {panel && canEdit && course && current === 'accepted' && !changing && (
        <p className="text-xs text-muted-foreground">
          To change the decision, remove the course first (Edit → Remove course).
        </p>
      )}
    </div>
  )
}
