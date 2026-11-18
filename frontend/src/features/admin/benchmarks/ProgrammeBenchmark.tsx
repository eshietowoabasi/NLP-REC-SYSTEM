import { BookOpen, Loader2, Upload } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useProgrammeBenchmarks, useUploadProgrammeBenchmark } from '@/features/programmes/api'
import { formatDateTime } from '@/lib/format'

/** The programme's NUC core: the active version, its history and uploading a new one. */
export function ProgrammeBenchmark({ programmeId }: { programmeId: number }) {
  const state = useProgrammeBenchmarks(programmeId)

  const upload = useUploadProgrammeBenchmark()

  const [versionLabel, setVersionLabel] = useState('')

  const [file, setFile] = useState<File | null>(null)

  if (state.isPending) {
    return <Skeleton className="h-64 w-full" />
  }

  if (state.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the NUC core</AlertTitle>

        <AlertDescription>{state.error.message}</AlertDescription>
      </Alert>
    )
  }

  const { programme, active, versions } = state.data

  const submitUpload = (event: FormEvent) => {
    event.preventDefault()

    if (!file || !versionLabel.trim()) {
      return
    }

    upload.mutate(
      {
        programmeId,
        file,
        versionLabel: versionLabel.trim(),
      },
      {
        onSuccess: () => {
          toast.success(`Benchmark uploaded for ${programme.name}; processing has started.`)

          setVersionLabel('')
          setFile(null)
        },
      },
    )
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <div className="space-y-5">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              <span className="flex size-11 items-center justify-center rounded-xl bg-teal-tint">
                <BookOpen className="size-5 text-teal" aria-hidden="true" />
              </span>
              NUC core curriculum
            </CardTitle>

            <CardDescription>
              The CCMAS document every {programme.name} topic is compared with.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {active ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-ink">{active.version_label}</span>

                    <Badge variant="success">Active</Badge>
                  </div>

                  <p className="mt-1 text-sm text-muted-foreground">
                    Uploaded {formatDateTime(active.created_at)}
                  </p>
                </div>

                <Button variant="outline" asChild>
                  <Link to={`/documents/${active.document.id}`}>View document</Link>
                </Button>
              </div>
            ) : (
              <Alert variant="warning">
                <AlertTitle>No active NUC core yet</AlertTitle>

                <AlertDescription>
                  Reviews for {programme.name}
                  can be created, but cannot run until a NUC core has been uploaded and processed.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>NUC core versions</CardTitle>
          </CardHeader>

          <CardContent>
            {versions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No NUC core uploaded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Version</TableHead>
                      <TableHead>Uploaded</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {versions.map((version) => (
                      <TableRow key={version.id}>
                        <TableCell className="font-bold">
                          {version.version_label}

                          {version.is_active && (
                            <Badge className="ml-2" variant="success">
                              Active
                            </Badge>
                          )}
                        </TableCell>

                        <TableCell>{formatDateTime(version.created_at)}</TableCell>

                        <TableCell className="capitalize">
                          {version.document.processing_status}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="h-fit">
        <CardHeader>
          <CardTitle>Upload NUC core</CardTitle>

          <CardDescription>
            Upload the CCMAS, accreditation framework, or another curriculum reference for this
            programme.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="space-y-3" onSubmit={submitUpload}>
            <Input
              aria-label="NUC core version"
              placeholder="e.g. CCMAS 2023"
              value={versionLabel}
              onChange={(event) => setVersionLabel(event.target.value)}
              required
            />

            <Input
              aria-label="NUC core document"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required
            />

            {upload.isError && <p className="text-sm text-destructive">{upload.error.message}</p>}

            <Button type="submit" disabled={upload.isPending || !file || !versionLabel.trim()}>
              {upload.isPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <Upload aria-hidden="true" />
              )}
              Upload NUC core
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
