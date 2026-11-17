import { ArrowRight, Check, CircleAlert, Users } from 'lucide-react'
import { useSearchParams } from 'react-router'

import { PageHeader } from '@/components/shared/PageHeader'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ProgrammeBenchmark } from '@/features/admin/benchmarks/ProgrammeBenchmark'
import { ProgrammeDetailsCard } from '@/features/admin/benchmarks/ProgrammeDetailsCard'
import { ProgrammeHarvester } from '@/features/admin/labour-market/LabourMarketPage'
import { useProgrammes, useProgrammesReadiness } from '@/features/programmes/api'
import { READINESS_CHECKS, readyCount, type ProgrammeTab } from '@/features/programmes/readiness'
import { useCurrentProgramme } from '@/features/programmes/useCurrentProgramme'
import { cn } from '@/lib/utils'
import type { Programme, ProgrammeReadiness } from '@/types/api'

import { AddProgrammeDialog } from './AddProgrammeDialog'
import { ProgrammePeople } from './ProgrammePeople'

const TABS: { value: ProgrammeTab; label: string }[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'core', label: 'NUC core' },
  { value: 'jobs', label: 'Job collection' },
  { value: 'people', label: 'People' },
]

const isTab = (value: string | null): value is ProgrammeTab =>
  TABS.some((tab) => tab.value === value)

const codeOf = (programme: Programme) =>
  programme.discipline_code ?? programme.name.slice(0, 3).toUpperCase()

/**
 * Admin Programmes: every NUC programme with what it still needs, and one place to set each up
 * (details and discipline, NUC core, job collection, people). `?programme=&tab=` deep-links
 * here, e.g. from the readiness card on Home.
 */
