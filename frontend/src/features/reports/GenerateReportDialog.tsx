import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

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
import type { ReportFormat, ReportSection } from '@/types/api'

import { useCompletedSessions } from './api'
import { generateAndDownload } from './download'
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
  showOptions = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Pre-selected session, e.g. when opened from a session's proposed courses. */
  sessionId?: number
  /** Open "More options" (format and sections) straight away. */
  showOptions?: boolean
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {open && (
          <GenerateForm
            sessionId={sessionId}
            showOptions={showOptions}
            onDone={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function GenerateForm({
  sessionId,
  showOptions,
  onDone,
}: {
  sessionId?: number
  showOptions: boolean
  onDone: () => void
}) {
  const sessions = useCompletedSessions()
  const queryClient = useQueryClient()
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      session_id: sessionId ? String(sessionId) : '',
      format: 'docx',
      sections: REPORT_SECTIONS.map((s) => s.id),
    },
  })

  const onSubmit = handleSubmit((values) => {
    // The report is generated in the background and downloaded when ready (see the toast).
    void generateAndDownload(queryClient, Number(values.session_id), {
      format: values.format,
      // Keep the standard order whatever the click order was.
      sections: REPORT_SECTIONS.map((s) => s.id).filter((id) => values.sections.includes(id)),
    })
    onDone()
  })

  const options = sessions.data?.items ?? []
  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Download report</DialogTitle>
        <DialogDescription>
          A Word report with every section, built from the session&apos;s results and current
          decisions. It downloads as soon as it is ready.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
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

        <details open={showOptions} className="group rounded-md border px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium">
            More options{' '}
            <span className="font-normal text-muted-foreground">(format, sections)</span>
          </summary>
          <FieldGroup className="pt-3">
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
                            <label
                              htmlFor={`section-${section.id}`}
                              className="text-sm font-medium"
                            >
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
        </details>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit">
          <Download aria-hidden="true" /> Download report
        </Button>
      </DialogFooter>
    </form>
  )
}
