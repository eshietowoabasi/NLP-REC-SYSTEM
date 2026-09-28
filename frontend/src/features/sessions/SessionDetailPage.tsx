import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ListChecks,
  Loader2,
  Play,
  RotateCcw,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/useAuth'
import { CATEGORY_BADGES, CATEGORY_LABELS } from '@/features/documents/labels'
import { ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type { SessionDetail } from '@/types/api'
import { formatPercent, formatWeight } from '@/features/review/labels'
import { SessionProgress } from '@/features/review/SessionProgress'

import { useRetrySession, useRunSession, useSession } from './api'
import { DeleteSessionDialog } from './DeleteSessionDialog'
import { SessionStatusBadge } from './SessionStatusBadge'
import { StageTracker } from './StageTracker'
import { PIPELINE_STAGES } from './stages'

export function SessionDetailPage() {
  const params = useParams()
  const id = Number(params.sessionId)
  const session = useSession(id)

  if (
    !Number.isInteger(id) ||
    (session.error instanceof ApiError && session.error.status === 404)
  ) {
    return <NotFoundPage />
  }
  if (session.isPending) {
    return (
      <div className="mx-auto max-w-5xl space-y-4" aria-label="Loading session">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }
  if (session.isError) {
    return (
      <Alert variant="destructive" className="mx-auto max-w-5xl">
        <AlertTitle>Could not load the session</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>{session.error.message}</p>
          <Button variant="outline" size="sm" onClick={() => void session.refetch()}>
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  return <SessionView session={session.data} />
}

function SessionView({ session }: { session: SessionDetail }) {
  const { canEdit } = useAuth()
  const navigate = useNavigate()
  const run = useRunSession()
  const retry = useRetrySession()
  const [deleting, setDeleting] = useState(false)
  const busy = run.isPending || retry.isPending
  const failedStage = PIPELINE_STAGES.find((s) => s.id === session.current_stage)?.label

  const start = (action: typeof run, label: string) =>
    action.mutate(session.id, {
      onSuccess: () => toast.success(`${label}; progress updates automatically.`),
      onError: (error) => toast.error(error.message),
    })

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <Link
        to="/sessions"
        className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Analyses
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h2 className="page-title break-words">{session.session_name}</h2>
          <div className="flex flex-wrap items-center gap-2 text-[13px] text-muted-ink">
            <SessionStatusBadge status={session.status} stage={session.current_stage} />
            <span>
              Created {formatDateTime(session.created_at)} by {session.created_by.full_name}
            </span>
          </div>
        </div>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            {session.status === 'pending' && (
              <Button onClick={() => start(run, 'Analysis started')} disabled={busy}>
                {run.isPending ? (
                  <Loader2 className="animate-spin" aria-hidden="true" />
                ) : (
                  <Play aria-hidden="true" />
                )}
                Run analysis
              </Button>
            )}
            {session.status !== 'processing' && (
              <Button variant="outline" onClick={() => setDeleting(true)} disabled={busy}>
                <Trash2 aria-hidden="true" /> Delete
              </Button>
            )}
          </div>
        )}
      </div>

      {session.status === 'failed' && (
        <Alert variant="destructive">
          <AlertCircle aria-hidden="true" />
          <AlertTitle>
            The analysis failed{failedStage ? ` at the ${failedStage} stage` : ''}
          </AlertTitle>
          <AlertDescription className="space-y-3">
            <p>{session.error_message}</p>
            {canEdit && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => start(retry, 'Retry started')}
                disabled={busy}
              >
                <RotateCcw aria-hidden="true" /> Retry
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {session.status === 'completed' && (
        <Alert variant="success">
          <CheckCircle2 aria-hidden="true" />
          <AlertTitle>Analysis complete</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>
              {session.recommendation_count} recommendation
              {session.recommendation_count === 1 ? '' : 's'} from {session.topic_count ?? 0} topic
              {session.topic_count === 1 ? '' : 's'} found in {session.document_count} document
              {session.document_count === 1 ? '' : 's'}. Finished{' '}
              {formatDateTime(session.completed_at)}.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" asChild>
                <Link to={`/sessions/${session.id}/recommendations`}>
                  <ListChecks aria-hidden="true" /> View recommendations
                </Link>
              </Button>
              <Button size="sm" variant="outline" asChild>
                <Link to={`/sessions/${session.id}/evidence`}>
                  <BarChart3 aria-hidden="true" /> View evidence
                </Link>
              </Button>
              <Button size="sm" variant="outline" asChild>
                <Link to={`/sessions/${session.id}/curriculum`}>
                  <BookOpen aria-hidden="true" /> Proposed courses
                </Link>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}
      {session.status === 'completed' && <SessionProgress sessionId={session.id} />}

      <div className="grid items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="rounded-3xl py-7">
          <CardHeader className="sm:px-8">
            {session.status === 'processing' && (
              <span className="text-xs font-extrabold tracking-[0.1em] text-primary uppercase">
                Working on it
              </span>
            )}
            <CardTitle className="text-xl">Analysis steps</CardTitle>
            <CardDescription>
              {session.status === 'pending'
                ? 'The analysis has not been run yet.'
                : session.status === 'processing'
                  ? 'Running. This page updates every few seconds.'
                  : 'Stages of the last run.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="sm:px-8">
            <StageTracker session={session} />
          </CardContent>
        </Card>
        <section
          aria-labelledby="whats-happening"
          className="flex flex-col gap-2.5 rounded-[20px] bg-ink px-6 py-[22px] text-white"
        >
          <h3 id="whats-happening" className="text-base font-extrabold">
            What&apos;s happening?
          </h3>
          <p className="text-sm leading-relaxed text-[#d9ccc2]">
            The system reads every advert and policy paper, spots the skills employers mention,
            groups similar needs into topics, then checks each topic against the NUC core so you
            only see what&apos;s new.
          </p>
        </section>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
              <dt className="text-muted-ink">Weights</dt>
              <dd className="font-bold tabular-nums">
                employer demand {formatWeight(session.parameter_config.weights.ner)} · how often it
                comes up {formatWeight(session.parameter_config.weights.topic)} · how new it is{' '}
                {formatWeight(session.parameter_config.weights.novelty)}
              </dd>
              <dt className="text-muted-ink">“May already be in NUC core”</dt>
              <dd className="font-bold tabular-nums">
                above {formatPercent(session.parameter_config.similarity_threshold)} similar
              </dd>
              <dt className="text-muted-ink">Max recommendations</dt>
              <dd className="font-bold">{session.parameter_config.max_recommendations}</dd>
              <dt className="text-muted-ink">NUC core</dt>
              <dd className="font-bold">
                {session.nuc_core_version?.version_label ?? 'Chosen when the session runs'}
              </dd>
              <dt className="text-muted-ink">Language models (advanced)</dt>
              <dd className="font-bold break-all">
                {session.parameter_config.sbert_model} · {session.parameter_config.spacy_model}
              </dd>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Documents ({session.documents.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="max-h-64 divide-y divide-divider overflow-y-auto text-sm">
              {session.documents.map((document) => (
                <li key={document.id} className="flex items-center justify-between gap-3 py-2">
                  <Link
                    to={`/documents/${document.id}`}
                    className="truncate font-semibold text-ink hover:text-primary"
                  >
                    {document.title}
                  </Link>
                  <Badge variant={CATEGORY_BADGES[document.source_category]} className="shrink-0">
                    {CATEGORY_LABELS[document.source_category]}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <DeleteSessionDialog
        session={deleting ? session : null}
        onClose={() => setDeleting(false)}
        onDeleted={() => navigate('/sessions', { replace: true })}
      />
    </div>
  )
}
