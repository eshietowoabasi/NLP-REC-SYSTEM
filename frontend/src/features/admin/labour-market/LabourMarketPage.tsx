import {
  BriefcaseBusiness,
  Loader2,
  RefreshCw,
  Save,
} from 'lucide-react'
import {
  useEffect,
  useState,
} from 'react'
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
  useHarvestState,
  useSaveHarvestProfile,
  useStartHarvest,
} from '@/features/labour-market/api'
import { useProgrammes } from '@/features/programmes/api'
import { formatDateTime } from '@/lib/format'


const FIELD_EXAMPLES = [
  'information-technology',
  'research-data-analysis',
  'medical',
  'accounting-audit',
  'engineering',
  'pharmaceutical',
  'banking',
  'legal-and-regulatory',
]


export function LabourMarketPage() {
  const programmes = useProgrammes()

  const [programmeId, setProgrammeId] =
    useState(0)

  useEffect(() => {
    if (
      programmeId === 0 &&
      programmes.data?.length
    ) {
      setProgrammeId(
        programmes.data[0].id,
      )
    }
  }, [
    programmeId,
    programmes.data,
  ])

  if (programmes.isPending) {
    return (
      <Skeleton className="h-96 w-full" />
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
          Labour Market Harvester
        </h2>

        <p className="max-w-3xl page-lead">
          Define the roles that belong to each academic
          programme, then let SkillBridge collect live job
          adverts and send them directly into the NLP
          ingestion pipeline.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            Programme
          </CardTitle>

          <CardDescription>
            Each programme has its own labour-market
            search profile.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <select
            aria-label="Programme"
            value={programmeId}
            onChange={(event) =>
              setProgrammeId(
                Number(event.target.value),
              )
            }
            className="h-11 w-full max-w-xl rounded-xl border border-input bg-white px-3.5 text-sm font-medium text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
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
        </CardContent>
      </Card>

      {programmeId > 0 && (
        <ProgrammeHarvester
          programmeId={programmeId}
        />
      )}
    </div>
  )
}


function ProgrammeHarvester({
  programmeId,
}: {
  programmeId: number
}) {
  const state =
    useHarvestState(programmeId)

  const save =
    useSaveHarvestProfile()

  const start =
    useStartHarvest()

  const [terms, setTerms] =
    useState('')

  const [fields, setFields] =
    useState('')

  const [target, setTarget] =
    useState(10)

  const [pages, setPages] =
    useState(2)

  useEffect(() => {
    if (!state.data) {
      return
    }

    setTerms(
      state.data.profile.search_terms.join(
        ', ',
      ),
    )

    setFields(
      state.data.profile.field_slugs.join(
        ', ',
      ),
    )
  }, [
    programmeId,
    state.data?.profile,
  ])

  if (state.isPending) {
    return (
      <Skeleton className="h-96 w-full" />
    )
  }

  if (state.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>
          Could not load the harvester
        </AlertTitle>

        <AlertDescription>
          {state.error.message}
        </AlertDescription>
      </Alert>
    )
  }

  const latest = state.data.latest_run

  const running =
    latest?.status === 'queued' ||
    latest?.status === 'running'

  const parseCsv = (value: string) =>
    value
      .split(',')
      .map((item) =>
        item.trim().toLowerCase(),
      )
      .filter(Boolean)

  const saveProfile = () => {
    save.mutate(
      {
        programmeId,
        profile: {
          search_terms:
            parseCsv(terms),
          field_slugs:
            parseCsv(fields),
        },
      },
      {
        onSuccess: () =>
          toast.success(
            'Labour-market profile saved.',
          ),
      },
    )
  }

  const collect = () => {
    start.mutate(
      {
        programmeId,
        targetCount: target,
        pagesPerField: pages,
      },
      {
        onSuccess: () =>
          toast.success(
            'Labour-market collection started.',
          ),
      },
    )
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <Card>
        <CardHeader>
          <CardTitle>
            Search profile
          </CardTitle>

          <CardDescription>
            The profile is editable, so SkillBridge is not
            limited to predefined disciplines.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="space-y-2">
            <label
              htmlFor="job-search-terms"
              className="text-sm font-bold text-ink"
            >
              Relevant job titles / keywords
            </label>

            <textarea
              id="job-search-terms"
              value={terms}
              onChange={(event) =>
                setTerms(event.target.value)
              }
              rows={4}
              placeholder="e.g. registered nurse, nursing officer, midwife"
              className="w-full rounded-xl border border-input bg-white p-3 text-sm text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
            />

            <p className="text-xs text-muted-foreground">
              Separate terms with commas. Only adverts whose
              job titles match these terms are imported.
            </p>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="job-fields"
              className="text-sm font-bold text-ink"
            >
              MyJobMag fields
            </label>

            <textarea
              id="job-fields"
              value={fields}
              onChange={(event) =>
                setFields(event.target.value)
              }
              rows={3}
              placeholder="e.g. medical"
              className="w-full rounded-xl border border-input bg-white p-3 text-sm text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
            />

            <p className="text-xs text-muted-foreground">
              Examples: {FIELD_EXAMPLES.join(', ')}.
            </p>
          </div>

          {save.isError && (
            <Alert variant="destructive">
              <AlertDescription>
                {save.error.message}
              </AlertDescription>
            </Alert>
          )}

          <Button
            onClick={saveProfile}
            disabled={save.isPending}
          >
            {save.isPending ? (
              <Loader2
                className="animate-spin"
                aria-hidden="true"
              />
            ) : (
              <Save aria-hidden="true" />
            )}

            Save search profile
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-5">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BriefcaseBusiness
                className="size-5"
                aria-hidden="true"
              />
              Collect jobs
            </CardTitle>

            <CardDescription>
              SkillBridge will respect the source's
              robots.txt and collect slowly in the
              background.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label
                  htmlFor="target-count"
                  className="text-xs font-bold text-ink"
                >
                  Target adverts
                </label>

                <Input
                  id="target-count"
                  type="number"
                  min={1}
                  max={30}
                  value={target}
                  onChange={(event) =>
                    setTarget(
                      Number(
                        event.target.value,
                      ),
                    )
                  }
                />
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="pages"
                  className="text-xs font-bold text-ink"
                >
                  Pages per field
                </label>

                <Input
                  id="pages"
                  type="number"
                  min={1}
                  max={5}
                  value={pages}
                  onChange={(event) =>
                    setPages(
                      Number(
                        event.target.value,
                      ),
                    )
                  }
                />
              </div>
            </div>

            {start.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  {start.error.message}
                </AlertDescription>
              </Alert>
            )}

            <Button
              className="w-full"
              onClick={collect}
              disabled={
                running ||
                start.isPending ||
                !terms.trim() ||
                !fields.trim()
              }
            >
              {running ||
              start.isPending ? (
                <Loader2
                  className="animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <RefreshCw
                  aria-hidden="true"
                />
              )}

              {running
                ? 'Collecting…'
                : 'Collect jobs now'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              Latest run
            </CardTitle>
          </CardHeader>

          <CardContent>
            {!latest ? (
              <p className="text-sm text-muted-foreground">
                No labour-market collection has been run
                for this programme yet.
              </p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Badge
                    variant={
                      latest.status === 'completed'
                        ? 'success'
                        : latest.status === 'failed'
                          ? 'destructive'
                          : 'secondary'
                    }
                  >
                    {latest.status}
                  </Badge>

                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(
                      latest.created_at,
                    )}
                  </span>
                </div>

                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">
                      Examined
                    </dt>
                    <dd className="font-bold text-ink">
                      {latest.examined_count}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-muted-foreground">
                      Matched
                    </dt>
                    <dd className="font-bold text-ink">
                      {latest.found_count}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-muted-foreground">
                      Imported
                    </dt>
                    <dd className="font-bold text-ink">
                      {latest.imported_count}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-muted-foreground">
                      Skipped
                    </dt>
                    <dd className="font-bold text-ink">
                      {latest.skipped_count}
                    </dd>
                  </div>
                </dl>

                {latest.error_message && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      {latest.error_message}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
