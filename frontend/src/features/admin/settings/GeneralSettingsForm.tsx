import { zodResolver } from '@hookform/resolvers/zod'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { formatDateTime } from '@/lib/format'
import { applyServerErrors } from '@/lib/forms'
import { cn } from '@/lib/utils'
import type { SettingItem, SettingKey, SettingValues, SettingsUpdate } from '@/types/api'

import { useUpdateSettings } from './api'

const WEIGHT_TOLERANCE = 0.001
const MODEL_NAME = /^[A-Za-z0-9._/-]{1,128}$/

const int = (min: number, max: number) =>
  z
    .number({ error: 'Enter a whole number.' })
    .int('Enter a whole number.')
    .min(min, `At least ${min}.`)
    .max(max, `At most ${max}.`)
const weight = z.number({ error: 'Enter a number.' }).min(0, 'At least 0.').max(1, 'At most 1.')
const range = (min: number, max: number) =>
  z
    .object({ min: int(min, max), max: int(min, max) })
    .refine((r) => r.min <= r.max, { message: 'The minimum cannot exceed the maximum.' })

const schema = z.object({
  score_weights: z
    .object({ ner: weight, topic: weight, novelty: weight })
    .refine((w) => Math.abs(w.ner + w.topic + w.novelty - 1) <= WEIGHT_TOLERANCE, {
      message: 'The three weights must add up to 1.00.',
    }),
  similarity_threshold: z
    .number({ error: 'Enter a number.' })
    .gt(0, 'Must be above 0.')
    .lt(1, 'Must be below 1.'),
  max_recommendations: int(1, 100),
  min_topic_size: int(2, 100),
  evidence_per_recommendation: int(1, 20),
  max_documents_per_session: int(1, 200),
  credit_unit_allowance: z
    .string()
    .trim()
    .refine((v) => v === '' || (/^\d+$/.test(v) && +v >= 1 && +v <= 300), {
      message: 'Enter a whole number from 1 to 300, or leave empty.',
    }),
  passage_sentences: range(1, 10),
  passage_words: range(20, 500),
  sbert_model: z.string().trim().regex(MODEL_NAME, 'Letters, digits and . _ / - only.'),
  spacy_model: z.string().trim().regex(MODEL_NAME, 'Letters, digits and . _ / - only.'),
})
type FormValues = z.infer<typeof schema>

type ByKey = { [K in SettingKey]: SettingItem<K> }

function toForm(settings: ByKey): FormValues {
  const value = <K extends SettingKey>(key: K) => settings[key].value as SettingValues[K]
  return {
    score_weights: { ...value('score_weights') },
    similarity_threshold: value('similarity_threshold'),
    max_recommendations: value('max_recommendations'),
    min_topic_size: value('min_topic_size'),
    evidence_per_recommendation: value('evidence_per_recommendation'),
    max_documents_per_session: value('max_documents_per_session'),
    credit_unit_allowance:
      value('credit_unit_allowance') === null ? '' : String(value('credit_unit_allowance')),
    passage_sentences: { ...value('passage_sentences') },
    passage_words: { ...value('passage_words') },
    sbert_model: value('sbert_model'),
    spacy_model: value('spacy_model'),
  }
}

function fromForm(values: FormValues): SettingValues {
  return {
    ...values,
    credit_unit_allowance:
      values.credit_unit_allowance === '' ? null : Number(values.credit_unit_allowance),
  }
}

/** Only the settings whose value differs from the saved one. */
function diff(saved: ByKey, next: SettingValues): SettingsUpdate {
  const changes: Record<string, unknown> = {}
  for (const key of Object.keys(next) as SettingKey[]) {
    if (JSON.stringify(saved[key].value) !== JSON.stringify(next[key])) changes[key] = next[key]
  }
  return changes as SettingsUpdate
}

const FIELDS = [
  'score_weights',
  'similarity_threshold',
  'max_recommendations',
  'min_topic_size',
  'evidence_per_recommendation',
  'max_documents_per_session',
  'credit_unit_allowance',
  'passage_sentences',
  'passage_words',
  'sbert_model',
  'spacy_model',
] as const

