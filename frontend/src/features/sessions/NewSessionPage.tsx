import { zodResolver } from '@hookform/resolvers/zod'
import { AlertTriangle, ArrowLeft, ArrowRight, Check, Loader2, Play, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  Controller,
  useForm,
  useWatch,
  type Control,
  type FieldErrors,
  type UseFormRegister,
} from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { CATEGORY_LABELS, UPLOAD_CATEGORIES } from '@/features/documents/labels'
import { ApiError } from '@/lib/api'
import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { DocumentSummary, SessionDefaults, UploadCategory } from '@/types/api'

import { useCreateSession, useReadyDocuments, useSessionDefaults } from './api'

const WEIGHT_TOLERANCE = 0.001

function makeSchema(maxDocuments: number) {
  const weight = z.number({ error: 'Enter a number.' }).min(0, 'At least 0.').max(1, 'At most 1.')
  return z.object({
    session_name: z.string().trim().min(1, 'Enter a session name.').max(200),
    document_ids: z
      .array(z.number())
      .min(1, 'Select at least one document.')
      .max(maxDocuments, `Select at most ${maxDocuments} documents.`),
    weights: z
      .object({ ner: weight, topic: weight, novelty: weight })
      .refine((w) => Math.abs(w.ner + w.topic + w.novelty - 1) <= WEIGHT_TOLERANCE, {
        message: 'The three weights must add up to 1.00.',
      }),
    similarity_threshold: z
      .number({ error: 'Enter a number.' })
      .gt(0, 'Must be above 0.')
      .lt(1, 'Must be below 1.'),
    max_recommendations: z
      .number({ error: 'Enter a whole number.' })
      .int('Enter a whole number.')
      .min(1, 'At least 1.')
      .max(100, 'At most 100.'),
  })
}

type SessionForm = z.infer<ReturnType<typeof makeSchema>>

const STEPS = [
  { title: 'Name', fields: ['session_name'] },
  { title: 'Documents', fields: ['document_ids'] },
  { title: 'Settings', fields: ['weights', 'similarity_threshold', 'max_recommendations'] },
] as const

