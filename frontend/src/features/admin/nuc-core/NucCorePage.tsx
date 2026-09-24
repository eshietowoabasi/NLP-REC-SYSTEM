import { zodResolver } from '@hookform/resolvers/zod'
import { AlertTriangle, BookMarked, CheckCircle2, Loader2, Upload } from 'lucide-react'
import { useId, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DocumentStatusBadge } from '@/features/documents/DocumentStatusBadge'
import { checkFile } from '@/features/documents/labels'
import { applyServerErrors } from '@/lib/forms'
import { formatDateTime, formatNumber } from '@/lib/format'
import type { NucCoreVersion } from '@/types/api'

import { useNucCore, useNucCoreVersions, useUploadNucCore } from './api'

export function NucCorePage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold">NUC core reference</h2>
        <p className="max-w-prose text-sm text-muted-foreground">
          The nationally fixed 70% of the CCMAS Computer Science curriculum. Every candidate topic
          is compared against the active version to flag potential duplicates and measure novelty.
          Exactly one version is active; a new upload becomes active once it has been processed.
        </p>
      </div>
      <CurrentVersion />
      <UploadVersionCard />
      <VersionHistory />
    </div>
  )
}

function CurrentVersion() {
  const nucCore = useNucCore()

  if (nucCore.isPending) return <Skeleton className="h-36 w-full" />
  if (nucCore.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the NUC core reference</AlertTitle>
        <AlertDescription>{nucCore.error.message}</AlertDescription>
      </Alert>
    )
  }
  const { active, latest } = nucCore.data
  const pendingLatest = latest && latest.id !== active?.id ? latest : null

  return (
    <div className="space-y-3">
      {active ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              <BookMarked className="size-5" aria-hidden="true" />
              {active.version_label}
              <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">
                <CheckCircle2 aria-hidden="true" /> Active
              </Badge>
            </CardTitle>
            <CardDescription>
              Uploaded {formatDateTime(active.created_at)} by {active.uploaded_by.full_name}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center justify-between gap-4 text-sm">
            <dl className="flex flex-wrap gap-x-8 gap-y-2">
              <div>
                <dt className="text-muted-foreground">File</dt>
                <dd className="font-medium">{active.document.original_filename}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Pages</dt>
                <dd className="font-medium">{formatNumber(active.document.page_count)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Words</dt>
                <dd className="font-medium">{formatNumber(active.document.word_count)}</dd>
              </div>
            </dl>
            <Button variant="outline" asChild>
              <Link to={`/documents/${active.document.id}`}>View extracted text</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Alert>
          <AlertTriangle aria-hidden="true" />
          <AlertTitle>No active NUC core reference</AlertTitle>
          <AlertDescription>
            Analysis sessions cannot run until a NUC core document has been uploaded and processed.
          </AlertDescription>
        </Alert>
      )}

      {pendingLatest && <LatestUploadNotice version={pendingLatest} />}
    </div>
  )
}

function LatestUploadNotice({ version }: { version: NucCoreVersion }) {
  const status = version.document.processing_status
  if (status === 'failed') {
    return (
      <Alert variant="destructive">
        <AlertTriangle aria-hidden="true" />
        <AlertTitle>“{version.version_label}” could not be processed</AlertTitle>
        <AlertDescription>
          {version.document.error_message} The previous version remains active.
        </AlertDescription>
      </Alert>
    )
  }
  if (status === 'uploaded' || status === 'parsing') {
    return (
      <Alert>
        <Loader2 className="animate-spin" aria-hidden="true" />
        <AlertTitle>Processing “{version.version_label}”</AlertTitle>
        <AlertDescription>
          It becomes the active version automatically once processing finishes.
        </AlertDescription>
      </Alert>
    )
  }
  return null
}

const uploadSchema = z.object({
  version_label: z.string().trim().min(1, 'Enter a version label.').max(64),
  file: z
    .instanceof(File, { message: 'Choose the NUC core document.' })
    .superRefine((file, ctx) => {
      const problem = checkFile(file)
      if (problem) ctx.addIssue({ code: 'custom', message: problem })
    }),
})

type UploadValues = z.infer<typeof uploadSchema>

function UploadVersionCard() {
  const upload = useUploadNucCore()
  const fileId = useId()
  const [progress, setProgress] = useState<number | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<UploadValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { version_label: '' },
  })

  const onSubmit = handleSubmit(({ version_label, file }) => {
    setFormError(null)
    setProgress(0)
    upload.mutate(
      { file, versionLabel: version_label, onProgress: setProgress },
      {
        onSuccess: (version) => {
          toast.success(`“${version.version_label}” uploaded; processing has started.`)
          reset({ version_label: '' })
        },
        onError: (error) =>
          setFormError(applyServerErrors(error, setError, ['version_label', 'file'])),
        onSettled: () => setProgress(null),
      },
    )
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a new version</CardTitle>
        <CardDescription>
          PDF, DOCX or TXT, up to 25 MB. The current version stays active until the new one has been
          processed successfully.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} noValidate className="max-w-lg">
          <FieldGroup>
            {formError && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <Field data-invalid={!!errors.version_label}>
              <FieldLabel htmlFor="version_label">Version label</FieldLabel>
              <Input
                id="version_label"
                placeholder="e.g. CCMAS 2023"
                aria-invalid={!!errors.version_label}
                {...register('version_label')}
              />
              <FieldError errors={[errors.version_label]} />
            </Field>
            <Field data-invalid={!!errors.file}>
              <FieldLabel htmlFor={fileId}>Document</FieldLabel>
              <Controller
                control={control}
                name="file"
                render={({ field }) => (
                  <Input
                    id={fileId}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    aria-invalid={!!errors.file}
                    onChange={(event) => field.onChange(event.target.files?.[0])}
                    onBlur={field.onBlur}
                  />
                )}
              />
              <FieldDescription>The complete NUC CCMAS core curriculum document.</FieldDescription>
              <FieldError errors={[errors.file]} />
            </Field>
            {progress !== null && (
              <Progress value={Math.round(progress * 100)} aria-label="Upload progress" />
            )}
            <div>
              <Button type="submit" disabled={upload.isPending}>
                {upload.isPending ? (
                  <Loader2 className="animate-spin" aria-hidden="true" />
                ) : (
                  <Upload aria-hidden="true" />
                )}
                Upload version
              </Button>
            </div>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}

function VersionHistory() {
  const versions = useNucCoreVersions()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Version history</CardTitle>
      </CardHeader>
      <CardContent>
        {versions.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : versions.isError ? (
          <p className="text-sm text-destructive">{versions.error.message}</p>
        ) : versions.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">No versions uploaded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead>By</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.data.map((version) => (
                  <TableRow key={version.id}>
                    <TableCell className="font-medium">
                      {version.version_label}
                      {version.is_active && (
                        <Badge variant="secondary" className="ml-2">
                          Active
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Link to={`/documents/${version.document.id}`} className="hover:underline">
                        {version.document.original_filename}
                      </Link>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {formatDateTime(version.created_at)}
                    </TableCell>
                    <TableCell>{version.uploaded_by.full_name}</TableCell>
                    <TableCell>
                      <DocumentStatusBadge
                        status={version.document.processing_status}
                        errorMessage={version.document.error_message}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
