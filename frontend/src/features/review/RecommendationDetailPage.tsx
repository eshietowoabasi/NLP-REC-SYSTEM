import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, BookOpenCheck, Loader2, Pencil } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useAuth } from '@/features/auth/useAuth'
import { CATEGORY_LABELS } from '@/features/documents/labels'
import { ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { applyServerErrors } from '@/lib/forms'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type { Evidence, PlannerDecision, RecommendationDetail } from '@/types/api'

import { useDecide, useEditRecommendation, useRecommendation } from './api'
import { DecisionBadge, ErrorPanel, LoadingBlock, OverlapBadge, ScoreMeter } from './components'
import {
  DECISION_ACTIONS,
  DECISION_ICONS,
  DECISIONS,
  formatScore,
  SCORE_PARTS,
  SKILL_LABELS,
} from './labels'

export function RecommendationDetailPage() {
  const id = Number(useParams().recommendationId)
  const recommendation = useRecommendation(id)

  if (
    !Number.isInteger(id) ||
    (recommendation.error instanceof ApiError && recommendation.error.status === 404)
  ) {
    return <NotFoundPage />
  }
  if (recommendation.isPending) return <LoadingBlock label="Loading recommendation" />
  if (recommendation.isError) {
    return (
      <ErrorPanel
        title="Could not load the recommendation"
        error={recommendation.error}
        onRetry={() => void recommendation.refetch()}
      />
    )
  }
  return <RecommendationView recommendation={recommendation.data} />
}

function RecommendationView({ recommendation }: { recommendation: RecommendationDetail }) {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={`/sessions/${recommendation.session_id}/recommendations`}>
          <ArrowLeft aria-hidden="true" /> Recommendations · {recommendation.session.session_name}
        </Link>
      </Button>

      <TitleSection recommendation={recommendation} />

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="min-w-0 space-y-6">
          <ScoreCard recommendation={recommendation} />
          <OverlapCard recommendation={recommendation} />
          <EvidenceCard evidence={recommendation.evidence} />
        </div>
        <div className="space-y-6">
          <DecisionCard recommendation={recommendation} />
          <TermsCard recommendation={recommendation} />
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------- title & text */

const editSchema = z.object({
  topic_title: z.string().trim().min(1, 'Enter a title.').max(255, 'At most 255 characters.'),
  topic_description: z
    .string()
    .trim()
    .min(1, 'Enter a description.')
    .max(5000, 'At most 5,000 characters.'),
})
type EditValues = z.infer<typeof editSchema>

function TitleSection({ recommendation }: { recommendation: RecommendationDetail }) {
  const { canEdit } = useAuth()
  const [editing, setEditing] = useState(false)

  return (
    <div className="space-y-3">
      {editing ? (
        <EditForm recommendation={recommendation} onDone={() => setEditing(false)} />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-2">
              <p className="text-sm text-muted-foreground">
                Rank {recommendation.rank} · theme {recommendation.topic_id}
              </p>
              <h2 className="text-2xl font-semibold tracking-tight break-words">
                {recommendation.topic_title}
              </h2>
              {recommendation.topic_title !== recommendation.auto_title && (
                <p className="text-sm text-muted-foreground">
                  Generated title: {recommendation.auto_title}
                </p>
              )}
            </div>
            {canEdit && (
              <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                <Pencil aria-hidden="true" /> Edit title and description
              </Button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            <OverlapBadge status={recommendation.overlap_status} />
            <DecisionBadge decision={recommendation.planner_decision} />
          </div>
          <p className="max-w-3xl text-sm leading-relaxed">{recommendation.topic_description}</p>
        </>
      )}
    </div>
  )
}

function EditForm({
  recommendation,
  onDone,
}: {
  recommendation: RecommendationDetail
  onDone: () => void
}) {
  const edit = useEditRecommendation(recommendation.id)
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      topic_title: recommendation.topic_title,
      topic_description: recommendation.topic_description,
    },
  })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    edit.mutate(values, {
      onSuccess: () => {
        toast.success('Recommendation updated.')
        onDone()
      },
      onError: (error) =>
        setFormError(applyServerErrors(error, setError, ['topic_title', 'topic_description'])),
    })
  })

  return (
    <Card>
      <CardContent>
        <form onSubmit={onSubmit} noValidate>
          <FieldGroup>
            {formError && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <Field data-invalid={!!errors.topic_title}>
              <FieldLabel htmlFor="topic_title">Title</FieldLabel>
              <Input
                id="topic_title"
                aria-invalid={!!errors.topic_title}
                {...register('topic_title')}
              />
              <FieldError errors={[errors.topic_title]} />
            </Field>
            <Field data-invalid={!!errors.topic_description}>
              <FieldLabel htmlFor="topic_description">Description</FieldLabel>
              <Textarea
                id="topic_description"
                rows={5}
                aria-invalid={!!errors.topic_description}
                {...register('topic_description')}
              />
              <FieldError errors={[errors.topic_description]} />
            </Field>
            <p className="text-xs text-muted-foreground">
              The generated title ({recommendation.auto_title}) is kept for reference.
            </p>
            <div className="flex gap-2">
              <Button type="submit" disabled={edit.isPending}>
                {edit.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
                Save
              </Button>
              <Button type="button" variant="outline" onClick={onDone}>
                Cancel
              </Button>
            </div>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}

/* -------------------------------------------------------------------- scores */

function ScoreCard({ recommendation }: { recommendation: RecommendationDetail }) {
  const weights = recommendation.session.weights
  const terms = SCORE_PARTS.map((part) => ({
    ...part,
    weight: weights[part.key],
    value: recommendation[part.field],
  }))
  return (
    <Card>
      <CardHeader>
        <CardTitle>Why it ranks #{recommendation.rank}</CardTitle>
        <CardDescription>
          Composite score = weighted sum of three scores, each scaled to 0–1 across this
          session&apos;s themes.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p
          className="rounded-md bg-muted/60 p-3 font-mono text-sm leading-relaxed tabular-nums"
          aria-label="Composite score formula"
        >
          {terms.map((term, index) => (
            <span key={term.key}>
              {index > 0 && ' + '}
              {term.weight.toFixed(2)} × {formatScore(term.value)}
              <span className="text-muted-foreground"> ({term.label.toLowerCase()})</span>
            </span>
          ))}{' '}
          = <strong>{formatScore(recommendation.composite_score)}</strong>
        </p>
        <div className="space-y-1.5">
          <ScoreMeter label="Composite" value={recommendation.composite_score} emphasis />
          {terms.map((term) => (
            <ScoreMeter key={term.key} label={term.label} value={term.value} />
          ))}
        </div>
        <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
          <div>
            <dt className="font-medium text-foreground">Skill demand</dt>
            <dd>How many documents mention the theme&apos;s top skills.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Theme strength</dt>
            <dd>Share of passages in the theme × how confidently they belong to it.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Novelty</dt>
            <dd>1 − the highest similarity to any NUC core passage.</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  )
}

/* ------------------------------------------------------------------- overlap */

function OverlapCard({ recommendation }: { recommendation: RecommendationDetail }) {
  const nuc = recommendation.closest_nuc_passage
  const threshold = recommendation.session.similarity_threshold
  const top = recommendation.evidence[0]
  const duplicate = recommendation.overlap_status === 'Potential Duplicate'
  return (
    <Card>
      <CardHeader>
        <CardTitle>Overlap with the NUC core</CardTitle>
        <CardDescription>
          Highest similarity {formatScore(recommendation.max_similarity)} against a threshold of{' '}
          {formatScore(threshold)}:{' '}
          {duplicate
            ? 'this theme may repeat content already in the NUC core.'
            : 'no significant overlap with the NUC core.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <section aria-labelledby="overlap-theme" className="space-y-1.5 rounded-md border p-3">
          <h3 id="overlap-theme" className="text-sm font-semibold">
            Most representative passage
          </h3>
          {top ? (
            <>
              <p className="text-xs text-muted-foreground">
                {top.document.title}
                {top.page_number != null && ` · p. ${top.page_number}`}
              </p>
              <p className="text-sm">{top.text}</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No evidence passages stored.</p>
          )}
        </section>
        <section
          aria-labelledby="overlap-nuc"
          className={
            duplicate
              ? 'space-y-1.5 rounded-md border border-amber-300 bg-amber-50/60 p-3 dark:border-amber-800 dark:bg-amber-950/40'
              : 'space-y-1.5 rounded-md border p-3'
          }
        >
          <h3 id="overlap-nuc" className="text-sm font-semibold">
            Closest NUC core passage
          </h3>
          {nuc ? (
            <>
              <p className="text-xs text-muted-foreground">
                {nuc.version_label ?? nuc.document_title}
                {nuc.page_number != null && ` · p. ${nuc.page_number}`}
              </p>
              <p className="text-sm">{nuc.text}</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              The NUC core passage is no longer available.
            </p>
          )}
        </section>
      </CardContent>
    </Card>
  )
}

/* ------------------------------------------------------------------ evidence */

function groupByDocument(evidence: Evidence[]) {
  const groups = new Map<number, { document: Evidence['document']; passages: Evidence[] }>()
  for (const item of evidence) {
    const group = groups.get(item.document.id) ?? { document: item.document, passages: [] }
    group.passages.push(item)
    groups.set(item.document.id, group)
  }
  return [...groups.values()]
}

function EvidenceCard({ evidence }: { evidence: Evidence[] }) {
  const groups = groupByDocument(evidence)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence</CardTitle>
        <CardDescription>
          The {evidence.length} passages closest to the centre of this theme, grouped by document.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {groups.length === 0 && (
          <p className="text-sm text-muted-foreground">No evidence passages stored.</p>
        )}
        {groups.map(({ document, passages }) => (
          <section key={document.id} aria-label={document.title} className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Link
                to={`/documents/${document.id}`}
                className="text-sm font-semibold hover:underline"
              >
                {document.title}
              </Link>
              <Badge variant="secondary">{CATEGORY_LABELS[document.source_category]}</Badge>
            </div>
            <ul className="space-y-2">
              {passages.map((passage) => (
                <li key={passage.passage_id} className="rounded-md border-l-2 bg-muted/40 p-3">
                  <p className="mb-1 text-xs text-muted-foreground tabular-nums">
                    {passage.page_number != null
                      ? `Page ${passage.page_number}`
                      : `Passage ${passage.position + 1}`}{' '}
                    · relevance {formatScore(passage.relevance_score)}
                  </p>
                  <p className="text-sm">{passage.text}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </CardContent>
    </Card>
  )
}

/* --------------------------------------------------------- skills & keywords */

function TermsCard({ recommendation }: { recommendation: RecommendationDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Skills and keywords</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <section className="space-y-2" aria-labelledby="skills-heading">
          <h3 id="skills-heading" className="text-sm font-medium">
            Skills
          </h3>
          {recommendation.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recognised skills in this theme.</p>
          ) : (
            <ul className="divide-y text-sm">
              {recommendation.skills.map((skill) => (
                <li key={skill.name} className="flex items-baseline justify-between gap-2 py-1">
                  <span>
                    {skill.name}{' '}
                    <span className="text-xs text-muted-foreground">
                      {SKILL_LABELS[skill.label]}
                    </span>
                  </span>
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {skill.document_frequency} docs
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="space-y-2" aria-labelledby="keywords-heading">
          <h3 id="keywords-heading" className="text-sm font-medium">
            Keywords
          </h3>
          <div className="flex flex-wrap gap-1">
            {recommendation.keywords.map((keyword) => (
              <Badge key={keyword.term} variant="secondary">
                {keyword.term}
              </Badge>
            ))}
          </div>
        </section>
      </CardContent>
    </Card>
  )
}

/* ------------------------------------------------------------------ decision */

function DecisionCard({ recommendation }: { recommendation: RecommendationDetail }) {
  const { canEdit } = useAuth()
  const decide = useDecide()
  const [decision, setDecision] = useState<PlannerDecision | null>(recommendation.planner_decision)
  const [notes, setNotes] = useState(recommendation.planner_notes ?? '')
  const mapped = recommendation.mapping !== null
  const changed =
    decision !== recommendation.planner_decision ||
    notes.trim() !== (recommendation.planner_notes ?? '')

  const save = () =>
    decide.mutate(
      { id: recommendation.id, decision, notes: notes.trim() || null },
      {
        onSuccess: () => toast.success('Decision saved.'),
        onError: (error) => toast.error(error.message),
      },
    )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision</CardTitle>
        {recommendation.decided_by && (
          <CardDescription>
            {recommendation.decided_by.full_name}, {formatDateTime(recommendation.decided_at)}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {canEdit ? (
          <>
            <ToggleGroup
              type="single"
              variant="outline"
              value={decision ?? ''}
              onValueChange={(value) => setDecision((value || null) as PlannerDecision | null)}
              aria-label="Decision"
              className="w-full"
              disabled={mapped}
            >
              {DECISIONS.map((value) => {
                const Icon = DECISION_ICONS[value]
                return (
                  <ToggleGroupItem key={value} value={value} className="flex-1">
                    <Icon aria-hidden="true" /> {DECISION_ACTIONS[value]}
                  </ToggleGroupItem>
                )
              })}
            </ToggleGroup>
            {mapped && (
              <p className="text-xs text-muted-foreground">
                Mapped to a course: remove the mapping to change the decision.
              </p>
            )}
            <div className="grid gap-1.5">
              <Label htmlFor="decision-notes">Notes</Label>
              <Textarea
                id="decision-notes"
                rows={4}
                maxLength={2000}
                placeholder="Reasons, conditions or follow-up (optional)"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </div>
            <Button onClick={save} disabled={!changed || decide.isPending} className="w-full">
              {decide.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
              Save decision
            </Button>
          </>
        ) : (
          <div className="space-y-2 text-sm">
            <DecisionBadge decision={recommendation.planner_decision} />
            {recommendation.planner_notes && <p>{recommendation.planner_notes}</p>}
          </div>
        )}

        <MappingSummary recommendation={recommendation} />
      </CardContent>
    </Card>
  )
}

function MappingSummary({ recommendation }: { recommendation: RecommendationDetail }) {
  const { canEdit } = useAuth()
  const mapping = recommendation.mapping
  const mappingPath = `/recommendations/${recommendation.id}/mapping`

  if (mapping) {
    return (
      <div className="space-y-2 rounded-md border p-3 text-sm">
        <p className="flex items-center gap-1.5 font-medium">
          <BookOpenCheck className="size-4" aria-hidden="true" /> {mapping.course_code}:{' '}
          {mapping.course_title}
        </p>
        <p className="text-muted-foreground">
          {mapping.credit_units} credit unit{mapping.credit_units === 1 ? '' : 's'} ·{' '}
          {mapping.learning_outcomes.length} learning outcome
          {mapping.learning_outcomes.length === 1 ? '' : 's'}
        </p>
        {canEdit ? (
          <Button variant="outline" size="sm" asChild>
            <Link to={mappingPath}>Edit course mapping</Link>
          </Button>
        ) : (
          <Link
            to={`/sessions/${recommendation.session_id}/curriculum`}
            className="text-sm underline-offset-4 hover:underline"
          >
            View the proposed curriculum
          </Link>
        )}
      </div>
    )
  }
  if (!canEdit) return null
  if (recommendation.planner_decision !== 'accepted') {
    return (
      <p className="text-xs text-muted-foreground">
        Accept the recommendation to map it to a proposed course.
      </p>
    )
  }
  return (
    <Button asChild variant="secondary" className="w-full">
      <Link to={mappingPath}>
        <BookOpenCheck aria-hidden="true" /> Map to course
      </Link>
    </Button>
  )
}
