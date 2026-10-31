import { zodResolver } from '@hookform/resolvers/zod'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Play,
  Search,
  Upload,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
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
import { FilterChip } from '@/components/shared/FilterChip'
import { PageHeader } from '@/components/shared/PageHeader'
import { useAuth } from '@/features/auth/useAuth'
import { useDocuments } from '@/features/documents/api'
import {
  CATEGORY_LABELS,
  documentMeta,
  IN_PROGRESS,
  UPLOAD_CATEGORIES,
} from '@/features/documents/labels'
import { UploadDialog } from '@/features/documents/UploadDialog'
import { useProgrammeBenchmarks } from '@/features/programmes/api'
import { ApiError } from '@/lib/api'
import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { DocumentSummary, SessionDefaults, UploadCategory } from '@/types/api'
import { formatWeight } from '@/features/review/labels'

import { useCreateSession, useReadyDocuments, useSessionDefaults } from './api'

const WEIGHT_TOLERANCE = 0.001

function makeSchema(maxDocuments: number) {
  const weight = z.number({ error: 'Enter a number.' }).min(0, 'At least 0.').max(1, 'At most 1.')
  return z.object({
    programme_id: z.number().int().min(0),
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
  { title: 'Programme & name', fields: ['programme_id', 'session_name'] },
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
    programme_id:
      defaults.default_programme_id ??
      defaults.programmes?.[0]?.id ??
      0,
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
  } = useForm<SessionForm>({
    resolver: zodResolver(schema),
    defaultValues: initial,
  })

  const selectedProgrammeId = useWatch({
    control,
    name: 'programme_id',
  })

  const selectedBenchmark =
    useProgrammeBenchmarks(selectedProgrammeId)

  const benchmarkLoading =
    selectedProgrammeId > 0 &&
    selectedBenchmark.isPending

  const noBenchmark =
    selectedProgrammeId > 0
      ? selectedBenchmark.isError ||
        (!selectedBenchmark.isPending &&
          selectedBenchmark.data?.active == null)
      : defaults.nuc_core_version === null

  const next = async () => {
    if (await trigger([...STEPS[step].fields])) setStep((s) => s + 1)
  }

  const submit = (run: boolean) =>
    handleSubmit((values) => {
      setFormError(null)
      create.mutate(
        {
          session_name: values.session_name,
          ...(values.programme_id > 0
            ? { programme_id: values.programme_id }
            : {}),
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
    <div className="mx-auto max-w-6xl space-y-5">
      <Link
        to="/sessions"
        className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Analyses
      </Link>
      <PageHeader
        title="New analysis session"
        description="Choose a programme and the evidence to analyse. SkillBridge discovers the topics they discuss, compares them with that programme's curriculum benchmark and ranks possible curriculum additions."
      />

      <ol className="flex flex-wrap items-center gap-3" aria-label="Steps">
        {STEPS.map((item, index) => (
          <li
            key={item.title}
            aria-current={index === step ? 'step' : undefined}
            className={cn(
              'flex items-center gap-2.5 text-sm font-semibold text-faint',
              index === step && 'font-extrabold text-primary',
              index < step && 'font-bold text-green',
            )}
          >
            {index > 0 && (
              <span className="h-0.5 w-10 bg-input-line sm:w-[60px]" aria-hidden="true" />
            )}
            <span
              className={cn(
                'flex size-[30px] items-center justify-center rounded-full bg-divider text-muted-ink tabular-nums',
                index === step && 'bg-primary text-primary-foreground',
                index < step && 'bg-green-tint text-green',
              )}
            >
              {index < step ? (
                <Check className="size-4" strokeWidth={2.6} aria-hidden="true" />
              ) : (
                index + 1
              )}
            </span>
            {item.title}
          </li>
        ))}
      </ol>

      {noBenchmark && (
        <Alert variant="warning">
          <AlertTriangle aria-hidden="true" />
          <AlertTitle>No active curriculum benchmark</AlertTitle>
          <AlertDescription>
            You can create the analysis now, but it cannot run until an administrator uploads a
            benchmark for the selected programme.
          </AlertDescription>
        </Alert>
      )}
      {formError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="grid items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_340px]">
        <form onSubmit={(event) => event.preventDefault()} noValidate>
          {step === 0 && (
            <Card className="rounded-[20px]">
              <CardHeader>
                <CardTitle>Name the session</CardTitle>
                <CardDescription>
                  For example “2026 review — job market and policy”.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {(defaults.programmes?.length ?? 0) > 0 && (
                  <Field className="max-w-lg">
                    <FieldLabel htmlFor="programme_id">
                      Programme
                    </FieldLabel>

                    <select
                      id="programme_id"
                      className="h-11 w-full rounded-xl border border-input bg-white px-3.5 text-sm font-medium text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
                      {...register('programme_id', {
                        valueAsNumber: true,
                      })}
                    >
                      {defaults.programmes?.map(
                        (programme) => (
                          <option
                            key={programme.id}
                            value={programme.id}
                          >
                            {programme.name}
                            {programme.discipline_code
                              ? ` (${programme.discipline_code})`
                              : ''}
                          </option>
                        ),
                      )}
                    </select>

                    <FieldDescription>
                      SkillBridge uses this programme's
                      curriculum benchmark for comparison.
                    </FieldDescription>
                  </Field>
                )}

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
                  Pre-filled with the usual values. The score adds up employer demand, how often the
                  topic comes up and how new it is, weighted as below.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup className="max-w-xl">
                  <WeightsFields control={control} register={register} errors={errors} />
                  <Field data-invalid={!!errors.similarity_threshold}>
                    <FieldLabel htmlFor="similarity_threshold">
                      “May already be in benchmark” above
                    </FieldLabel>
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
                      A topic more similar than this to a benchmark course is marked “May already be
                      in benchmark”. 0.80 means 80% similar.
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
                  disabled={create.isPending || noBenchmark || benchmarkLoading}
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
        <AnalysisSummary control={control} defaults={defaults} />
      </div>
    </div>
  )
}

/** "Your analysis": what has been chosen so far (NewAnalysis.dc.html). */
function AnalysisSummary({
  control,
  defaults,
}: {
  control: Control<SessionForm>
  defaults: SessionDefaults
}) {
  const [name, documentIds, programmeId] =
    useWatch({
      control,
      name: [
        'session_name',
        'document_ids',
        'programme_id',
      ],
    })

  const benchmark =
    useProgrammeBenchmarks(programmeId)

  const programme =
    defaults.programmes?.find(
      (item) => item.id === programmeId,
    )

  return (
    <aside
      aria-labelledby="analysis-summary"
      className="flex flex-col gap-3.5 rounded-[20px] border border-line bg-white px-6 py-[22px]"
    >
      <h3 id="analysis-summary" className="card-title">
        Your analysis
      </h3>
      <dl className="flex flex-col gap-3 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-body-soft">Name</dt>
          <dd className="truncate font-bold text-ink">{name.trim() || '—'}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-body-soft">
            Programme
          </dt>
          <dd className="truncate font-bold text-ink">
            {programme?.name ?? '—'}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-body-soft">Documents selected</dt>
          <dd className="font-bold text-ink tabular-nums">{documentIds.length}</dd>
        </div>
      </dl>
      <div className="flex flex-col gap-1.5 rounded-xl bg-teal-tint px-3.5 py-3 text-teal-ink">
        <span className="text-[13px] font-extrabold">Compared against</span>
        <span className="text-[13px]">
          {benchmark.data?.active?.version_label ??
            (programmeId > 0
              ? 'No benchmark yet'
              : defaults.nuc_core_version?.version_label ??
                'No benchmark yet')}
        </span>
      </div>
    </aside>
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
    { key: 'ner', name: 'weights.ner', label: 'Employer demand', error: errors.weights?.ner },
    {
      key: 'topic',
      name: 'weights.topic',
      label: 'How often it comes up',
      error: errors.weights?.topic,
    },
    {
      key: 'novelty',
      name: 'weights.novelty',
      label: 'How new it is',
      error: errors.weights?.novelty,
    },
  ] as const

  return (
    <fieldset className="space-y-3">
      <legend className="mb-2 text-sm font-extrabold">
        What matters most when ranking topics?
      </legend>
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
            <FieldDescription>
              {Number.isFinite(weights[item.key]) ? formatWeight(weights[item.key]) : '—'}
            </FieldDescription>
            <FieldError errors={[item.error]} />
          </Field>
        ))}
      </div>
      <p
        role="status"
        className={cn('text-sm', valid ? 'font-bold text-green' : 'font-bold text-destructive')}
      >
        Total: {Number.isFinite(sum) ? `${Math.round(sum * 100)}%` : '—'}{' '}
        {valid ? '✓' : '— the weights must add up to 100% (1.00)'}
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
  const { canEdit } = useAuth()
  const [uploadOpen, setUploadOpen] = useState(false)
  // Newest library documents: shows uploads that are still being processed.
  const library = useDocuments({ per_page: 100 })
  const processing = (library.data?.items ?? []).filter((d) =>
    IN_PROGRESS.includes(d.processing_status),
  )
  const documents = useReadyDocuments(processing.length > 0 ? 3000 : false)
  // Polling stops when the last upload is ready, possibly just before the ready list would
  // have picked it up, so fetch the list once more at that moment.
  const wasProcessing = useRef(false)
  const refetchReady = documents.refetch
  useEffect(() => {
    if (wasProcessing.current && processing.length === 0) void refetchReady()
    wasProcessing.current = processing.length > 0
  }, [processing.length, refetchReady])
  // Documents uploaded from this page are ticked automatically as soon as they are ready.
  const knownIds = useRef<Set<number> | null>(null)
  const openUpload = () => {
    knownIds.current = new Set((documents.data ?? []).map((d) => d.id))
    setUploadOpen(true)
  }
  useEffect(() => {
    const known = knownIds.current
    if (!documents.data || known === null) return
    const fresh = documents.data.filter((d) => !known.has(d.id)).map((d) => d.id)
    if (fresh.length === 0) return
    fresh.forEach((id) => known.add(id))
    const room = Math.max(0, maxDocuments - selected.length)
    const added = fresh.filter((id) => !selected.includes(id)).slice(0, room)
    if (added.length > 0) onChange([...selected, ...added])
  }, [documents.data, selected, onChange, maxDocuments])
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
          Choose the documents to analyse, or upload new ones. Only documents that have finished
          processing can be selected. The NUC core is always used as the comparison baseline.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by category">
            <FilterChip active={category === null} onClick={() => setCategory(null)}>
              All
            </FilterChip>
            {UPLOAD_CATEGORIES.map((value) => (
              <FilterChip
                key={value}
                active={category === value}
                onClick={() => setCategory(value)}
              >
                {CATEGORY_LABELS[value]}
              </FilterChip>
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
          {canEdit && (
            <Button type="button" size="sm" onClick={openUpload}>
              <Upload aria-hidden="true" />
              Upload documents
            </Button>
          )}
        </div>

        {processing.length > 0 && (
          <p
            role="status"
            className="flex items-center gap-2 rounded-2xl bg-sand px-4 py-2.5 text-sm text-body-soft"
          >
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            {processing.length === 1
              ? '1 document is still being processed. It will appear below when it is ready.'
              : `${processing.length} documents are still being processed. They will appear below when they are ready.`}
          </p>
        )}

        {documents.isPending ? (
          <Skeleton className="h-48 w-full" />
        ) : documents.isError ? (
          <p className="text-sm text-destructive">{documents.error.message}</p>
        ) : documents.data.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-input-line p-6 text-center text-sm text-body-soft">
            No ready documents yet.{' '}
            {canEdit ? (
              <>
                <button type="button" className="font-bold underline" onClick={openUpload}>
                  Upload documents
                </button>{' '}
                to get started.
              </>
            ) : (
              <>
                See the{' '}
                <Link to="/documents" className="underline">
                  Documents
                </Link>{' '}
                page.
              </>
            )}
          </p>
        ) : (
          <ul
            className="max-h-96 divide-y divide-divider overflow-y-auto rounded-2xl border border-line"
            aria-label="Ready documents"
          >
            {shown.length === 0 && (
              <li className="p-4 text-sm text-muted-ink">No documents match.</li>
            )}
            {shown.map((document) => {
              const id = `doc-${document.id}`
              return (
                <li
                  key={document.id}
                  className="flex items-center gap-3.5 px-4 py-2.5 hover:bg-sand"
                >
                  <Checkbox
                    id={id}
                    checked={chosen.has(document.id)}
                    onCheckedChange={(checked) => toggle(document.id, checked === true)}
                  />
                  <label htmlFor={id} className="min-w-0 flex-1 cursor-pointer">
                    <span className="block truncate text-sm font-bold text-ink">
                      {document.title}
                    </span>
                    <span className="block text-xs text-muted-ink">
                      {[documentMeta(document), `${formatNumber(document.word_count)} words`]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </Card>
  )
}
