import {
  BookOpen,
  Loader2,
  Plus,
  Upload,
} from 'lucide-react'
import {
  useEffect,
  useState,
  type FormEvent,
} from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
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
import {
  useCreateProgramme,
  useProgrammeBenchmarks,
  useProgrammes,
  useUploadProgrammeBenchmark,
} from '@/features/programmes/api'
import { formatDateTime } from '@/lib/format'

export function BenchmarksPage() {
  const programmes = useProgrammes()
  const [programmeId, setProgrammeId] =
    useState(0)

  useEffect(() => {
    if (
      !programmeId &&
      programmes.data?.length
    ) {
      setProgrammeId(programmes.data[0].id)
    }
  }, [programmeId, programmes.data])

  if (programmes.isPending) {
    return (
      <Skeleton className="h-72 w-full" />
    )
  }

  if (programmes.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>
          Could not load programmes
        </AlertTitle>
        <AlertDescription>
          {programmes.error.message}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="space-y-1">
        <h2 className="page-title">
          Programmes &amp; curriculum benchmarks
        </h2>

        <p className="max-w-3xl page-lead">
          Manage the disciplines SkillBridge can analyse.
          Each programme has its own curriculum benchmark,
          so labour-market evidence is compared with the
          correct academic framework.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <Card>
          <CardHeader>
            <CardTitle>
              Select programme
            </CardTitle>
            <CardDescription>
              Choose the programme whose curriculum
              benchmark you want to manage.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {programmes.data.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No programmes have been created yet.
              </p>
            ) : (
              <select
                value={programmeId}
                onChange={(event) =>
                  setProgrammeId(
                    Number(event.target.value),
                  )
                }
                className="h-11 w-full max-w-lg rounded-xl border border-input bg-white px-3.5 text-sm font-medium text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
                aria-label="Programme"
              >
                {programmes.data.map(
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
            )}
          </CardContent>
        </Card>

        <CreateProgrammeCard />
      </div>

      {programmeId > 0 && (
        <ProgrammeBenchmark
          programmeId={programmeId}
        />
      )}
    </div>
  )
}


function CreateProgrammeCard() {
  const create = useCreateProgramme()

  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [faculty, setFaculty] =
    useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()

    create.mutate(
      {
        name: name.trim(),
        discipline_code:
          code.trim() || null,
        faculty:
          faculty.trim() || null,
        country: 'Nigeria',
      },
      {
        onSuccess: (programme) => {
          toast.success(
            `${programme.name} added.`,
          )

          setName('')
          setCode('')
          setFaculty('')
        },
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Add programme
        </CardTitle>

        <CardDescription>
          Add another discipline for analysis.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form
          className="space-y-3"
          onSubmit={submit}
        >
          <Input
            aria-label="Programme name"
            placeholder="e.g. Nursing Science"
            value={name}
            onChange={(event) =>
              setName(event.target.value)
            }
            required
          />

          <Input
            aria-label="Discipline code"
            placeholder="Code, e.g. NSC"
            value={code}
            onChange={(event) =>
              setCode(event.target.value)
            }
          />

          <Input
            aria-label="Faculty"
            placeholder="Faculty (optional)"
            value={faculty}
            onChange={(event) =>
              setFaculty(event.target.value)
            }
          />

          {create.isError && (
            <p className="text-sm text-destructive">
              {create.error.message}
            </p>
          )}

          <Button
            type="submit"
            disabled={
              create.isPending ||
              !name.trim()
            }
          >
            {create.isPending ? (
              <Loader2
                className="animate-spin"
                aria-hidden="true"
              />
            ) : (
              <Plus aria-hidden="true" />
            )}

            Add programme
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}


function ProgrammeBenchmark({
  programmeId,
}: {
  programmeId: number
}) {
  const state =
    useProgrammeBenchmarks(programmeId)

  const upload =
    useUploadProgrammeBenchmark()

  const [versionLabel, setVersionLabel] =
    useState('')

  const [file, setFile] =
    useState<File | null>(null)

  if (state.isPending) {
    return (
      <Skeleton className="h-64 w-full" />
    )
  }

  if (state.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>
          Could not load the curriculum benchmark
        </AlertTitle>

        <AlertDescription>
          {state.error.message}
        </AlertDescription>
      </Alert>
    )
  }

  const {
    programme,
    active,
    versions,
  } = state.data

  const submitUpload = (
    event: FormEvent,
  ) => {
    event.preventDefault()

    if (
      !file ||
      !versionLabel.trim()
    ) {
      return
    }

    upload.mutate(
      {
        programmeId,
        file,
        versionLabel:
          versionLabel.trim(),
      },
      {
        onSuccess: () => {
          toast.success(
            `Benchmark uploaded for ${programme.name}; processing has started.`,
          )

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
                <BookOpen
                  className="size-5 text-teal"
                  aria-hidden="true"
                />
              </span>

              {programme.name}
            </CardTitle>

            <CardDescription>
              {programme.faculty ??
                programme.country}
            </CardDescription>
          </CardHeader>

          <CardContent>
            {active ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-ink">
                      {active.version_label}
                    </span>

                    <Badge variant="success">
                      Active benchmark
                    </Badge>
                  </div>

                  <p className="mt-1 text-sm text-muted-foreground">
                    Uploaded{' '}
                    {formatDateTime(
                      active.created_at,
                    )}
                  </p>
                </div>

                <Button
                  variant="outline"
                  asChild
                >
                  <Link
                    to={`/documents/${active.document.id}`}
                  >
                    View benchmark
                  </Link>
                </Button>
              </div>
            ) : (
              <Alert variant="warning">
                <AlertTitle>
                  No active curriculum benchmark
                </AlertTitle>

                <AlertDescription>
                  Analyses for {programme.name}
                  can be created, but cannot run
                  until a benchmark has been
                  uploaded and processed.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              Benchmark history
            </CardTitle>
          </CardHeader>

          <CardContent>
            {versions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No benchmark versions uploaded yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        Version
                      </TableHead>
                      <TableHead>
                        Uploaded
                      </TableHead>
                      <TableHead>
                        Status
                      </TableHead>
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {versions.map(
                      (version) => (
                        <TableRow
                          key={version.id}
                        >
                          <TableCell className="font-bold">
                            {
                              version.version_label
                            }

                            {version.is_active && (
                              <Badge
                                className="ml-2"
                                variant="success"
                              >
                                Active
                              </Badge>
                            )}
                          </TableCell>

                          <TableCell>
                            {formatDateTime(
                              version.created_at,
                            )}
                          </TableCell>

                          <TableCell className="capitalize">
                            {
                              version.document
                                .processing_status
                            }
                          </TableCell>
                        </TableRow>
                      ),
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="h-fit">
        <CardHeader>
          <CardTitle>
            Upload benchmark
          </CardTitle>

          <CardDescription>
            Upload the CCMAS, accreditation
            framework, or another curriculum
            reference for this programme.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form
            className="space-y-3"
            onSubmit={submitUpload}
          >
            <Input
              aria-label="Benchmark version"
              placeholder="e.g. CCMAS 2023"
              value={versionLabel}
              onChange={(event) =>
                setVersionLabel(
                  event.target.value,
                )
              }
              required
            />

            <Input
              aria-label="Benchmark document"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(event) =>
                setFile(
                  event.target.files?.[0] ??
                    null,
                )
              }
              required
            />

            {upload.isError && (
              <p className="text-sm text-destructive">
                {upload.error.message}
              </p>
            )}

            <Button
              type="submit"
              disabled={
                upload.isPending ||
                !file ||
                !versionLabel.trim()
              }
            >
              {upload.isPending ? (
                <Loader2
                  className="animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <Upload aria-hidden="true" />
              )}

              Upload benchmark
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