export function NewSessionPage() {
  const defaults = useSessionDefaults()

  if (defaults.isPending) {
    return (
      <div className="mx-auto max-w-4xl space-y-4" aria-label="Loading">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }
  if (defaults.isError) {
    return (
      <Alert variant="destructive" className="mx-auto max-w-4xl">
        <AlertTitle>Could not load the session settings</AlertTitle>
        <AlertDescription>{defaults.error.message}</AlertDescription>
      </Alert>
    )
  }
  return <NewSessionForm defaults={defaults.data} />
}

function NewSessionForm({ defaults }: { defaults: SessionDefaults }) {
  const navigate = useNavigate()
  const create = useCreateSession()
  const [step, setStep] = useState(0)
  const [formError, setFormError] = useState<string | null>(null)
  const schema = useMemo(() => makeSchema(defaults.max_documents), [defaults.max_documents])
  const initial: SessionForm = {
    session_name: '',
    document_ids: [],
    weights: defaults.parameters.weights,
    similarity_threshold: defaults.parameters.similarity_threshold,
    max_recommendations: defaults.parameters.max_recommendations,
  }
  const {
    register,
    control,
    handleSubmit,
    trigger,
    setValue,
    formState: { errors },
  } = useForm<SessionForm>({ resolver: zodResolver(schema), defaultValues: initial })
  const noNucCore = defaults.nuc_core_version === null

  const next = async () => {
    if (await trigger([...STEPS[step].fields])) setStep((s) => s + 1)
  }

  const submit = (run: boolean) =>
    handleSubmit((values) => {
      setFormError(null)
      create.mutate(
        {
          session_name: values.session_name,
          document_ids: values.document_ids,
          parameters: {
            weights: values.weights,
            similarity_threshold: values.similarity_threshold,
            max_recommendations: values.max_recommendations,
          },
          run,
        },
        {
          onSuccess: (session) => {
            toast.success(run ? 'Session created and started.' : 'Session created.')
            navigate(`/sessions/${session.id}`)
          },
          onError: (error) =>
            setFormError(
              error instanceof ApiError ? error.message : 'Could not create the session.',
            ),
        },
      )
    })

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/sessions">
          <ArrowLeft aria-hidden="true" /> Analysis sessions
        </Link>
      </Button>
      <div>
        <h2 className="text-xl font-semibold">New analysis session</h2>
        <p className="text-sm text-muted-foreground">
          Choose documents to analyse. The pipeline discovers themes in them and ranks candidate
          course topics against the NUC core.
        </p>
      </div>

      <ol className="flex flex-wrap gap-2" aria-label="Steps">
        {STEPS.map((item, index) => (
          <li
            key={item.title}
            aria-current={index === step ? 'step' : undefined}
            className={cn(
              'flex items-center gap-2 rounded-full border px-3 py-1 text-sm',
              index === step && 'border-primary bg-primary text-primary-foreground',
              index < step && 'text-muted-foreground',
            )}
          >
            <span className="tabular-nums">
              {index < step ? <Check className="size-3.5" aria-hidden="true" /> : index + 1}
            </span>
            {item.title}
          </li>
        ))}
      </ol>

      {noNucCore && (
        <Alert>
          <AlertTriangle aria-hidden="true" />
          <AlertTitle>No active NUC core reference</AlertTitle>
          <AlertDescription>
            You can create the session now, but it cannot run until an administrator uploads the NUC
            core reference.
          </AlertDescription>
        </Alert>
      )}
      {formError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={(event) => event.preventDefault()} noValidate>
        {step === 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Name the session</CardTitle>
              <CardDescription>For example “2026 review — job market and policy”.</CardDescription>
            </CardHeader>
            <CardContent>
              <Field data-invalid={!!errors.session_name} className="max-w-lg">
                <FieldLabel htmlFor="session_name">Session name</FieldLabel>
                <Input
                  id="session_name"
                  autoFocus
                  aria-invalid={!!errors.session_name}
                  {...register('session_name')}
                />
                <FieldError errors={[errors.session_name]} />
              </Field>
            </CardContent>
          </Card>
        )}

        {step === 1 && (
          <Controller
            control={control}
            name="document_ids"
            render={({ field, fieldState }) => (
              <DocumentPicker
                selected={field.value}
                onChange={field.onChange}
                maxDocuments={defaults.max_documents}
                error={fieldState.error?.message}
              />
            )}
          />
        )}

        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Scoring settings</CardTitle>
              <CardDescription>
                Pre-filled with the defaults. composite = w₁ × skill demand + w₂ × theme strength +
                w₃ × novelty.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup className="max-w-xl">
                <WeightsFields control={control} register={register} errors={errors} />
                <Field data-invalid={!!errors.similarity_threshold}>
                  <FieldLabel htmlFor="similarity_threshold">Duplicate threshold</FieldLabel>
                  <Input
                    id="similarity_threshold"
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="0.99"
                    className="w-32"
                    aria-invalid={!!errors.similarity_threshold}
                    {...register('similarity_threshold', { valueAsNumber: true })}
                  />
                  <FieldDescription>
                    A theme more similar than this to any NUC core passage is flagged as a Potential
                    Duplicate.
                  </FieldDescription>
                  <FieldError errors={[errors.similarity_threshold]} />
                </Field>
                <Field data-invalid={!!errors.max_recommendations}>
                  <FieldLabel htmlFor="max_recommendations">Maximum recommendations</FieldLabel>
                  <Input
                    id="max_recommendations"
                    type="number"
                    step="1"
                    min="1"
                    max="100"
                    className="w-32"
                    aria-invalid={!!errors.max_recommendations}
                    {...register('max_recommendations', { valueAsNumber: true })}
                  />
                  <FieldError errors={[errors.max_recommendations]} />
                </Field>
                <div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setValue('weights', defaults.parameters.weights, { shouldValidate: true })
                      setValue('similarity_threshold', defaults.parameters.similarity_threshold)
                      setValue('max_recommendations', defaults.parameters.max_recommendations)
                    }}
                  >
                    Reset to defaults
                  </Button>
                </div>
              </FieldGroup>
            </CardContent>
          </Card>
        )}

        <div className="mt-6 flex flex-wrap justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setStep((s) => s - 1)}
            disabled={step === 0 || create.isPending}
          >
            <ArrowLeft aria-hidden="true" /> Back
          </Button>
          {step < STEPS.length - 1 ? (
            <Button type="button" onClick={() => void next()}>
              Next <ArrowRight aria-hidden="true" />
            </Button>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={create.isPending}
                onClick={() => void submit(false)()}
              >
                Create
              </Button>
              <Button
                type="button"
                disabled={create.isPending || noNucCore}
                onClick={() => void submit(true)()}
              >
                {create.isPending ? (
                  <Loader2 className="animate-spin" aria-hidden="true" />
                ) : (
                  <Play aria-hidden="true" />
                )}
                Create &amp; run
              </Button>
            </div>
          )}
        </div>
      </form>
    </div>
  )
}

