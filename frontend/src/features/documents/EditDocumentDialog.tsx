import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useProgrammes } from '@/features/programmes/api'
import { ProgrammeSelect } from '@/features/programmes/ProgrammeSelect'
import { applyServerErrors } from '@/lib/forms'
import type { DocumentSummary } from '@/types/api'

import { useEditDocument } from './api'

const schema = z.object({
  title: z.string().trim().min(1, 'Enter a title.').max(255, 'At most 255 characters.'),
  source: z.string().trim().max(128, 'At most 128 characters.'),
  source_url: z
    .string()
    .trim()
    .max(1024, 'At most 1,024 characters.')
    .refine((v) => v === '' || /^https?:\/\//i.test(v), {
      message: 'Enter a web address starting with http:// or https://.',
    }),
  published_on: z.string(),
  // null: a general document, usable by every programme's analyses.
  programme_id: z.number().int().nullable(),
})
type Values = z.infer<typeof schema>

/** Title, source, link and date (shown wherever the document is quoted) and its programme. */
export function EditDocumentDialog({
  document,
  open,
  onOpenChange,
}: {
  document: DocumentSummary
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {open && <EditForm document={document} onDone={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function EditForm({ document, onDone }: { document: DocumentSummary; onDone: () => void }) {
  const edit = useEditDocument(document.id)
  const programmes = useProgrammes()
  // A NUC core document always belongs to its benchmark's programme.
  const canMove = document.source_category !== 'nuc_core'
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: document.title,
      source: document.source ?? '',
      source_url: document.source_url ?? '',
      published_on: document.published_on ?? '',
      programme_id: document.programme?.id ?? null,
    },
  })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    edit.mutate(
      {
        title: values.title,
        source: values.source || null,
        source_url: values.source_url || null,
        published_on: values.published_on || null,
        ...(canMove ? { programme_id: values.programme_id } : {}),
      },
      {
        onSuccess: () => {
          toast.success('Document details saved.')
          onDone()
        },
        onError: (error) =>
          setFormError(
            applyServerErrors(error, setError, [
              'title',
              'source',
              'source_url',
              'published_on',
              'programme_id',
            ]),
          ),
      },
    )
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Edit document details</DialogTitle>
        <DialogDescription>
          These details are shown wherever the document is quoted, for example “Senior QA Engineer –
          Acme, job advert (MyJobMag, Sep 2026)”.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.title}>
          <FieldLabel htmlFor="document-title">Title</FieldLabel>
          <Input id="document-title" aria-invalid={!!errors.title} {...register('title')} />
          <FieldDescription>For a job advert: the job title and the employer.</FieldDescription>
          <FieldError errors={[errors.title]} />
        </Field>
        <Field data-invalid={!!errors.source}>
          <FieldLabel htmlFor="document-source">Source</FieldLabel>
          <Input
            id="document-source"
            placeholder="e.g. MyJobMag, NITDA"
            aria-invalid={!!errors.source}
            {...register('source')}
          />
          <FieldError errors={[errors.source]} />
        </Field>
        <Field data-invalid={!!errors.source_url}>
          <FieldLabel htmlFor="document-link">Link to the original</FieldLabel>
          <Input
            id="document-link"
            type="url"
            placeholder="https://"
            aria-invalid={!!errors.source_url}
            {...register('source_url')}
          />
          <FieldError errors={[errors.source_url]} />
        </Field>
        <Field data-invalid={!!errors.published_on}>
          <FieldLabel htmlFor="document-date">Date published</FieldLabel>
          <Input
            id="document-date"
            type="date"
            className="w-48"
            aria-invalid={!!errors.published_on}
            {...register('published_on')}
          />
          <FieldError errors={[errors.published_on]} />
        </Field>
        {canMove && (
          <Field data-invalid={!!errors.programme_id}>
            <FieldLabel htmlFor="document-programme-edit">Programme</FieldLabel>
            <Controller
              control={control}
              name="programme_id"
              render={({ field }) => (
                <ProgrammeSelect
                  id="document-programme-edit"
                  programmes={programmes.data ?? []}
                  value={field.value}
                  onChange={field.onChange}
                  noneLabel="All programmes (general document)"
                />
              )}
            />
            <FieldDescription>
              Only reviews for this programme can use the document. Reviews already created keep it.
            </FieldDescription>
            <FieldError errors={[errors.programme_id]} />
          </Field>
        )}
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={!isDirty || edit.isPending}>
          {edit.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Save details
        </Button>
      </DialogFooter>
    </form>
  )
}
