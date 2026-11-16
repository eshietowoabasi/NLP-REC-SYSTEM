import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, Loader2, Plus, Trash2, X } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'
import { Controller, useFieldArray, useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { DocumentRef } from '@/components/shared/DocumentRef'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { ApiError } from '@/lib/api'
import { applyServerErrors } from '@/lib/forms'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type { MappingRequest, RecommendationDetail } from '@/types/api'

import { useDeleteMapping, useRecommendation, useSaveMapping } from './api'
import { EmptyPanel, ErrorPanel, LoadingBlock, OverlapBadge } from './components'
import { formatOutOf100 } from './labels'

const COURSE_CODE = /^([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)$/
const MAX_PREREQUISITES = 10
const MAX_OUTCOMES = 15

const mappingSchema = z.object({
  course_code: z
    .string()
    .trim()
    .regex(COURSE_CODE, 'Use a course code like “CSC 419” (2–4 letters, then 3 digits).'),
  course_title: z.string().trim().min(1, 'Enter the course title.').max(255),
  credit_units: z.union([z.literal(1), z.literal(2), z.literal(3)], {
    error: 'Choose 1, 2 or 3 credit units.',
  }),
  prerequisites: z.array(z.string()).max(MAX_PREREQUISITES),
  learning_outcomes: z
    .array(z.object({ text: z.string().trim().max(500, 'At most 500 characters.') }))
    .refine((items) => items.some((item) => item.text), 'Add at least one learning outcome.')
    .refine(
      (items) => {
        const texts = items.map((item) => item.text.toLowerCase()).filter(Boolean)
        return new Set(texts).size === texts.length
      },
      { message: 'Remove duplicate learning outcomes.' },
    ),
})
type MappingValues = z.infer<typeof mappingSchema>

/** "csc419" → "CSC 419", mirroring the server's normalisation. */
function normaliseCode(value: string) {
  const match = COURSE_CODE.exec(value.trim().replace(/\s+/g, ' '))
  return match ? `${match[1].toUpperCase()} ${match[2].toUpperCase()}` : value.trim()
}

export function MappingPage() {
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
  const data = recommendation.data
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <Link
        to={`/recommendations/${data.id}`}
        className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> {data.topic_title}
      </Link>
      <h2 className="page-title">{data.mapping ? 'Edit course' : 'Design course'}</h2>
      {data.planner_decision !== 'accepted' && !data.mapping ? (
        <EmptyPanel icon={X} title="Only accepted recommendations can have a course">
          Accept this recommendation first, then design its course.{' '}
          <Link to={`/recommendations/${data.id}`} className="underline">
            Back to the recommendation
          </Link>
        </EmptyPanel>
      ) : (
        <div className="grid items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_320px]">
          <MappingForm recommendation={data} />
          <EvidencePanel recommendation={data} />
        </div>
      )}
    </div>
  )
}

function MappingForm({ recommendation }: { recommendation: RecommendationDetail }) {
  const navigate = useNavigate()
  const mapping = recommendation.mapping
  const save = useSaveMapping(recommendation.id, mapping?.id ?? null)
  const remove = useDeleteMapping(recommendation.id)
  const [formError, setFormError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<MappingValues>({
    resolver: zodResolver(mappingSchema),
    defaultValues: {
      course_code: mapping?.course_code ?? '',
      course_title: mapping?.course_title ?? recommendation.topic_title,
      credit_units: mapping?.credit_units ?? 3,
      prerequisites: mapping?.prerequisites ?? [],
      learning_outcomes: (mapping?.learning_outcomes.length ? mapping.learning_outcomes : ['']).map(
        (text) => ({ text }),
      ),
    },
  })
  const outcomes = useFieldArray({ control, name: 'learning_outcomes' })
  const back = () => navigate(`/recommendations/${recommendation.id}`)

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    const request: MappingRequest = {
      course_code: normaliseCode(values.course_code),
      course_title: values.course_title,
      credit_units: values.credit_units,
      prerequisites: values.prerequisites,
      learning_outcomes: values.learning_outcomes.map((o) => o.text.trim()).filter(Boolean),
    }
    save.mutate(request, {
      onSuccess: (saved) => {
        toast.success(`${saved.course_code} saved to the proposed courses.`)
        back()
      },
      onError: (error) =>
        setFormError(
          applyServerErrors(error, setError, [
            'course_code',
            'course_title',
            'credit_units',
            'prerequisites',
            'learning_outcomes',
          ]),
        ),
    })
  })

  const deleteMapping = () => {
    if (!mapping) return
    remove.mutate(mapping.id, {
      onSuccess: () => {
        toast.success(`${mapping.course_code} removed from the proposed courses.`)
        back()
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <Card className="self-start rounded-[22px] py-6">
      <CardContent className="sm:px-7">
        <form onSubmit={onSubmit} noValidate aria-label="Course design">
          <FieldGroup>
            {formError && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <div className="grid gap-4 sm:grid-cols-[10rem_1fr]">
              <Field data-invalid={!!errors.course_code}>
                <FieldLabel htmlFor="course_code">Course code</FieldLabel>
                <Input
                  id="course_code"
                  placeholder="CSC 419"
                  autoComplete="off"
                  aria-invalid={!!errors.course_code}
                  {...register('course_code')}
                />
                <FieldError errors={[errors.course_code]} />
              </Field>
              <Field data-invalid={!!errors.course_title}>
                <FieldLabel htmlFor="course_title">Course title</FieldLabel>
                <Input
                  id="course_title"
                  aria-invalid={!!errors.course_title}
                  {...register('course_title')}
                />
                <FieldError errors={[errors.course_title]} />
              </Field>
            </div>

            <FieldSet data-invalid={!!errors.credit_units}>
              <FieldLegend variant="label">Credit units</FieldLegend>
              <Controller
                control={control}
                name="credit_units"
                render={({ field }) => (
                  <ToggleGroup
                    type="single"
                    variant="segment"
                    spacing={1.5}
                    value={String(field.value)}
                    onValueChange={(value) => value && field.onChange(Number(value))}
                    aria-label="Credit units"
                    className="w-fit rounded-xl bg-sand-deep p-1"
                  >
                    {[1, 2, 3].map((units) => (
                      <ToggleGroupItem
                        key={units}
                        value={String(units)}
                        className="w-[52px]"
                        aria-label={`${units} credit unit${units === 1 ? '' : 's'}`}
                      >
                        {units}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                )}
              />
              <FieldError errors={[errors.credit_units]} />
            </FieldSet>

            <Controller
              control={control}
              name="prerequisites"
              render={({ field }) => (
                <TagInput
                  id="prerequisites"
                  label="Prerequisites"
                  description={`Course codes or titles; press Enter to add (up to ${MAX_PREREQUISITES}).`}
                  values={field.value}
                  onChange={field.onChange}
                  max={MAX_PREREQUISITES}
                  error={errors.prerequisites?.message}
                />
              )}
            />

            <FieldSet data-invalid={!!errors.learning_outcomes}>
              <FieldLegend variant="label">Learning outcomes</FieldLegend>
              <FieldDescription>
                What students will be able to do after the course (1–{MAX_OUTCOMES}).
              </FieldDescription>
              <ol className="space-y-2">
                {outcomes.fields.map((item, index) => (
                  <li key={item.id} className="flex items-start gap-2">
                    <span className="mt-3 w-6 text-right text-[13px] font-extrabold text-faint tabular-nums">
                      {index + 1}.
                    </span>
                    <div className="flex-1">
                      <Input
                        aria-label={`Learning outcome ${index + 1}`}
                        aria-invalid={!!errors.learning_outcomes?.[index]?.text}
                        {...register(`learning_outcomes.${index}.text`)}
                      />
                      <FieldError errors={[errors.learning_outcomes?.[index]?.text]} />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove learning outcome ${index + 1}`}
                      disabled={outcomes.fields.length === 1}
                      onClick={() => outcomes.remove(index)}
                    >
                      <Trash2 aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ol>
              <FieldError errors={[errors.learning_outcomes?.root ?? errors.learning_outcomes]} />
              <Button
                type="button"
                variant="link"
                className="w-fit text-[13px]"
                disabled={outcomes.fields.length >= MAX_OUTCOMES}
                onClick={() => outcomes.append({ text: '' })}
              >
                <Plus aria-hidden="true" /> Add outcome
              </Button>
            </FieldSet>

            <div className="flex flex-wrap-reverse justify-between gap-2.5 border-t border-divider pt-4">
              <div className="flex gap-2.5">
                <Button type="submit" disabled={save.isPending}>
                  {save.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
                  {mapping ? 'Save changes' : 'Save course'}
                </Button>
                <Button type="button" variant="outline" onClick={back}>
                  Cancel
                </Button>
              </div>
              {mapping && (
                <Button type="button" variant="destructive" onClick={() => setConfirmDelete(true)}>
                  <Trash2 aria-hidden="true" /> Remove course
                </Button>
              )}
            </div>
          </FieldGroup>
        </form>
      </CardContent>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {mapping?.course_code}?</AlertDialogTitle>
            <AlertDialogDescription>
              The course leaves the proposed courses. The recommendation stays accepted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={deleteMapping}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}

/** Free-text chips: Enter or comma adds, the × button or Backspace on empty removes. */
function TagInput({
  id,
  label,
  description,
  values,
  onChange,
  max,
  error,
}: {
  id: string
  label: string
  description: string
  values: string[]
  onChange: (values: string[]) => void
  max: number
  error?: string
}) {
  const [draft, setDraft] = useState('')
  const [hint, setHint] = useState<string | null>(null)

  const add = () => {
    const value = draft.trim().replace(/\s+/g, ' ')
    if (!value) return
    if (values.some((v) => v.toLowerCase() === value.toLowerCase())) {
      setHint(`${value} is already listed.`)
    } else if (values.length >= max) {
      setHint(`At most ${max}.`)
    } else {
      onChange([...values, value])
      setHint(null)
    }
    setDraft('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      add()
    } else if (event.key === 'Backspace' && !draft && values.length) {
      onChange(values.slice(0, -1))
    }
  }

  const message = error ?? hint
  return (
    <Field data-invalid={!!error}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <div className="flex min-h-12 flex-wrap items-center gap-1.5 rounded-xl border border-input bg-white px-2 py-1.5 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/25">
        <ul className="contents" aria-label={`${label} added`}>
          {values.map((value) => (
            <li key={value}>
              <Badge variant="secondary" className="gap-1 rounded-lg py-1.5 pr-1.5 text-[13px]">
                {value}
                <button
                  type="button"
                  className="cursor-pointer rounded-sm hover:bg-divider"
                  aria-label={`Remove ${value}`}
                  onClick={() => onChange(values.filter((v) => v !== value))}
                >
                  <X className="size-3" aria-hidden="true" />
                </button>
              </Badge>
            </li>
          ))}
        </ul>
        <input
          id={id}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          onBlur={add}
          placeholder={values.length ? '' : 'e.g. CSC 301'}
          className="h-8 min-w-24 flex-1 bg-transparent px-1.5 text-sm outline-none placeholder:text-faint"
        />
      </div>
      <FieldDescription>{description}</FieldDescription>
      {message && <FieldError>{message}</FieldError>}
    </Field>
  )
}

/** Beside the form: what the topic is about and the evidence behind it. */
function EvidencePanel({ recommendation }: { recommendation: RecommendationDetail }) {
  return (
    <div className="flex flex-col gap-4 self-start">
      <section
        aria-label="The topic"
        className="flex flex-col gap-2.5 rounded-[20px] bg-ink px-[22px] py-5 text-white"
      >
        <span className="text-xs font-extrabold tracking-[0.1em] text-amber uppercase">
          Rank {recommendation.rank} · Score {formatOutOf100(recommendation.composite_score)}
        </span>
        <h3 className="text-base font-extrabold">{recommendation.topic_title}</h3>
        <div>
          <OverlapBadge status={recommendation.overlap_status} />
        </div>
        <p className="text-[13px] leading-normal text-[#d9ccc2]">
          {recommendation.topic_description}
        </p>
        {recommendation.skills.length > 0 && (
          <ul className="flex flex-wrap gap-1.5" aria-label="Skills">
            {recommendation.skills.map((skill) => (
              <li
                key={skill.name}
                className="rounded-full bg-white/12 px-2.5 py-[5px] text-xs font-semibold"
              >
                {skill.name}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section
        aria-labelledby="mapping-evidence"
        className="flex flex-col gap-3 rounded-[20px] border border-line bg-white px-5 py-[18px]"
      >
        <h3 id="mapping-evidence" className="text-sm font-extrabold">
          Evidence
        </h3>
        <ul className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
          {recommendation.evidence.map((item) => (
            <li key={item.passage_id} className="space-y-1 rounded-[14px] bg-sand px-3.5 py-3">
              <DocumentRef document={item.document} titleClassName="text-xs" />
              <p className="text-[13px] leading-relaxed">{item.text}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