export function GeneralSettingsForm({ settings }: { settings: SettingItem[] }) {
  const byKey = Object.fromEntries(settings.map((s) => [s.key, s])) as ByKey
  const update = useUpdateSettings()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isDirty },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: toForm(byKey) })
  const weights = useWatch({ control, name: 'score_weights' })
  const sbertModel = useWatch({ control, name: 'sbert_model' })
  const sum = (weights.ner || 0) + (weights.topic || 0) + (weights.novelty || 0)
  const sumOk = Math.abs(sum - 1) <= WEIGHT_TOLERANCE

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    const changes = diff(byKey, fromForm(values))
    if (Object.keys(changes).length === 0) {
      toast.info('Nothing to save.')
      return
    }
    update.mutate(changes, {
      onSuccess: (data) => {
        const saved = Object.fromEntries(data.settings.map((s) => [s.key, s])) as ByKey
        reset(toForm(saved))
        const count = data.changed?.length ?? 0
        toast.success(`Settings saved (${count} changed).`)
      },
      onError: (error) => setFormError(applyServerErrors(error, setError, FIELDS)),
    })
  })

  const hint = (key: SettingKey, text: string) => {
    const item = byKey[key]
    return (
      <FieldDescription>
        {text}
        {item.updated_by && (
          <span className="block text-xs">
            Changed by {item.updated_by.full_name}, {formatDateTime(item.updated_at)}
          </span>
        )}
      </FieldDescription>
    )
  }
  const number = (name: Parameters<typeof register>[0], step = '1') => ({
    type: 'number' as const,
    step,
    inputMode: step === '1' ? ('numeric' as const) : ('decimal' as const),
    ...register(name, { valueAsNumber: true }),
  })

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6" aria-label="General settings">
      {formError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Scoring defaults</CardTitle>
          <CardDescription>
            Pre-filled in the New Session form; planners can change them per session.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <fieldset className="space-y-3" aria-describedby="weights-sum">
              <legend className="text-sm font-medium">Composite score weights</legend>
              <div className="grid gap-4 sm:grid-cols-3">
                {(
                  [
                    ['ner', 'Skill demand (NER)'],
                    ['topic', 'Theme strength'],
                    ['novelty', 'Novelty'],
                  ] as const
                ).map(([key, label]) => (
                  <Field key={key} data-invalid={!!errors.score_weights?.[key]}>
                    <FieldLabel htmlFor={`weight-${key}`}>{label}</FieldLabel>
                    <Input
                      id={`weight-${key}`}
                      min={0}
                      max={1}
                      aria-invalid={!!errors.score_weights?.[key]}
                      {...number(`score_weights.${key}`, '0.01')}
                    />
                    <FieldError errors={[errors.score_weights?.[key]]} />
                  </Field>
                ))}
              </div>
              <p
                id="weights-sum"
                className={cn(
                  'text-sm tabular-nums',
                  sumOk ? 'text-muted-foreground' : 'font-medium text-destructive',
                )}
              >
                Sum: {sum.toFixed(2)} {sumOk ? '✓' : '— the weights must add up to 1.00'}
              </p>
              <FieldError errors={[errors.score_weights?.root ?? errors.score_weights]} />
            </fieldset>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field data-invalid={!!errors.similarity_threshold}>
                <FieldLabel htmlFor="similarity_threshold">Duplicate threshold</FieldLabel>
                <Input
                  id="similarity_threshold"
                  aria-invalid={!!errors.similarity_threshold}
                  {...number('similarity_threshold', '0.01')}
                />
                {hint(
                  'similarity_threshold',
                  'A theme more similar than this to the NUC core is marked a potential duplicate. Default 0.80.',
                )}
                <FieldError errors={[errors.similarity_threshold]} />
              </Field>
              <Field data-invalid={!!errors.max_recommendations}>
                <FieldLabel htmlFor="max_recommendations">Maximum recommendations</FieldLabel>
                <Input
                  id="max_recommendations"
                  aria-invalid={!!errors.max_recommendations}
                  {...number('max_recommendations')}
                />
                {hint('max_recommendations', 'Recommendations kept per session (1–100).')}
                <FieldError errors={[errors.max_recommendations]} />
              </Field>
            </div>
          </FieldGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Analysis and curriculum</CardTitle>
          <CardDescription>Apply to sessions created after saving.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field data-invalid={!!errors.min_topic_size}>
              <FieldLabel htmlFor="min_topic_size">Minimum theme size</FieldLabel>
              <Input
                id="min_topic_size"
                aria-invalid={!!errors.min_topic_size}
                {...number('min_topic_size')}
              />
              {hint('min_topic_size', 'Passages needed to form a theme (BERTopic). Default 5.')}
              <FieldError errors={[errors.min_topic_size]} />
            </Field>
            <Field data-invalid={!!errors.evidence_per_recommendation}>
              <FieldLabel htmlFor="evidence_per_recommendation">
                Evidence passages per recommendation
              </FieldLabel>
              <Input
                id="evidence_per_recommendation"
                aria-invalid={!!errors.evidence_per_recommendation}
                {...number('evidence_per_recommendation')}
              />
              {hint('evidence_per_recommendation', 'Default 8.')}
              <FieldError errors={[errors.evidence_per_recommendation]} />
            </Field>
            <Field data-invalid={!!errors.max_documents_per_session}>
              <FieldLabel htmlFor="max_documents_per_session">
                Maximum documents per session
              </FieldLabel>
              <Input
                id="max_documents_per_session"
                aria-invalid={!!errors.max_documents_per_session}
                {...number('max_documents_per_session')}
              />
              {hint('max_documents_per_session', 'Default 50.')}
              <FieldError errors={[errors.max_documents_per_session]} />
            </Field>
            <Field data-invalid={!!errors.credit_unit_allowance}>
              <FieldLabel htmlFor="credit_unit_allowance">30% credit-unit allowance</FieldLabel>
              <Input
                id="credit_unit_allowance"
                inputMode="numeric"
                placeholder="Not set"
                aria-invalid={!!errors.credit_unit_allowance}
                {...register('credit_unit_allowance')}
              />
              {hint(
                'credit_unit_allowance',
                'Credit units available for the institution-designed 30%. Leave empty until the department confirms the figure.',
              )}
              <FieldError errors={[errors.credit_unit_allowance]} />
            </Field>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Document processing</CardTitle>
          <CardDescription>
            Applied when documents are parsed, so they affect documents uploaded after saving.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <div className="grid gap-4 sm:grid-cols-2">
              {(
                [
                  ['passage_sentences', 'Sentences per passage', 'Default 3 to 5.'],
                  ['passage_words', 'Words per passage', 'Default 100 to 200.'],
                ] as const
              ).map(([key, label, text]) => (
                <fieldset key={key} className="space-y-2">
                  <legend className="text-sm font-medium">{label}</legend>
                  <div className="flex items-center gap-2">
                    <Input
                      aria-label={`${label}: minimum`}
                      className="w-24"
                      aria-invalid={!!errors[key]?.min}
                      {...number(`${key}.min`)}
                    />
                    <span className="text-sm text-muted-foreground">to</span>
                    <Input
                      aria-label={`${label}: maximum`}
                      className="w-24"
                      aria-invalid={!!errors[key]?.max}
                      {...number(`${key}.max`)}
                    />
                  </div>
                  {hint(key, text)}
                  <FieldError
                    errors={[errors[key]?.min, errors[key]?.max, errors[key]?.root ?? errors[key]]}
                  />
                </fieldset>
              ))}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field data-invalid={!!errors.sbert_model}>
                <FieldLabel htmlFor="sbert_model">Embedding model (SBERT)</FieldLabel>
                <Input
                  id="sbert_model"
                  autoComplete="off"
                  aria-invalid={!!errors.sbert_model}
                  {...register('sbert_model')}
                />
                {hint('sbert_model', 'sentence-transformers model name. Default all-MiniLM-L6-v2.')}
                <FieldError errors={[errors.sbert_model]} />
              </Field>
              <Field data-invalid={!!errors.spacy_model}>
                <FieldLabel htmlFor="spacy_model">spaCy pipeline</FieldLabel>
                <Input
                  id="spacy_model"
                  autoComplete="off"
                  aria-invalid={!!errors.spacy_model}
                  {...register('spacy_model')}
                />
                {hint('spacy_model', 'Must be installed on the server. Default en_core_web_sm.')}
                <FieldError errors={[errors.spacy_model]} />
              </Field>
            </div>
            {sbertModel.trim() !== byKey.sbert_model.value && (
              <Alert>
                <AlertTriangle aria-hidden="true" className="text-amber-600" />
                <AlertTitle>Changing the embedding model</AlertTitle>
                <AlertDescription>
                  Documents embedded with different models cannot be analysed together. After
                  saving, re-upload the existing documents and the NUC core so that they all use the
                  new model; sessions mixing models are refused with an explanation.
                </AlertDescription>
              </Alert>
            )}
          </FieldGroup>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button type="submit" disabled={update.isPending || !isDirty}>
          {update.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Save settings
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={!isDirty}
          onClick={() => reset(toForm(byKey))}
        >
          Discard changes
        </Button>
      </div>
    </form>
  )
}
