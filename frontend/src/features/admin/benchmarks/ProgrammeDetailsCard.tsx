import { zodResolver } from '@hookform/resolvers/zod'
import { Archive, ArchiveRestore, Loader2, Pencil } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
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
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useDisciplines, useUpdateProgramme } from '@/features/programmes/api'
import { DisciplineSelect } from '@/features/programmes/DisciplineSelect'
import { ApiError } from '@/lib/api'
import { applyServerErrors } from '@/lib/forms'
import type { NucDiscipline, Programme } from '@/types/api'

const schema = z.object({
  name: z.string().trim().min(2, 'At least 2 characters.').max(160, 'At most 160 characters.'),
  discipline_code: z
    .string()
    .trim()
    .max(32, 'At most 32 characters.')
    .refine((v) => v === '' || v.length >= 2, 'At least 2 characters.'),
  faculty: z.string().trim().max(160, 'At most 160 characters.'),
  description: z.string().trim().max(2000, 'At most 2,000 characters.'),
  nuc_discipline: z.string().nullable(),
})
type Values = z.infer<typeof schema>

/** The selected programme's details, with Edit and Retire/Restore. */
export function ProgrammeDetailsCard({ programme }: { programme: Programme }) {
  const [editing, setEditing] = useState(false)
  const [confirmRetire, setConfirmRetire] = useState(false)
  const update = useUpdateProgramme(programme.id)
  const disciplines = useDisciplines()
  const discipline = disciplines.data?.disciplines.find((d) => d.value === programme.nuc_discipline)

  const setActive = (isActive: boolean) =>
    update.mutate(
      { is_active: isActive },
      {
        onSuccess: () => {
          setConfirmRetire(false)
          toast.success(isActive ? `${programme.name} restored.` : `${programme.name} retired.`)
        },
        onError: (error) => {
          setConfirmRetire(false)
          toast.error(error instanceof ApiError ? error.message : 'Could not change the programme.')
        },
      },
    )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {programme.name}
          {programme.discipline_code && (
            <Badge variant="neutral">{programme.discipline_code}</Badge>
          )}
          {!programme.is_active && <Badge variant="warning">Retired</Badge>}
        </CardTitle>
        <CardDescription>{programme.faculty ?? 'Faculty not given'}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-body">
          <span className="font-semibold text-ink">NUC discipline: </span>
          {discipline
            ? `${discipline.name}, ${discipline.skills} skills plus ${disciplines.data?.general_skills ?? 0} general ones`
            : programme.nuc_discipline === null
              ? 'Not set'
              : '…'}
        </p>
        {programme.nuc_discipline === null && (
          <Alert variant="warning">
            <AlertDescription>
              Choose the NUC discipline so employer demand is measured with the right skills list.
              Until then only general skills count.
            </AlertDescription>
          </Alert>
        )}
        {programme.description && <p className="text-sm text-body">{programme.description}</p>}
        {!programme.is_active && (
          <p className="text-sm text-body-soft">
            Retired programmes cannot be chosen for new analyses, uploads or job collections. Past
            analyses are kept.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            <Pencil aria-hidden="true" /> Edit programme
          </Button>
          {programme.is_active ? (
            <Button variant="outline" size="sm" onClick={() => setConfirmRetire(true)}>
              <Archive aria-hidden="true" /> Retire programme
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled={update.isPending}
              onClick={() => setActive(true)}
            >
              <ArchiveRestore aria-hidden="true" /> Restore programme
            </Button>
          )}
        </div>
      </CardContent>

      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent className="sm:max-w-lg">
          {editing && <EditProgrammeForm programme={programme} onDone={() => setEditing(false)} />}
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmRetire} onOpenChange={setConfirmRetire}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Retire {programme.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              It will no longer be offered for new analyses, uploads or job collections. Its
              documents, benchmark and past analyses are kept, and you can restore it at any time.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={update.isPending}
              onClick={(event) => {
                event.preventDefault()
                setActive(false)
              }}
            >
              Retire programme
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}

function EditProgrammeForm({ programme, onDone }: { programme: Programme; onDone: () => void }) {
  const update = useUpdateProgramme(programme.id)
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
      name: programme.name,
      discipline_code: programme.discipline_code ?? '',
      faculty: programme.faculty ?? '',
      description: programme.description ?? '',
      nuc_discipline: programme.nuc_discipline,
    },
  })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    update.mutate(
      {
        name: values.name,
        discipline_code: values.discipline_code || null,
        faculty: values.faculty || null,
        description: values.description || null,
        nuc_discipline: values.nuc_discipline as NucDiscipline | null,
      },
      {
        onSuccess: () => {
          toast.success('Programme saved.')
          onDone()
        },
        onError: (error) =>
          setFormError(
            applyServerErrors(error, setError, [
              'name',
              'discipline_code',
              'faculty',
              'description',
              'nuc_discipline',
            ]),
          ),
      },
    )
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Edit programme</DialogTitle>
        <DialogDescription>
          The name is shown on analyses and reports for this programme.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.name}>
          <FieldLabel htmlFor="programme-name">Name</FieldLabel>
          <Input id="programme-name" aria-invalid={!!errors.name} {...register('name')} />
          <FieldError errors={[errors.name]} />
        </Field>
        <Field data-invalid={!!errors.discipline_code}>
          <FieldLabel htmlFor="programme-code">Code</FieldLabel>
          <Input
            id="programme-code"
            className="w-40"
            placeholder="e.g. NSC"
            aria-invalid={!!errors.discipline_code}
            {...register('discipline_code')}
          />
          <FieldError errors={[errors.discipline_code]} />
        </Field>
        <Field data-invalid={!!errors.nuc_discipline}>
          <FieldLabel htmlFor="programme-discipline">NUC discipline</FieldLabel>
          <Controller
            control={control}
            name="nuc_discipline"
            render={({ field }) => (
              <DisciplineSelect
                id="programme-discipline"
                className="w-full"
                value={field.value as NucDiscipline | null}
                onChange={field.onChange}
                noneLabel="Not set (general skills only)"
                showCounts
              />
            )}
          />
          <FieldError errors={[errors.nuc_discipline]} />
        </Field>
        <Field data-invalid={!!errors.faculty}>
          <FieldLabel htmlFor="programme-faculty">Faculty</FieldLabel>
          <Input id="programme-faculty" aria-invalid={!!errors.faculty} {...register('faculty')} />
          <FieldError errors={[errors.faculty]} />
        </Field>
        <Field data-invalid={!!errors.description}>
          <FieldLabel htmlFor="programme-description">Description</FieldLabel>
          <Textarea
            id="programme-description"
            rows={3}
            aria-invalid={!!errors.description}
            {...register('description')}
          />
          <FieldError errors={[errors.description]} />
        </Field>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={!isDirty || update.isPending}>
          {update.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Save programme
        </Button>
      </DialogFooter>
    </form>
  )
}
