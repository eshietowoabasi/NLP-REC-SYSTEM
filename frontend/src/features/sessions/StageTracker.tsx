import { AlertCircle, Check, Circle, Loader2 } from 'lucide-react'

import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import type { SessionDetail } from '@/types/api'

import { PIPELINE_STAGES, stageStates, type StageState } from './stages'

const ICONS: Record<StageState, typeof Circle> = {
  done: Check,
  current: Loader2,
  failed: AlertCircle,
  waiting: Circle,
}

const DOT_STYLES: Record<StageState, string> = {
  done: 'bg-green-tint text-green',
  current: 'bg-primary text-primary-foreground',
  failed: 'bg-red-tint text-red',
  waiting: 'bg-divider text-faint',
}

const TEXT_STYLES: Record<StageState, string> = {
  done: 'text-ink',
  current: 'text-primary',
  failed: 'text-red',
  waiting: 'text-faint',
}

const STATE_LABELS: Record<StageState, string> = {
  done: 'done',
  current: 'in progress',
  failed: 'failed',
  waiting: 'not started',
}

const STATE_WORDS: Record<StageState, string> = {
  done: 'Done',
  current: 'In progress',
  failed: 'Failed',
  waiting: 'Waiting',
}

/** Checking → … → Scoring (AnalysisProgress.dc.html): the percentage, a bar and each step. */
export function StageTracker({ session }: { session: SessionDetail }) {
  const states = stageStates(session.status, session.current_stage)
  const queued = session.status === 'processing' && session.current_stage === 'queued'

  return (
    <div className="space-y-5">
      <div className="space-y-2.5">
        <div className="flex items-end justify-between gap-4">
          <span className="text-sm text-body-soft">
            {queued ? 'Waiting for the analysis worker…' : 'Progress'}
          </span>
          <span className="text-4xl leading-none font-extrabold text-primary tabular-nums">
            {session.progress_percent}%
          </span>
        </div>
        <Progress
          value={session.progress_percent}
          aria-label="Analysis progress"
          className="h-2.5"
        />
      </div>
      <ol className="flex flex-col" aria-label="Analysis stages">
        {PIPELINE_STAGES.map((stage, index) => {
          const state = states[stage.id]
          const Icon = ICONS[state]
          const seconds = session.stage_timings[stage.id]
          return (
            <li
              key={stage.id}
              className="flex items-center gap-3.5 border-b border-divider px-1 py-3 last:border-b-0"
              aria-current={state === 'current' ? 'step' : undefined}
            >
              <span
                className={cn(
                  'flex size-8 shrink-0 items-center justify-center rounded-full text-[13px] font-extrabold',
                  DOT_STYLES[state],
                )}
                aria-hidden="true"
              >
                {state === 'waiting' ? (
                  index + 1
                ) : (
                  <Icon
                    className={cn('size-4', state === 'current' && 'animate-spin')}
                    strokeWidth={2.4}
                  />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p className={cn('text-[15px] font-bold', TEXT_STYLES[state])}>
                  {stage.label}
                  <span className="sr-only"> — {STATE_LABELS[state]}</span>
                </p>
                <p className="text-[13px] text-muted-ink">
                  {stage.description}
                  {seconds !== undefined && state === 'done' && ` · ${seconds.toFixed(1)} s`}
                </p>
              </div>
              <span
                className={cn('shrink-0 text-[13px] font-bold', TEXT_STYLES[state])}
                aria-hidden="true"
              >
                {STATE_WORDS[state]}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
