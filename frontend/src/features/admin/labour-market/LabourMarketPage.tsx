import { BriefcaseBusiness, Loader2, RefreshCw, Save } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useHarvestState,
  useSaveHarvestProfile,
  useStartHarvest,
} from '@/features/labour-market/api'
import { HARVEST_PHASES } from '@/features/labour-market/labels'
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

  const [chosenProgrammeId, setProgrammeId] = useState(0)
  // Until the admin picks one, show the first programme.
  const programmeId = chosenProgrammeId || programmes.data?.[0]?.id || 0

  if (programmes.isPending) {
    return <Skeleton className="h-96 w-full" />
  }

  if (programmes.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load programmes</AlertTitle>

        <AlertDescription>{programmes.error.message}</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="space-y-1">
        <h2 className="page-title">Job collection</h2>

        <p className="max-w-3xl page-lead">
          Tell SkillBridge which job titles belong to each programme. It collects current job
          adverts and prepares them for reviews, just like uploaded documents.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Programme</CardTitle>

          <CardDescription>
            Each programme has its own labour-market search profile.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <select
            aria-label="Programme"
            value={programmeId}
            onChange={(event) => setProgrammeId(Number(event.target.value))}
            className="h-11 w-full max-w-xl rounded-xl border border-input bg-white px-3.5 text-sm font-medium text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
          >
            {programmes.data.map((programme) => (
              <option key={programme.id} value={programme.id}>
                {programme.name}
                {programme.discipline_code ? ` (${programme.discipline_code})` : ''}
              </option>
            ))}
          </select>
        </CardContent>
      </Card>

      {programmeId > 0 && <ProgrammeHarvester key={programmeId} programmeId={programmeId} />}
    </div>
  )
}