function WeightsFields({
  control,
  register,
  errors,
}: {
  control: Control<SessionForm>
  register: UseFormRegister<SessionForm>
  errors: FieldErrors<SessionForm>
}) {
  const weights = useWatch({ control, name: 'weights' })
  const sum = (weights.ner || 0) + (weights.topic || 0) + (weights.novelty || 0)
  const valid = Math.abs(sum - 1) <= WEIGHT_TOLERANCE
  const items = [
    { name: 'weights.ner', label: 'Skill demand (NER)', error: errors.weights?.ner },
    { name: 'weights.topic', label: 'Theme strength', error: errors.weights?.topic },
    { name: 'weights.novelty', label: 'Novelty', error: errors.weights?.novelty },
  ] as const

  return (
    <fieldset className="space-y-3">
      <legend className="mb-2 text-sm font-medium">Score weights</legend>
      <div className="grid gap-3 sm:grid-cols-3">
        {items.map((item) => (
          <Field key={item.name} data-invalid={!!item.error}>
            <FieldLabel htmlFor={item.name}>{item.label}</FieldLabel>
            <Input
              id={item.name}
              type="number"
              step="0.05"
              min="0"
              max="1"
              aria-invalid={!!item.error}
              {...register(item.name, { valueAsNumber: true })}
            />
            <FieldError errors={[item.error]} />
          </Field>
        ))}
      </div>
      <p
        role="status"
        className={cn(
          'text-sm',
          valid ? 'text-emerald-700 dark:text-emerald-400' : 'text-destructive',
        )}
      >
        Sum: {Number.isFinite(sum) ? sum.toFixed(2) : '—'}{' '}
        {valid ? '✓' : '— the weights must add up to 1.00'}
      </p>
      <FieldError errors={[errors.weights?.root, errors.weights as { message?: string }]} />
    </fieldset>
  )
}

function DocumentPicker({
  selected,
  onChange,
  maxDocuments,
  error,
}: {
  selected: number[]
  onChange: (ids: number[]) => void
  maxDocuments: number
  error?: string
}) {
  const documents = useReadyDocuments()
  const [category, setCategory] = useState<UploadCategory | null>(null)
  const [search, setSearch] = useState('')
  const chosen = new Set(selected)
  const needle = search.trim().toLowerCase()
  const shown = (documents.data ?? []).filter(
    (d: DocumentSummary) =>
      (category === null || d.source_category === category) &&
      (!needle || d.title.toLowerCase().includes(needle)),
  )
  const toggle = (id: number, on: boolean) =>
    onChange(on ? [...selected, id] : selected.filter((existing) => existing !== id))

  // Drop selections that are no longer ready (e.g. archived meanwhile).
  useEffect(() => {
    if (!documents.data) return
    const ready = new Set(documents.data.map((d) => d.id))
    if (selected.some((id) => !ready.has(id))) onChange(selected.filter((id) => ready.has(id)))
  }, [documents.data, selected, onChange])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Select documents</CardTitle>
        <CardDescription>
          Only documents that finished processing are listed. The NUC core is always used as the
          comparison baseline and is not selected here.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by category">
            <Button
              type="button"
              size="sm"
              variant={category === null ? 'default' : 'outline'}
              aria-pressed={category === null}
              onClick={() => setCategory(null)}
            >
              All
            </Button>
            {UPLOAD_CATEGORIES.map((value) => (
              <Button
                key={value}
                type="button"
                size="sm"
                variant={category === value ? 'default' : 'outline'}
                aria-pressed={category === value}
                onClick={() => setCategory(value)}
              >
                {CATEGORY_LABELS[value]}
              </Button>
            ))}
          </div>
          <p
            role="status"
            className={cn(
              'text-sm font-medium tabular-nums',
              selected.length > maxDocuments && 'text-destructive',
            )}
          >
            {selected.length} of {maxDocuments} selected
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-56 flex-1">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Label htmlFor="picker-search" className="sr-only">
              Search documents
            </Label>
            <Input
              id="picker-search"
              className="pl-8"
              placeholder="Search titles"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={shown.length === 0}
            onClick={() => onChange([...new Set([...selected, ...shown.map((d) => d.id)])])}
          >
            Select all shown
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={selected.length === 0}
            onClick={() => onChange([])}
          >
            Clear
          </Button>
        </div>

        {documents.isPending ? (
          <Skeleton className="h-48 w-full" />
        ) : documents.isError ? (
          <p className="text-sm text-destructive">{documents.error.message}</p>
        ) : documents.data.length === 0 ? (
          <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
            No ready documents.{' '}
            <Link to="/documents" className="underline">
              Upload documents
            </Link>{' '}
            first.
          </p>
        ) : (
          <ul
            className="max-h-96 divide-y overflow-y-auto rounded-md border"
            aria-label="Ready documents"
          >
            {shown.length === 0 && (
              <li className="p-4 text-sm text-muted-foreground">No documents match.</li>
            )}
            {shown.map((document) => {
              const id = `doc-${document.id}`
              return (
                <li key={document.id} className="flex items-center gap-3 px-3 py-2">
                  <Checkbox
                    id={id}
                    checked={chosen.has(document.id)}
                    onCheckedChange={(checked) => toggle(document.id, checked === true)}
                  />
                  <label htmlFor={id} className="min-w-0 flex-1 cursor-pointer">
                    <span className="block truncate text-sm font-medium">{document.title}</span>
                    <span className="block text-xs text-muted-foreground">
                      {CATEGORY_LABELS[document.source_category]} ·{' '}
                      {formatNumber(document.word_count)} words
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  )
}
