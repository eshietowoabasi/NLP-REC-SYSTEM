import { AlertCircle, CheckCircle2, Circle, Loader2 } from 'lucide-react'

import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import type { SessionDetail } from '@/types/api'

import { PIPELINE_STAGES, stageStates, type StageState } from './stages'

const ICONS: Record<StageState, typeof Circle> = {
  done: CheckCircle2,
  current: Loader2,
  failed: AlertCircle,
  waiting: Circle,
}

const ICON_STYLES: Record<StageState, string> = {
  done: 'text-emerald-600 dark:text-emerald-400',
  current: 'animate-spin text-sky-600 dark:text-sky-400',
  failed: 'text-destructive',
  waiting: 'text-muted-foreground/50',
}

const STATE_LABELS: Record<StageState, string> = {
  done: 'done',
  current: 'in progress',
  failed: 'failed',
  waiting: 'not started',
}

/** Validating → … → Scoring, with the progress bar and per-stage timings. */
export function StageTracker({ session }: { session: SessionDetail }) {
  const states = stageStates(session.status, session.current_stage)
  const queued = session.status === 'processing' && session.current_stage === 'queued'

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">
            {queued ? 'Waiting for the analysis worker…' : 'Progress'}
          </span>
          <span className="font-medium tabular-nums">{session.progress_percent}%</span>
        </div>
        <Progress value={session.progress_percent} aria-label="Analysis progress" />
      </div>
      <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" aria-label="Analysis stages">
        {PIPELINE_STAGES.map((stage) => {
          const state = states[stage.id]
          const Icon = ICONS[state]
          const seconds = session.stage_timings[stage.id]
          return (
            <li
              key={stage.id}
              className={cn(
                'flex items-start gap-2 rounded-md border p-2.5',
                state === 'current' &&
                  'border-sky-300 bg-sky-50 dark:border-sky-800 dark:bg-sky-950/40',
                state === 'failed' && 'border-destructive/50 bg-destructive/5',
              )}
              aria-current={state === 'current' ? 'step' : undefined}
            >
              <Icon
                className={cn('mt-0.5 size-4 shrink-0', ICON_STYLES[state])}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {stage.label}
                  <span className="sr-only"> — {STATE_LABELS[state]}</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  {stage.description}
                  {seconds !== undefined && state === 'done' && ` · ${seconds.toFixed(1)} s`}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
