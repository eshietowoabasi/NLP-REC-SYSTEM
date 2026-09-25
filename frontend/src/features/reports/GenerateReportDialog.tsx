import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { applyServerErrors } from '@/lib/forms'
import type { ReportFormat, ReportSection } from '@/types/api'

import { useCompletedSessions, useGenerateReport } from './api'
import { FORMAT_LABELS, REPORT_SECTIONS } from './labels'

const schema = z.object({
  session_id: z.string().min(1, 'Choose a completed session.'),
  format: z.enum(['pdf', 'docx']),
  sections: z
    .array(
      z.enum([
        'corpus_summary',
        'nlp_findings',
        'overlap',
        'recommendations',
        'decisions',
        'proposed_courses',
      ]),
    )
    .min(1, 'Choose at least one section.'),
})
type Values = z.infer<typeof schema>

export function GenerateReportDialog({
  open,
  onOpenChange,
  sessionId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Pre-selected session, e.g. when opened from a session's curriculum. */
  sessionId?: number
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {open && <GenerateForm sessionId={sessionId} onDone={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function GenerateForm({ sessionId, onDone }: { sessionId?: number; onDone: () => void }) {
  const sessions = useCompletedSessions()
  const generate = useGenerateReport()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      session_id: sessionId ? String(sessionId) : '',
      format: 'pdf',
      sections: REPORT_SECTIONS.map((s) => s.id),
    },
  })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    generate.mutate(
      {
        sessionId: Number(values.session_id),
        format: values.format,
        // Keep the standard order whatever the click order was.
        sections: REPORT_SECTIONS.map((s) => s.id).filter((id) => values.sections.includes(id)),
      },
      {
        onSuccess: () => {
          toast.success('Report queued. It appears in the list when ready.')
          onDone()
        },
        onError: (error) =>
          setFormError(applyServerErrors(error, setError, ['format', 'sections'])),
      },
    )
  })

  const options = sessions.data?.items ?? []
  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Generate report</DialogTitle>
        <DialogDescription>
          The report is generated in the background from the session&apos;s stored results and
          current decisions.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.session_id}>
          <FieldLabel htmlFor="report-session">Session</FieldLabel>
          <Controller
            control={control}
            name="session_id"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger
                  id="report-session"
                  className="w-full"
                  aria-invalid={!!errors.session_id}
                  disabled={sessions.isPending}
                >
                  <SelectValue
                    placeholder={sessions.isPending ? 'Loading sessions…' : 'Choose a session'}
                  />
                </SelectTrigger>
                <SelectContent>
                  {options.map((session) => (
                    <SelectItem key={session.id} value={String(session.id)}>
                      {session.session_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          {sessions.isSuccess && options.length === 0 && (
            <FieldDescription>
              No session has completed yet; reports need a completed analysis.
            </FieldDescription>
          )}
          <FieldError errors={[errors.session_id]} />
        </Field>

        <FieldSet>
          <FieldLegend variant="label">Format</FieldLegend>
          <Controller
            control={control}
            name="format"
            render={({ field }) => (
              <ToggleGroup
                type="single"
                variant="outline"
                value={field.value}
                onValueChange={(value) => value && field.onChange(value as ReportFormat)}
                aria-label="Format"
                className="w-fit"
              >
                {(['pdf', 'docx'] as const).map((format) => (
                  <ToggleGroupItem
                    key={format}
                    value={format}
                    className="px-4 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
                  >
                    {FORMAT_LABELS[format]}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            )}
          />
        </FieldSet>

        <FieldSet data-invalid={!!errors.sections}>
          <FieldLegend variant="label">Sections</FieldLegend>
          <Controller
            control={control}
            name="sections"
            render={({ field }) => (
              <ul className="space-y-2.5">
                {REPORT_SECTIONS.map((section) => {
                  const checked = field.value.includes(section.id)
                  const toggle = (on: boolean) =>
                    field.onChange(
                      on
                        ? [...field.value, section.id]
                        : field.value.filter((id: ReportSection) => id !== section.id),
                    )
                  return (
                    <li key={section.id} className="flex items-start gap-2.5">
                      <Checkbox
                        id={`section-${section.id}`}
                        checked={checked}
                        onCheckedChange={(value) => toggle(value === true)}
                        aria-describedby={`section-${section.id}-hint`}
                        className="mt-0.5"
                      />
                      <div className="grid gap-0.5">
                        <label htmlFor={`section-${section.id}`} className="text-sm font-medium">
                          {section.label}
                        </label>
                        <span
                          id={`section-${section.id}-hint`}
                          className="text-xs text-muted-foreground"
                        >
                          {section.hint}
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          />
          <FieldError errors={[errors.sections]} />
        </FieldSet>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={generate.isPending}>
          {generate.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Generate
        </Button>
      </DialogFooter>
    </form>
  )
}