export function ProgrammeHarvester({ programmeId }: { programmeId: number }) {
  const state = useHarvestState(programmeId)

  const save = useSaveHarvestProfile()

  const start = useStartHarvest()

  const [terms, setTerms] = useState('')

  const [fields, setFields] = useState('')

  const [target, setTarget] = useState(10)

  const [pages, setPages] = useState(2)

  // Fill the form from the saved profile whenever a new one arrives
  // (adjusting state during render instead of in an effect).
  const profile = state.data?.profile
  const [syncedProfile, setSyncedProfile] = useState<typeof profile>(undefined)
  if (profile && profile !== syncedProfile) {
    setSyncedProfile(profile)
    setTerms(profile.search_terms.join(', '))
    setFields(profile.field_slugs.join(', '))
  }

  if (state.isPending) {
    return <Skeleton className="h-96 w-full" />
  }

  if (state.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the harvester</AlertTitle>

        <AlertDescription>{state.error.message}</AlertDescription>
      </Alert>
    )
  }

  const latest = state.data.latest_run

  // A new collection can start once the previous one has finished collecting.
  const running = latest?.phase === 'queued' || latest?.phase === 'collecting'

  const parseCsv = (value: string) =>
    value
      .split(',')
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)

  const saveProfile = () => {
    save.mutate(
      {
        programmeId,
        profile: {
          search_terms: parseCsv(terms),
          field_slugs: parseCsv(fields),
        },
      },
      {
        onSuccess: () => toast.success('Labour-market profile saved.'),
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
        onSuccess: () => toast.success('Labour-market collection started.'),
      },
    )
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <Card>
        <CardHeader>
          <CardTitle>Search profile</CardTitle>

          <CardDescription>
            The job titles SkillBridge looks for. Each title is searched on its own, then any job
            fields you add are browsed for more.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="space-y-2">
            <label htmlFor="job-search-terms" className="text-sm font-bold text-ink">
              Job titles
            </label>

            <textarea
              id="job-search-terms"
              value={terms}
              onChange={(event) => setTerms(event.target.value)}
              rows={4}
              placeholder="e.g. registered nurse, nursing officer, midwife"
              className="w-full rounded-xl border border-input bg-white p-3 text-sm text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
            />

            <p className="text-xs text-muted-foreground">
              Separate titles with commas. Each one is searched on MyJobMag, and only adverts whose
              job title contains one of them are imported.
            </p>
          </div>

          <div className="space-y-2">
            <label htmlFor="job-fields" className="text-sm font-bold text-ink">
              MyJobMag fields (optional)
            </label>

            <textarea
              id="job-fields"
              value={fields}
              onChange={(event) => setFields(event.target.value)}
              rows={3}
              placeholder="e.g. medical"
              className="w-full rounded-xl border border-input bg-white p-3 text-sm text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
            />

            <p className="text-xs text-muted-foreground">
              Browsed after the job titles, for adverts the title search misses. Examples:{' '}
              {FIELD_EXAMPLES.join(', ')}.
            </p>
          </div>

          {save.isError && (
            <Alert variant="destructive">
              <AlertDescription>{save.error.message}</AlertDescription>
            </Alert>
          )}

          <Button onClick={saveProfile} disabled={save.isPending}>
            {save.isPending ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
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
              <BriefcaseBusiness className="size-5" aria-hidden="true" />
              Collect jobs
            </CardTitle>

            <CardDescription>
              SkillBridge will respect the source's robots.txt and collect slowly in the background.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="target-count" className="text-xs font-bold text-ink">
                  Target adverts
                </label>

                <Input
                  id="target-count"
                  type="number"
                  min={1}
                  max={30}
                  value={target}
                  onChange={(event) => setTarget(Number(event.target.value))}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="pages" className="text-xs font-bold text-ink">
                  Pages per search
                </label>

                <Input
                  id="pages"
                  type="number"
                  min={1}
                  max={5}
                  value={pages}
                  onChange={(event) => setPages(Number(event.target.value))}
                />
              </div>
            </div>

            {start.isError && (
              <Alert variant="destructive">
                <AlertDescription>{start.error.message}</AlertDescription>
              </Alert>
            )}

            <Button
              className="w-full"
              onClick={collect}
              disabled={running || start.isPending || !terms.trim()}
            >
              {running || start.isPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw aria-hidden="true" />
              )}

              {running ? 'Collecting…' : 'Collect jobs now'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latest run</CardTitle>
          </CardHeader>

          <CardContent>
            {!latest ? (
              <p className="text-sm text-muted-foreground">
                No job collection has run for this programme yet.
              </p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Badge variant={HARVEST_PHASES[latest.phase].variant}>
                    {latest.phase === 'collecting' || latest.phase === 'preparing' ? (
                      <Loader2 className="animate-spin" aria-hidden="true" />
                    ) : null}
                    {HARVEST_PHASES[latest.phase].label}
                  </Badge>

                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(latest.created_at)}
                  </span>
                </div>

                {latest.imported_count > 0 && (
                  <p className="text-sm text-ink" aria-live="polite">
                    <strong className="tabular-nums">
                      {latest.documents_ready} of {latest.imported_count}
                    </strong>{' '}
                    {latest.imported_count === 1 ? 'advert is' : 'adverts are'} ready to analyse
                    {latest.phase === 'preparing'
                      ? '. The rest are still being prepared and will appear in New analysis when they are ready.'
                      : '.'}
                  </p>
                )}

                {latest.phase === 'ready' && latest.imported_count === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No new adverts were found. Try more job titles or more pages per search.
                  </p>
                )}

                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Adverts checked</dt>
                    <dd className="font-bold text-ink tabular-nums">{latest.examined_count}</dd>
                  </div>

                  <div>
                    <dt className="text-muted-foreground">Matching job titles</dt>
                    <dd className="font-bold text-ink tabular-nums">{latest.found_count}</dd>
                  </div>

                  <div>
                    <dt className="text-muted-foreground">Added to the library</dt>
                    <dd className="font-bold text-ink tabular-nums">{latest.imported_count}</dd>
                  </div>

                  <div>
                    <dt className="text-muted-foreground">Skipped</dt>
                    <dd className="font-bold text-ink tabular-nums">{latest.skipped_count}</dd>
                  </div>
                </dl>

                {latest.documents_failed > 0 && (
                  <Alert variant="warning">
                    <AlertDescription>
                      {latest.documents_failed}{' '}
                      {latest.documents_failed === 1 ? 'advert' : 'adverts'} could not be processed
                      and will not be used.
                    </AlertDescription>
                  </Alert>
                )}

                {latest.error_message && (
                  <Alert variant="destructive">
                    <AlertDescription>{latest.error_message}</AlertDescription>
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
