import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, BookOpen, Loader2, Pencil } from 'lucide-react'
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
import { useAuth } from '@/features/auth/useAuth'
import { DOCUMENT_TYPE, monthYear, shorten } from '@/features/documents/labels'
import { ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { applyServerErrors } from '@/lib/forms'
import { cn } from '@/lib/utils'
import { DocumentRef } from '@/components/shared/DocumentRef'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type { Evidence, RecommendationDetail } from '@/types/api'

import { useDecide, useEditRecommendation, useRecommendation } from './api'
import {
  DecisionBadge,
  ErrorPanel,
  KeywordsLine,
  LoadingBlock,
  OverlapBadge,
  ScoreContribution,
} from './components'
import { DecisionControl } from './DecisionControl'
import {
  contributionPoints,
  formatDecimal,
  formatPercent,
  SCORE_PARTS,
  SKILL_LABELS,
  toPoints,
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
    <div className="mx-auto max-w-6xl space-y-4">
      <Link
        to={`/sessions/${recommendation.session_id}/recommendations`}
        className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Back to suggested topics ·{' '}
        {recommendation.session.session_name}
      </Link>

      <div className="grid items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-4">
          <TitleSection recommendation={recommendation} />
          <EvidenceCard evidence={recommendation.evidence} />
          <OverlapCard recommendation={recommendation} />
        </div>
        <aside className="space-y-4" aria-label="Score and decision">
          <ScoreCard recommendation={recommendation} />
          <DecisionCard recommendation={recommendation} />
          <ScoreMeaningCard recommendation={recommendation} />
          <TermsCard recommendation={recommendation} />
        </aside>
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
    <section className="flex flex-col gap-3 rounded-[20px] border border-line bg-white px-6 py-[22px] sm:px-[26px]">
      {editing ? (
        <EditForm recommendation={recommendation} onDone={() => setEditing(false)} />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <p className="text-[13px] font-bold text-muted-ink">
                Recommendation #{recommendation.rank}
              </p>
              <OverlapBadge status={recommendation.overlap_status} />
              <DecisionBadge decision={recommendation.planner_decision} />
            </div>
            {canEdit && (
              <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                <Pencil aria-hidden="true" /> Edit title and description
              </Button>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <h2 className="page-title break-words">{recommendation.topic_title}</h2>
            {recommendation.topic_title !== recommendation.auto_title && (
              <p className="text-xs text-muted-ink">Generated title: {recommendation.auto_title}</p>
            )}
            <KeywordsLine keywords={recommendation.keywords} />
          </div>
          <Description text={recommendation.topic_description} />
          <ExampleQuote evidence={recommendation.evidence[0]} />
        </>
      )}
    </section>
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
    <div>
      <div>
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
            <p className="text-xs text-muted-ink">
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
      </div>
    </div>
  )
}

const WHY = 'Why this is recommended:'

/** The description, with its "Why this is recommended:" opening in bold. */
function Description({ text }: { text: string }) {
  const why = text.startsWith(WHY)
  return (
    <p className="max-w-3xl text-[15px] leading-relaxed text-[#2e2620]">
      {why ? (
        <>
          <strong className="font-bold text-ink">{WHY}</strong>
          {text.slice(WHY.length)}
        </>
      ) : (
        text
      )}
    </p>
  )
}

/** "Example from a job advert (Title, MyJobMag, Sep 2026): “…”", as an amber quote block. */
function ExampleQuote({ evidence }: { evidence: Evidence | undefined }) {
  if (!evidence) return null
  const { document } = evidence
  const kind = DOCUMENT_TYPE[document.source_category] ?? 'document'
  const details = [document.source, monthYear(document.published_on)].filter(Boolean).join(', ')
  return (
    <figure className="flex max-w-3xl flex-col gap-1.5 rounded-r-[14px] border-l-4 border-amber bg-amber-tint px-4 py-3.5">
      <figcaption className="text-xs font-bold text-muted-ink">
        Example from {/^[aeiou]/i.test(kind) ? 'an' : 'a'} {kind} ({document.title}
        {details && `, ${details}`}):
      </figcaption>
      <blockquote className="text-sm leading-relaxed text-[#2e2620] italic">
        “{shorten(evidence.text, 400)}”
      </blockquote>
    </figure>
  )
}

/* -------------------------------------------------------------------- scores */

function ScoreCard({ recommendation }: { recommendation: RecommendationDetail }) {
  const weights = recommendation.session.weights
  const [showCalculation, setShowCalculation] = useState(false)
  const terms = SCORE_PARTS.map((part) => ({
    ...part,
    weight: weights[part.key],
    value: recommendation[part.field],
  }))
  const points = contributionPoints(
    terms.map((t) => t.weight * t.value),
    recommendation.composite_score,
  )
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Why it ranks #{recommendation.rank}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ScoreContribution recommendation={recommendation} weights={weights} detailed />
        <p className="rounded-xl bg-sand px-3.5 py-3 text-[13px] leading-relaxed text-body tabular-nums">
          {terms.map((term, index) => (
            <span key={term.key}>
              {index > 0 && ' + '}
              <strong className="text-ink">{points[index]}</strong>
              <span className="text-muted-ink"> ({term.label.toLowerCase()})</span>
            </span>
          ))}{' '}
          = <strong className="text-ink">{toPoints(recommendation.composite_score)} points</strong>{' '}
          out of 100
        </p>
        <div className="space-y-2 border-t border-divider pt-3">
          <Button
            type="button"
            variant="link"
            size="sm"
            className="h-8 text-[13px]"
            aria-expanded={showCalculation}
            aria-controls="score-calculation"
            onClick={() => setShowCalculation((shown) => !shown)}
          >
            {showCalculation ? 'Hide calculation' : 'Show calculation'}
          </Button>
          {showCalculation && (
            <div id="score-calculation" className="space-y-1.5">
              <p
                className="rounded-xl bg-sand p-3 font-mono text-xs leading-relaxed text-ink tabular-nums"
                aria-label="Composite score formula"
              >
                {terms.map((term, index) => (
                  <span key={term.key}>
                    {index > 0 && ' + '}
                    {formatDecimal(term.weight)} × {formatDecimal(term.value)}
                    <span className="text-muted-ink"> ({term.technical})</span>
                  </span>
                ))}{' '}
                = <strong>{formatDecimal(recommendation.composite_score)}</strong>
              </p>
              <p className="text-xs text-muted-ink">
                The exact calculation on the 0–1 scale; the points above are these values × 100,
                rounded so that the parts add up to the total. Highest similarity to the NUC core:{' '}
                {recommendation.max_similarity.toFixed(3)}.
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

/** What the three scores mean, in plain words. */
function ScoreMeaningCard({ recommendation }: { recommendation: RecommendationDetail }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>What the scores mean</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs leading-relaxed text-muted-ink">
          The score out of 100 adds up three scores, each out of 100 compared with this
          session&apos;s other topics and weighted by how much it counts.
        </p>
        <dl className="grid gap-3 text-xs text-muted-ink">
          <div>
            <dt className="font-bold text-ink">Employer demand</dt>
            <dd>
              How many documents ask for the skills that belong to this topic. Skills that every
              topic mentions count less.
            </dd>
          </div>
          <div>
            <dt className="font-bold text-ink">How often it comes up</dt>
            <dd>
              How much of the material is about this topic (each document counts the same), and how
              clearly its extracts belong to it.
            </dd>
          </div>
          <div>
            <dt className="font-bold text-ink">How new it is</dt>
            <dd>
              How different it is from the closest NUC core{' '}
              {recommendation.closest_nuc_course ? 'course' : 'extract'}. High means the NUC core
              does not teach it yet.
            </dd>
          </div>
          <p>High = 70 or more, Medium = 40–69, Low = below 40.</p>
        </dl>
      </CardContent>
    </Card>
  )
}

/* ------------------------------------------------------------------- overlap */

function OverlapCard({ recommendation }: { recommendation: RecommendationDetail }) {
  const nuc = recommendation.closest_nuc_passage
  const course = recommendation.closest_nuc_course
  const threshold = recommendation.session.similarity_threshold
  const top = recommendation.evidence[0]
  const duplicate = recommendation.overlap_status === 'Potential Duplicate'
  const verdict = duplicate
    ? 'this topic may already be taught in the NUC core.'
    : 'the NUC core does not seem to cover it.'
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-teal-tint">
            <BookOpen className="size-5 text-teal" strokeWidth={1.8} aria-hidden="true" />
          </span>
          Comparison with the NUC core
        </CardTitle>
        <CardDescription>
          {course ? (
            <>
              We compared this topic with every NUC core course. A topic more than{' '}
              {formatPercent(threshold)} similar to a course may already be in the NUC core. Here,{' '}
              {verdict}
            </>
          ) : (
            <>
              {formatPercent(recommendation.max_similarity)} similar to the closest NUC core
              extract; above {formatPercent(threshold)} a topic may already be in the NUC core.
              Here, {verdict}
            </>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        {course && (
          <p
            className={cn(
              'rounded-[14px] bg-sand px-4 py-3 text-sm md:col-span-2',
              duplicate && 'bg-amber-tint',
            )}
          >
            <span className="font-bold tabular-nums">
              {formatPercent(recommendation.max_similarity)} similar
            </span>{' '}
            to the closest NUC course: <span className="font-bold">{course.code}</span> –{' '}
            {course.title}
            {(course.units != null || course.page_number != null) && (
              <span className="text-muted-ink">
                {' · '}
                {[
                  course.units != null && `${course.units} units`,
                  course.page_number != null && `p. ${course.page_number}`,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            )}
          </p>
        )}
        <section
          aria-labelledby="overlap-theme"
          className="space-y-1.5 rounded-[14px] border border-line p-4"
        >
          <h3 id="overlap-theme" className="text-sm font-extrabold">
            Typical extract from this topic
          </h3>
          {top ? (
            <>
              <DocumentRef
                document={top.document}
                titleClassName="text-xs"
                className="[&>span:last-child]:text-[11px]"
              />
              <p className="text-sm leading-relaxed">{top.text}</p>
            </>
          ) : (
            <p className="text-sm text-muted-ink">No evidence extracts stored.</p>
          )}
        </section>
        <section
          aria-labelledby="overlap-nuc"
          className={
            duplicate && !course
              ? 'space-y-1.5 rounded-[14px] bg-amber-tint p-4'
              : 'space-y-1.5 rounded-[14px] border border-line p-4'
          }
        >
          <h3 id="overlap-nuc" className="text-sm font-extrabold">
            Closest extract in the NUC core
          </h3>
          {nuc ? (
            <>
              <p className="text-xs text-muted-ink">
                {nuc.version_label ?? nuc.document_title}
                {nuc.page_number != null && ` · p. ${nuc.page_number}`}
              </p>
              <p className="text-sm leading-relaxed">{nuc.text}</p>
            </>
          ) : (
            <p className="text-sm text-muted-ink">This NUC core extract is no longer available.</p>
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
          The {evidence.length} extracts that best represent this topic, grouped by document.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {groups.length === 0 && (
          <p className="text-sm text-muted-ink">No evidence extracts stored.</p>
        )}
        {groups.map(({ document, passages }) => (
          <section
            key={document.id}
            aria-label={document.label ?? document.title}
            className="space-y-2"
          >
            <DocumentRef document={document} link />
            <ul className="space-y-2">
              {passages.map((passage) => (
                <li key={passage.passage_id} className="rounded-[14px] bg-sand px-4 py-3.5">
                  <p className="mb-1 text-xs font-bold text-muted-ink tabular-nums">
                    {passage.page_number != null
                      ? `Page ${passage.page_number}`
                      : `Extract ${passage.position + 1}`}{' '}
                    · {formatPercent(passage.relevance_score)} relevant
                  </p>
                  <p className="text-sm leading-relaxed text-[#2e2620] italic">“{passage.text}”</p>
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
    <Card size="sm">
      <CardHeader>
        <CardTitle>Skills and keywords</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <section className="space-y-2" aria-labelledby="skills-heading">
          <h3 id="skills-heading" className="section-label">
            Skills
          </h3>
          {recommendation.skills.length === 0 ? (
            <p className="text-sm text-muted-ink">No known skills were found in this topic.</p>
          ) : (
            <ul className="divide-y divide-divider text-sm">
              {recommendation.skills.map((skill) => (
                <li key={skill.name} className="flex items-baseline justify-between gap-2 py-1.5">
                  <span>
                    {skill.name}{' '}
                    <span className="text-xs text-muted-ink">{SKILL_LABELS[skill.label]}</span>
                  </span>
                  <span className="text-xs text-muted-ink tabular-nums">
                    {skill.document_frequency} docs
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="space-y-2" aria-labelledby="keywords-heading">
          <h3 id="keywords-heading" className="section-label">
            Keywords
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {recommendation.keywords.map((keyword) => (
              <Badge key={keyword.term} variant="secondary" className="font-semibold">
                {keyword.label ?? keyword.term}
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
  const saved = recommendation.planner_notes ?? ''
  const [notes, setNotes] = useState(saved)
  const mapping = recommendation.mapping

  const saveNotes = () =>
    decide.mutate(
      { id: recommendation.id, decision: recommendation.planner_decision, notes: notes.trim() },
      {
        onSuccess: () => toast.success('Notes saved.'),
        onError: (error) => toast.error(error.message),
      },
    )

  return (
    <Card size="sm" className="border-2 border-primary shadow-selected">
      <CardHeader>
        <CardTitle>Decision</CardTitle>
        {recommendation.decided_by && (
          <CardDescription>
            {recommendation.decided_by.full_name}, {formatDateTime(recommendation.decided_at)}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <DecisionControl recommendation={recommendation} layout="panel" />
        {mapping && (
          <p className="text-xs text-muted-ink">
            {mapping.credit_units} credit unit{mapping.credit_units === 1 ? '' : 's'} ·{' '}
            {mapping.learning_outcomes.length} learning outcome
            {mapping.learning_outcomes.length === 1 ? '' : 's'} ·{' '}
            <Link
              to={`/sessions/${recommendation.session_id}/curriculum`}
              className="font-bold text-primary hover:underline"
            >
              View the proposed courses
            </Link>
          </p>
        )}
        {canEdit ? (
          <div className="grid gap-1.5 border-t border-divider pt-4">
            <Label htmlFor="decision-notes">Notes</Label>
            <Textarea
              id="decision-notes"
              rows={4}
              maxLength={2000}
              placeholder="Reasons, conditions or follow-up (optional)"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
            <Button
              variant="outline"
              size="sm"
              className="justify-self-start"
              onClick={saveNotes}
              disabled={notes.trim() === saved || decide.isPending}
            >
              {decide.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
              Save notes
            </Button>
          </div>
        ) : (
          recommendation.planner_notes && (
            <p className="border-t border-divider pt-4 text-sm">{recommendation.planner_notes}</p>
          )
        )}
      </CardContent>
    </Card>
  )
}