export function ProgrammesPage() {
  // Admins manage retired programmes here too (to restore them).
  const programmes = useProgrammes({ includeInactive: true })
  const readiness = useProgrammesReadiness()
  const { programme: current } = useCurrentProgramme()
  const [params, setParams] = useSearchParams()

  if (programmes.isPending) {
    return (
      <div className="mx-auto max-w-6xl space-y-5" aria-label="Loading programmes">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-40 w-full rounded-[14px]" />
      </div>
    )
  }
  if (programmes.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load programmes</AlertTitle>
        <AlertDescription>{programmes.error.message}</AlertDescription>
      </Alert>
    )
  }

  const list = programmes.data
  const requested = Number(params.get('programme'))
  const selected =
    list.find((p) => p.id === requested) ??
    list.find((p) => p.id === current?.id) ??
    list.find((p) => p.is_active) ??
    list[0]
  const tabParam = params.get('tab')
  const tab: ProgrammeTab = isTab(tabParam) ? tabParam : 'overview'
  const readinessOf = (id: number) => readiness.data?.find((r) => r.programme_id === id)
  const readyTotal = list.filter((p) => p.is_active && readinessOf(p.id)?.ready).length
  const activeTotal = list.filter((p) => p.is_active).length

  const go = (programmeId: number, nextTab: ProgrammeTab = tab) =>
    setParams({ programme: String(programmeId), tab: nextTab }, { replace: true })

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Programmes"
        description={
          <>
            Every NUC CCMAS programme SkillBridge serves. Each one has its own NUC core, skills
            list, job collection and planners.{' '}
            {activeTotal > 0 && (
              <span className="num text-[13px] text-ink">
                {readyTotal} of {activeTotal} ready
              </span>
            )}
          </>
        }
        actions={<AddProgrammeDialog onCreated={(programme) => go(programme.id, 'core')} />}
      />

      {list.length === 0 ? (
        <p className="text-sm text-body-soft">No programmes yet. Add the first one.</p>
      ) : (
        <ul aria-label="Programmes" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {list.map((programme, index) => (
            <li
              key={programme.id}
              className="animate-rise"
              style={{ animationDelay: `${Math.min(index, 8) * 0.04}s` }}
            >
              <ProgrammeCard
                programme={programme}
                readiness={readinessOf(programme.id)}
                selected={programme.id === selected?.id}
                onSelect={() => go(programme.id)}
              />
            </li>
          ))}
        </ul>
      )}

      {selected && (
        <section aria-labelledby="programme-title" className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-md bg-terracotta px-2 py-1 num text-xs font-semibold text-white">
              {codeOf(selected)}
            </span>
            <h3 id="programme-title" className="text-xl font-extrabold tracking-[-0.01em] text-ink">
              {selected.name}
            </h3>
            {!selected.is_active && <Badge variant="neutral">Retired</Badge>}
          </div>

          <Tabs value={tab} onValueChange={(value) => go(selected.id, value as ProgrammeTab)}>
            <div className="max-w-full overflow-x-auto">
              <TabsList className="grid w-full grid-cols-2 sm:inline-flex sm:w-fit sm:flex-nowrap">
                {TABS.map((item) => (
                  <TabsTrigger key={item.value} value={item.value} className="shrink-0">
                    {item.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>

            <TabsContent value="overview" className="mt-4 space-y-5">
              <ReadinessPanel
                programme={selected}
                readiness={readinessOf(selected.id)}
                onFix={(next) => go(selected.id, next)}
              />
              <ProgrammeDetailsCard programme={selected} />
            </TabsContent>
            <TabsContent value="core" className="mt-4">
              <ProgrammeBenchmark key={selected.id} programmeId={selected.id} />
            </TabsContent>
            <TabsContent value="jobs" className="mt-4">
              {selected.is_active ? (
                <ProgrammeHarvester key={selected.id} programmeId={selected.id} />
              ) : (
                <p className="text-sm text-body-soft">
                  Restore {selected.name} on the Overview tab to collect jobs for it again.
                </p>
              )}
            </TabsContent>
            <TabsContent value="people" className="mt-4">
              <ProgrammePeople key={selected.id} programme={selected} />
            </TabsContent>
          </Tabs>
        </section>
      )}
    </div>
  )
}

function ProgrammeCard({
  programme,
  readiness,
  selected,
  onSelect,
}: {
  programme: Programme
  readiness: ProgrammeReadiness | undefined
  selected: boolean
  onSelect: () => void
}) {
  const done = readiness ? readyCount(readiness) : 0
  const status = !programme.is_active
    ? 'Retired'
    : readiness === undefined
      ? ''
      : readiness.ready
        ? 'Ready'
        : `${done} of 4 ready`

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={`${programme.name}${status ? `, ${status}` : ''}`}
      className={cn(
        'flex h-full w-full lift flex-col gap-3 rounded-[14px] border border-line bg-white px-4 py-3.5 text-left focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none',
        selected && 'border-2 border-primary px-[15px] py-[13px]',
        !programme.is_active && 'opacity-60',
      )}
    >
      <span className="flex w-full items-start gap-3">
        <span className="rounded-md bg-sand-deep px-1.5 py-1 num text-[11px] font-semibold text-terracotta-dark">
          {codeOf(programme)}
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-[14.5px] font-extrabold text-ink">{programme.name}</span>
          <span className="truncate text-xs text-body-soft">
            {programme.faculty ?? 'Faculty not set'}
          </span>
        </span>
        {status && (
          <span
            className={cn(
              'shrink-0 rounded-full px-2 py-0.5 text-[11px] font-bold',
              status === 'Ready'
                ? 'bg-green-tint text-green'
                : status === 'Retired'
                  ? 'bg-divider text-muted-ink'
                  : 'bg-[#fff3dc] text-amber-ink',
            )}
          >
            {status}
          </span>
        )}
      </span>
      {readiness && programme.is_active && (
        <span className="flex w-full items-center justify-between gap-2">
          <span className="flex gap-1" aria-hidden="true">
            {READINESS_CHECKS.map((check) => (
              <span
                key={check.key}
                title={check.label}
                className={cn(
                  'h-1.5 w-7 rounded-full',
                  check.ok(readiness) ? 'bg-[#1f8a6b]' : 'bg-divider',
                )}
              />
            ))}
          </span>
          <span className="flex items-center gap-1 text-xs text-body-soft">
            <Users className="size-3.5" aria-hidden="true" />
            <span className="num">{readiness.planners}</span>
            {readiness.planners === 1 ? ' planner' : ' planners'}
          </span>
        </span>
      )}
    </button>
  )
}

/** The four things a programme needs, each linking to the tab where it is set up. */
function ReadinessPanel({
  programme,
  readiness,
  onFix,
}: {
  programme: Programme
  readiness: ProgrammeReadiness | undefined
  onFix: (tab: ProgrammeTab) => void
}) {
  if (!programme.is_active) return null
  if (!readiness) return <Skeleton className="h-28 w-full rounded-[14px]" />
  const done = readyCount(readiness)

  return (
    <section
      aria-labelledby="setup-title"
      className="rounded-[14px] border border-line bg-white px-5 py-4"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h4 id="setup-title" className="flex items-center gap-2.5 text-sm font-extrabold">
          <span
            className={cn(
              'size-2.5 rounded-full',
              readiness.ready ? 'animate-live bg-[#1f8a6b]' : 'bg-amber',
            )}
            aria-hidden="true"
          />
          {readiness.ready ? `${programme.name} is ready for reviews` : `Set up ${programme.name}`}
        </h4>
        <span className="num text-xs text-muted-ink">{done} of 4 ready</span>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {READINESS_CHECKS.map((check) => {
          const ok = check.ok(readiness)
          return (
            <li
              key={check.key}
              className={cn(
                'flex flex-col gap-1 rounded-[10px] border px-3 py-2.5',
                ok
                  ? 'border-[#d3eadf] bg-[#f5fbf8]'
                  : 'border-dashed border-[#e9c48a] bg-[#fffaf0]',
              )}
            >
              <span className="flex items-center gap-2 text-[12.5px] font-extrabold text-ink">
                {ok ? (
                  <Check
                    className="size-4 rounded-full bg-[#1f8a6b] p-0.5 text-white"
                    aria-hidden="true"
                  />
                ) : (
                  <CircleAlert className="size-4 text-[#8a5a00]" aria-hidden="true" />
                )}
                {check.label}
                <span className="sr-only">{ok ? ' (done)' : ' (missing)'}</span>
              </span>
              <span className="truncate text-xs text-body-soft">{check.detail(readiness)}</span>
              {!ok && (
                <button
                  type="button"
                  onClick={() => onFix(check.tab)}
                  className="inline-flex items-center gap-1 self-start text-xs font-bold text-primary hover:underline"
                >
                  {check.key === 'documents' ? 'Collect jobs' : `Set up ${check.label}`}
                  <ArrowRight className="size-3" aria-hidden="true" />
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
