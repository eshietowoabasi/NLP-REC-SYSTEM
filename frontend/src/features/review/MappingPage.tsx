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
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
import { formatScore } from './labels'

const COURSE_CODE = /^([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)$/
const MAX_PREREQUISITES = 10
const MAX_OUTCOMES = 15

const mappingSchema = z.object({
  course_code: z
    .string()
    .trim()
    .regex(COURSE_CODE, 'Use a course code like â€œCSC 419â€ (2â€“4 letters, then 3 digits).'),
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

/** "csc419" â†’ "CSC 419", mirroring the server's normalisation. */
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
    <div className="mx-auto max-w-6xl space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={`/recommendations/${data.id}`}>
          <ArrowLeft aria-hidden="true" /> {data.topic_title}
        </Link>
      </Button>
      <h2 className="text-2xl font-semibold tracking-tight">
        {data.mapping ? 'Edit course mapping' : 'Map to a proposed course'}
      </h2>
      {data.planner_decision !== 'accepted' && !data.mapping ? (
        <EmptyPanel icon={X} title="Only accepted recommendations can be mapped">
          Accept this recommendation first, then map it to a course.{' '}
          <Link to={`/recommendations/${data.id}`} className="underline">
            Back to the recommendation
          </Link>
        </EmptyPanel>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
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
        toast.success(`${saved.course_code} saved to the proposed curriculum.`)
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
        toast.success(`${mapping.course_code} removed from the proposed curriculum.`)
        back()
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <Card className="self-start">
      <CardContent>
        <form onSubmit={onSubmit} noValidate aria-label="Course mapping">
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
                    variant="outline"
                    value={String(field.value)}
                    onValueChange={(value) => value && field.onChange(Number(value))}
                    aria-label="Credit units"
                    className="w-fit"
                  >
                    {[1, 2, 3].map((units) => (
                      <ToggleGroupItem
                        key={units}
                        value={String(units)}
                        className="w-12 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
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
                What students will be able to do after the course (1â€“{MAX_OUTCOMES}).
              </FieldDescription>
              <ol className="space-y-2">
                {outcomes.fields.map((item, index) => (
                  <li key={item.id} className="flex items-start gap-2">
                    <span className="mt-2 w-5 text-right text-sm text-muted-foreground tabular-nums">
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
                variant="outline"
                size="sm"
                className="w-fit"
                disabled={outcomes.fields.length >= MAX_OUTCOMES}
                onClick={() => outcomes.append({ text: '' })}
              >
                <Plus aria-hidden="true" /> Add outcome
              </Button>
            </FieldSet>

            <div className="flex flex-wrap justify-between gap-2">
              <div className="flex gap-2">
                <Button type="submit" disabled={save.isPending}>
                  {save.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
                  {mapping ? 'Save changes' : 'Add to curriculum'}
                </Button>
                <Button type="button" variant="outline" onClick={back}>
                  Cancel
                </Button>
              </div>
              {mapping && (
                <Button
                  type="button"
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => setConfirmDelete(true)}
                >
                  <Trash2 aria-hidden="true" /> Remove mapping
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
              The course leaves the proposed curriculum. The recommendation stays accepted.
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

/** Free-text chips: Enter or comma adds, the Ã— button or Backspace on empty removes. */
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
      <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border px-2 py-1.5 focus-within:ring-[3px] focus-within:ring-ring/50">
        <ul className="contents" aria-label={`${label} added`}>
          {values.map((value) => (
            <li key={value}>
              <Badge variant="secondary" className="gap-1 pr-1">
                {value}
                <button
                  type="button"
                  className="rounded-sm hover:bg-muted-foreground/20"
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
          className="min-w-24 flex-1 bg-transparent text-sm outline-none"
        />
      </div>
      <FieldDescription>{description}</FieldDescription>
      {message && <FieldError>{message}</FieldError>}
    </Field>
  )
}

function EvidencePanel({ recommendation }: { recommendation: RecommendationDetail }) {
  return (
    <Card className="self-start">
      <CardHeader>
        <CardTitle className="text-base">{recommendation.topic_title}</CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-2">
          <span className="tabular-nums">
            Rank {recommendation.rank} Â· score {formatScore(recommendation.composite_score)}
          </span>
          <OverlapBadge status={recommendation.overlap_status} />
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p className="text-muted-foreground">{recommendation.topic_description}</p>
        {recommendation.skills.length > 0 && (
          <div className="flex flex-wrap gap-1" aria-label="Skills">
            {recommendation.skills.map((skill) => (
              <Badge key={skill.name} variant="secondary">
                {skill.name}
              </Badge>
            ))}
          </div>
        )}
        <section aria-labelledby="mapping-evidence" className="space-y-2">
          <h3 id="mapping-evidence" className="font-medium">
            Evidence
          </h3>
          <ul className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
            {recommendation.evidence.map((item) => (
              <li key={item.passage_id} className="rounded-md bg-muted/50 p-2">
                <p className="text-xs text-muted-foreground">
                  {item.document.title}
                  {item.page_number != null && ` Â· p. ${item.page_number}`}
                </p>
                <p>{item.text}</p>
              </li>
            ))}
          </ul>
        </section>
      </CardContent>
    </Card>
  )
}
