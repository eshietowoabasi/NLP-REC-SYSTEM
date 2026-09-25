import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, Pencil, Plus, Search, Tags } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { SKILL_LABELS } from '@/features/review/labels'
import { ApiError } from '@/lib/api'
import { applyServerErrors } from '@/lib/forms'
import type { FieldErrorDetails, PatternToken, SkillLabel, SkillPattern } from '@/types/api'

import { useSaveSkillPattern, useSkillPatterns, useToggleSkillPattern } from './api'

const PER_PAGE = 25
const LABELS: readonly SkillLabel[] = ['SKILL', 'TOOL', 'LANGUAGE', 'CERT']

function patternText(pattern: SkillPattern['pattern']) {
  return typeof pattern === 'string' ? pattern : JSON.stringify(pattern)
}

export function SkillPatternsPanel() {
  const [search, setSearch] = useState('')
  const [label, setLabel] = useState<'all' | SkillLabel>('all')
  const [status, setStatus] = useState<'all' | 'active' | 'inactive'>('all')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<SkillPattern | 'new' | null>(null)
  const patterns = useSkillPatterns({
    page,
    per_page: PER_PAGE,
    search: search.trim(),
    label: label === 'all' ? undefined : label,
    is_active: status === 'all' ? undefined : status === 'active',
  })
  const toggle = useToggleSkillPattern()

  const setFilter =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value)
      setPage(1)
    }
  const flip = (pattern: SkillPattern) =>
    toggle.mutate(
      { id: pattern.id, is_active: !pattern.is_active },
      {
        onSuccess: (saved) =>
          toast.success(
            `${saved.canonical_name} pattern ${saved.is_active ? 'activated' : 'deactivated'}.`,
          ),
        onError: (error) => toast.error(error.message),
      },
    )

  return (
    <div className="space-y-4">
      <p className="max-w-3xl text-sm text-muted-foreground">
        Patterns of the spaCy EntityRuler that recognise skills, tools, languages and
        certifications. Phrases match case-insensitively; token patterns allow rules such as
        &ldquo;Go&rdquo; only when followed by &ldquo;developer&rdquo;. Changes apply to sessions
        run afterwards.
      </p>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="pattern-search">Search</Label>
            <div className="relative">
              <Search
                className="absolute top-2.5 left-2.5 size-4 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                id="pattern-search"
                className="w-56 pl-8"
                placeholder="Name or pattern"
                value={search}
                onChange={(event) => setFilter(setSearch)(event.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="pattern-label">Type</Label>
            <Select value={label} onValueChange={(v) => setFilter(setLabel)(v as typeof label)}>
              <SelectTrigger id="pattern-label" className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {LABELS.map((value) => (
                  <SelectItem key={value} value={value}>
                    {SKILL_LABELS[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="pattern-status">Status</Label>
            <Select value={status} onValueChange={(v) => setFilter(setStatus)(v as typeof status)}>
              <SelectTrigger id="pattern-status" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={() => setEditing('new')}>
          <Plus aria-hidden="true" /> Add pattern
        </Button>
      </div>

      {patterns.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load skill patterns</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{patterns.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void patterns.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : patterns.isSuccess && patterns.data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center">
          <Tags className="size-8 text-muted-foreground" aria-hidden="true" />
          <p className="font-medium">No patterns match</p>
          <p className="text-sm text-muted-foreground">Change the filters or add a pattern.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table aria-label="Skill patterns">
            <TableHeader>
              <TableRow>
                <TableHead>Canonical name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Pattern</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {patterns.isPending
                ? Array.from({ length: 4 }, (_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={5}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : patterns.data.items.map((pattern) => (
                    <TableRow key={pattern.id}>
                      <TableCell className="font-medium">{pattern.canonical_name}</TableCell>
                      <TableCell>{SKILL_LABELS[pattern.label]}</TableCell>
                      <TableCell className="max-w-96 whitespace-normal">
                        {typeof pattern.pattern === 'string' ? (
                          <span>&ldquo;{pattern.pattern}&rdquo;</span>
                        ) : (
                          <code className="rounded bg-muted px-1 py-0.5 text-xs break-all">
                            {patternText(pattern.pattern)}
                          </code>
                        )}
                      </TableCell>
                      <TableCell>
                        {pattern.is_active ? (
                          <Badge variant="secondary">Active</Badge>
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground">
                            Inactive
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => flip(pattern)}
                          disabled={toggle.isPending}
                          aria-label={`${pattern.is_active ? 'Deactivate' : 'Activate'} ${pattern.canonical_name} pattern ${patternText(pattern.pattern)}`}
                        >
                          {pattern.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditing(pattern)}
                          aria-label={`Edit ${pattern.canonical_name} pattern ${patternText(pattern.pattern)}`}
                        >
                          <Pencil aria-hidden="true" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>
        </div>
      )}
      {patterns.data && patterns.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={patterns.data.pagination}
          onPageChange={setPage}
          itemLabel="patterns"
        />
      )}

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="sm:max-w-lg">
          {editing !== null && (
            <PatternForm
              pattern={editing === 'new' ? null : editing}
              onDone={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

const schema = z
  .object({
    label: z.enum(['SKILL', 'TOOL', 'LANGUAGE', 'CERT']),
    canonical_name: z.string().trim().min(1, 'Enter the canonical name.').max(128),
    kind: z.enum(['phrase', 'tokens']),
    phrase: z.string().trim().max(100, 'At most 100 characters.'),
    tokens: z.string().trim(),
  })
  .superRefine((values, ctx) => {
    if (values.kind === 'phrase') {
      if (!values.phrase)
        ctx.addIssue({ code: 'custom', path: ['phrase'], message: 'Enter the phrase.' })
      return
    }
    const parsed = parseTokens(values.tokens)
    if (typeof parsed === 'string')
      ctx.addIssue({ code: 'custom', path: ['tokens'], message: parsed })
  })
type Values = z.infer<typeof schema>

/** Parse a JSON token pattern; returns the tokens or an error message. */
function parseTokens(text: string): PatternToken[] | string {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    return 'Enter valid JSON, e.g. [{"LOWER": "go"}, {"LOWER": "developer"}].'
  }
  if (
    !Array.isArray(value) ||
    value.length === 0 ||
    value.length > 10 ||
    !value.every((token) => token && typeof token === 'object' && !Array.isArray(token))
  ) {
    return 'A token pattern is a list of 1 to 10 token objects.'
  }
  return value as PatternToken[]
}

function PatternForm({ pattern, onDone }: { pattern: SkillPattern | null; onDone: () => void }) {
  const save = useSaveSkillPattern(pattern?.id ?? null)
  const [formError, setFormError] = useState<string | null>(null)
  const isPhrase = pattern === null || typeof pattern.pattern === 'string'
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      label: pattern?.label ?? 'SKILL',
      canonical_name: pattern?.canonical_name ?? '',
      kind: isPhrase ? 'phrase' : 'tokens',
      phrase: pattern && typeof pattern.pattern === 'string' ? pattern.pattern : '',
      tokens:
        pattern && typeof pattern.pattern !== 'string'
          ? JSON.stringify(pattern.pattern, null, 1)
          : '',
    },
  })
  const kind = useWatch({ control, name: 'kind' })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    const body = {
      label: values.label,
      canonical_name: values.canonical_name,
      pattern:
        values.kind === 'phrase' ? values.phrase : (parseTokens(values.tokens) as PatternToken[]),
    }
    save.mutate(body, {
      onSuccess: (saved) => {
        toast.success(`Pattern for ${saved.canonical_name} saved.`)
        onDone()
      },
      onError: (error) => {
        const message = applyServerErrors(error, setError, ['label', 'canonical_name'])
        // Server errors on "pattern" belong to whichever input is showing.
        const patternErrors =
          error instanceof ApiError
            ? (error.details as FieldErrorDetails).fields?.pattern
            : undefined
        if (patternErrors) {
          setError(values.kind === 'phrase' ? 'phrase' : 'tokens', {
            type: 'server',
            message: patternErrors.join(' '),
          })
          setFormError(null)
        } else {
          setFormError(message)
        }
      },
    })
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>{pattern ? 'Edit skill pattern' : 'Add skill pattern'}</DialogTitle>
        <DialogDescription>
          Text matching the pattern is counted as the canonical skill in future sessions.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-4 sm:grid-cols-[1fr_10rem]">
          <Field data-invalid={!!errors.canonical_name}>
            <FieldLabel htmlFor="canonical_name">Canonical name</FieldLabel>
            <Input
              id="canonical_name"
              placeholder="e.g. Kubernetes"
              aria-invalid={!!errors.canonical_name}
              {...register('canonical_name')}
            />
            <FieldError errors={[errors.canonical_name]} />
          </Field>
          <Field data-invalid={!!errors.label}>
            <FieldLabel htmlFor="pattern-type">Type</FieldLabel>
            <Controller
              control={control}
              name="label"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="pattern-type" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LABELS.map((value) => (
                      <SelectItem key={value} value={value}>
                        {SKILL_LABELS[value]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            <FieldError errors={[errors.label]} />
          </Field>
        </div>
        <FieldSet>
          <FieldLegend variant="label">Pattern</FieldLegend>
          <Controller
            control={control}
            name="kind"
            render={({ field }) => (
              <ToggleGroup
                type="single"
                variant="outline"
                value={field.value}
                onValueChange={(value) => value && field.onChange(value)}
                aria-label="Pattern kind"
                className="w-fit"
              >
                <ToggleGroupItem value="phrase" className="px-3">
                  Phrase
                </ToggleGroupItem>
                <ToggleGroupItem value="tokens" className="px-3">
                  Token pattern
                </ToggleGroupItem>
              </ToggleGroup>
            )}
          />
          {kind === 'phrase' ? (
            <Field data-invalid={!!errors.phrase}>
              <FieldLabel htmlFor="phrase" className="sr-only">
                Phrase
              </FieldLabel>
              <Input
                id="phrase"
                placeholder="e.g. kubernetes"
                aria-invalid={!!errors.phrase}
                {...register('phrase')}
              />
              <FieldDescription>Matched case-insensitively as whole words.</FieldDescription>
              <FieldError errors={[errors.phrase]} />
            </Field>
          ) : (
            <Field data-invalid={!!errors.tokens}>
              <FieldLabel htmlFor="tokens" className="sr-only">
                Token pattern (JSON)
              </FieldLabel>
              <Textarea
                id="tokens"
                rows={4}
                className="font-mono text-xs"
                placeholder='[{"LOWER": "go"}, {"LOWER": {"IN": ["developer", "engineer"]}}]'
                aria-invalid={!!errors.tokens}
                {...register('tokens')}
              />
              <FieldDescription>
                A spaCy token pattern as JSON: a list of 1 to 10 token objects.
              </FieldDescription>
              <FieldError errors={[errors.tokens]} />
            </Field>
          )}
        </FieldSet>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Save pattern
        </Button>
      </DialogFooter>
    </form>
  )
}
