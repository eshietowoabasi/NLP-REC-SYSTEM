import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { applyServerErrors } from '@/lib/forms'
import type { Recommendation } from '@/types/api'

import { useSaveMapping } from './api'
import { COURSE_CODE, COURSE_CODE_MESSAGE, normaliseCode } from './courseCode'
import { designCoursePath, toPoints } from './labels'

const quickSchema = z.object({
  course_code: z.string().trim().regex(COURSE_CODE, COURSE_CODE_MESSAGE),
  course_title: z.string().trim().min(1, 'Enter the course title.').max(255),
  credit_units: z.union([z.literal(1), z.literal(2), z.literal(3)], {
    error: 'Choose 1, 2 or 3 units.',
  }),
  outcome: z
    .string()
    .trim()
    .min(1, 'Say what students will be able to do.')
    .max(500, 'At most 500 characters.'),
})
type QuickValues = z.infer<typeof quickSchema>

/**
 * One accepted topic as a row of the Design courses step: code, title, units and one learning
 * outcome, saved in one click. Prerequisites and more outcomes are added on the full form.
 */
export function QuickCourseForm({ recommendation }: { recommendation: Recommendation }) {
  const save = useSaveMapping(recommendation.id, null)
  const [formError, setFormError] = useState<string | null>(null)
  const id = `topic-${recommendation.id}`
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<QuickValues>({
    resolver: zodResolver(quickSchema),
    defaultValues: {
      course_code: '',
      course_title: recommendation.topic_title,
      credit_units: 3,
      outcome: '',
    },
  })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    save.mutate(
      {
        course_code: normaliseCode(values.course_code),
        course_title: values.course_title,
        credit_units: values.credit_units,
        prerequisites: [],
        learning_outcomes: [values.outcome],
      },
      {
        onSuccess: (saved) => toast.success(`${saved.course_code} added to the proposed courses.`),
        onError: (error) =>
          setFormError(
            applyServerErrors(error, setError, ['course_code', 'course_title', 'credit_units']),
          ),
      },
    )
  })

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-labelledby={`${id}-title`}
      className="flex flex-col gap-3 rounded-[14px] border border-line bg-white px-4 py-4 sm:px-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 id={`${id}-title`} className="text-[15px] font-extrabold text-ink">
          <span className="num text-xs font-semibold text-muted-ink">#{recommendation.rank} </span>
          {recommendation.topic_title}
        </h4>
        <span className="num text-xs text-muted-ink">
          Score {toPoints(recommendation.composite_score)}/100
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-[8.5rem_minmax(0,1fr)_auto]">
        <Field data-invalid={!!errors.course_code}>
          <FieldLabel htmlFor={`${id}-code`}>Code</FieldLabel>
          <Input
            id={`${id}-code`}
            placeholder="CSC 419"
            aria-invalid={!!errors.course_code}
            {...register('course_code')}
          />
          <FieldError errors={[errors.course_code]} />
        </Field>
        <Field data-invalid={!!errors.course_title}>
          <FieldLabel htmlFor={`${id}-course-title`}>Course title</FieldLabel>
          <Input
            id={`${id}-course-title`}
            aria-invalid={!!errors.course_title}
            {...register('course_title')}
          />
          <FieldError errors={[errors.course_title]} />
        </Field>
        <Field data-invalid={!!errors.credit_units}>
          <FieldLabel id={`${id}-units`}>Units</FieldLabel>
          <Controller
            control={control}
            name="credit_units"
            render={({ field }) => (
              <ToggleGroup
                type="single"
                variant="segment"
                aria-labelledby={`${id}-units`}
                value={String(field.value)}
                onValueChange={(value) => value && field.onChange(Number(value))}
              >
                {[1, 2, 3].map((units) => (
                  <ToggleGroupItem key={units} value={String(units)} className="num">
                    {units}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            )}
          />
          <FieldError errors={[errors.credit_units]} />
        </Field>
      </div>
      <Field data-invalid={!!errors.outcome}>
        <FieldLabel htmlFor={`${id}-outcome`}>Students will be able to</FieldLabel>
        <Input
          id={`${id}-outcome`}
          placeholder="e.g. secure a cloud workload against common attacks"
          aria-invalid={!!errors.outcome}
          {...register('outcome')}
        />
        <FieldError errors={[errors.outcome]} />
      </Field>
      {formError && (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Save course
        </Button>
        <Link
          to={designCoursePath(recommendation.id)}
          className="text-[13px] font-bold text-primary hover:underline"
        >
          Full form (prerequisites, more outcomes)
        </Link>
      </div>
    </form>
  )
}
