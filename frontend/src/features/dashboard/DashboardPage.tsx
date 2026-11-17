import {
  AlertTriangle,
  ArrowRight,
  BriefcaseBusiness,
  Check,
  CircleAlert,
  FileText,
  Plus,
  Search,
  Upload,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'

import { LogoMark } from '@/components/brand/Logo'
import { EmptyState } from '@/components/shared/EmptyState'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { useProgrammeReadiness } from '@/features/programmes/api'
import { useCurrentProgramme } from '@/features/programmes/useCurrentProgramme'
import { SessionStatusBadge } from '@/features/sessions/SessionStatusBadge'
import { SystemStatusCard } from '@/features/system/SystemStatusCard'
import { firstName, formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { DashboardSummary, Programme, ProgrammeReadiness } from '@/types/api'

import { useDashboardSummary } from './api'

function greeting(date = new Date()) {
  const hour = date.getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

/**
 * Home: the chosen programme at a glance (hero with headline numbers), whether it is ready
 * for a review, the next step, its reviews and help. Everything follows the programme chosen
 * in the sidebar.
 */
export function DashboardPage() {
  const { programme, isLoading } = useCurrentProgramme()
  // Wait for the programme so the summary is fetched once, for the right programme.
  const summary = useDashboardSummary(programme?.id, !isLoading)
  const { user, isAdmin } = useAuth()

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {summary.isPending ? (
        <div className="space-y-5" aria-label="Loading summary">
          <Skeleton className="h-64 rounded-[20px]" />
          <Skeleton className="h-28 rounded-[14px]" />
        </div>
      ) : summary.isError ? (
        <>
          <Hero programme={programme} name={user.full_name} />
          <Alert variant="destructive">
            <AlertTitle>Could not load the dashboard</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>{summary.error.message}</p>
              <Button variant="outline" size="sm" onClick={() => void summary.refetch()}>
                Try again
              </Button>
            </AlertDescription>
          </Alert>
        </>
      ) : (
        <Overview data={summary.data} programme={programme} />
      )}

      {isAdmin && !summary.isSuccess && (
        <div className="max-w-xl animate-rise [animation-delay:0.3s]">
          <SystemStatusCard />
        </div>
      )}
    </div>
  )
}

/** The dark welcome panel; `action` is the next step and `children` the headline numbers. */
function Hero({
  programme,
  name,
  action,
  note,
  children,
}: {
  programme: Programme | undefined
  name: string
  action?: ReactNode
  note?: ReactNode
  children?: ReactNode
}) {
  return (
    <section
      aria-labelledby="home-title"
      className="relative animate-rise overflow-hidden rounded-[20px] night-grid px-7 py-7 text-white"
    >
      <LogoMark
        size={260}
        tone="dark"
        title=""
        className="pointer-events-none absolute -right-10 -bottom-20 opacity-[0.08]"
      />
      <div className="relative flex flex-col gap-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="flex max-w-2xl flex-col gap-2">
            {programme && (
              <p className="num text-[11.5px] tracking-[0.06em] text-ember-soft uppercase">
                {programme.discipline_code ?? programme.name}
                {programme.faculty ? ` · ${programme.faculty}` : ''}
              </p>
            )}
            <h2
              id="home-title"
              className="text-[28px] leading-tight font-extrabold tracking-[-0.02em]"
            >
              {greeting()}, {firstName(name)}
            </h2>
            <p className="text-[14.5px] leading-relaxed text-night-text">
              Find what employers want from{' '}
              <strong className="text-white">
                {programme ? `${programme.name} graduates` : 'graduates'}
              </strong>
              , compare it with the NUC core and design the university&apos;s 30%.
            </p>
            {note && <p className="text-[14.5px] text-night-text">{note}</p>}
          </div>
          {action}
        </div>
        {children}
      </div>
    </section>
  )
}

function Overview({
  data,
  programme,
}: {
  data: DashboardSummary
  programme: Programme | undefined
}) {
  const { user, canEdit, isAdmin } = useAuth()
  const firstRun = data.documents.total === 0 && data.sessions.total === 0
  const review = data.recommendations.review_session
  const curriculum = data.curriculum_session

  const action = canEdit ? (
    review ? (
      <Button size="lg" variant="secondary" className="bg-white text-ink hover:bg-sand" asChild>
        <Link to={`/sessions/${review.id}/recommendations?decision=undecided`}>
          Continue reviewing <ArrowRight aria-hidden="true" />
        </Link>
      </Button>
    ) : (
      <Button size="lg" variant="secondary" className="bg-white text-ink hover:bg-sand" asChild>
        <Link to="/sessions/new">
          <Plus aria-hidden="true" /> Start a new review
        </Link>
      </Button>
    )
  ) : null

  return (
    <>
      <Hero
        programme={programme}
        name={user.full_name}
        action={action}
        note={
          canEdit &&
          review && (
            <>
              <strong className="num text-white">
                {review.undecided} topic{review.undecided === 1 ? '' : 's'}
              </strong>{' '}
              not reviewed yet in “{review.session_name}”.
            </>
          )
        }
      >
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Documents"
            value={data.documents.total}
            to="/documents"
            detail={
              <>
                {data.documents.ready} ready
                {data.documents.processing > 0 && ` · ${data.documents.processing} processing`}
                {data.documents.failed > 0 && ` · ${data.documents.failed} failed`}
              </>
            }
          />
          <StatTile
            label="Reviews"
            value={data.sessions.total}
            to="/sessions"
            detail={
              <>
                {data.sessions.by_status.completed} completed
                {data.sessions.by_status.processing > 0 &&
                  ` · ${data.sessions.by_status.processing} running`}
              </>
            }
          />
          <StatTile
            label="Awaiting review"
            value={data.recommendations.pending_review}
            to={review ? `/sessions/${review.id}/recommendations?decision=undecided` : '/sessions'}
            linkHint={review ? `Review ${review.session_name}` : 'Reviews'}
            detail={
              review ? (
                <>
                  {review.undecided} not reviewed yet in “{review.session_name}”
                </>
              ) : (
                <>
                  of {data.recommendations.total} topic
                  {data.recommendations.total === 1 ? '' : 's'} · {data.recommendations.accepted}{' '}
                  accepted
                </>
              )
            }
          />
          <StatTile
            label="Courses designed"
            value={data.courses_mapped}
            to={curriculum ? `/sessions/${curriculum.id}/curriculum` : '/reports'}
            linkHint={curriculum ? `Proposed courses of ${curriculum.session_name}` : 'Reports'}
            detail={
              curriculum ? (
                <>Latest in “{curriculum.session_name}”</>
              ) : (
                <>
                  {data.reports} report{data.reports === 1 ? '' : 's'} generated
                </>
              )
            }
          />
        </div>
      </Hero>

      {programme && <Readiness programme={programme} />}
      {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}

      {firstRun ? (
        <EmptyState
          icon={Upload}
          title="Start by gathering evidence"
          action={
            canEdit && (
              <div className="flex flex-wrap justify-center gap-2">
                <Button asChild>
                  <Link to="/sessions/new">
                    <Plus aria-hidden="true" /> Start a new review
                  </Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link to="/documents">Upload documents</Link>
                </Button>
              </div>
            )
          }
        >
          Collect current job adverts or upload policy, institutional and academic documents. Once
          they are processed, a review finds candidate course topics.
        </EmptyState>
      ) : null}
      {firstRun && isAdmin && (
        <div className="max-w-xl animate-rise [animation-delay:0.3s]">
          <SystemStatusCard />
        </div>
      )}
      {!firstRun && (
        <div className="grid items-start gap-5 lg:grid-cols-[1fr_360px]">
          <div className="flex min-w-0 flex-col gap-5">
            <RecentSessions data={data} programme={programme} />
            {isAdmin && (
              <div className="animate-rise [animation-delay:0.3s]">
                <SystemStatusCard />
              </div>
            )}
          </div>
          <div className="flex flex-col gap-5">
            <HowThisWorks />
            <JobMarket data={data} />
            {canEdit ? <QuickActions data={data} /> : <ReadOnlySummary data={data} />}
          </div>
        </div>
      )}
    </>
  )
}

const CHECKS: {
  key: string
  label: string
  ok: (r: ProgrammeReadiness) => boolean
  detail: (r: ProgrammeReadiness) => string
  fix: string
}[] = [
  {
    key: 'core',
    label: 'NUC core',
    ok: (r) => r.nuc_core !== null,
    detail: (r) => r.nuc_core?.version_label ?? 'Not uploaded yet',
    fix: 'An admin uploads the CCMAS document.',
  },
  {
    key: 'skills',
    label: 'Skills list',
    ok: (r) => r.discipline !== null,
    detail: (r) => (r.discipline ? r.discipline.name : 'Discipline not chosen'),
    fix: 'An admin chooses the NUC discipline.',
  },
  {
    key: 'jobs',
    label: 'Job collection',
    ok: (r) => r.job_search.ready,
    detail: (r) =>
      r.job_search.ready ? r.job_search.search_terms.slice(0, 3).join(', ') : 'Not set up',
    fix: 'An admin adds the job titles to look for.',
  },
  {
    key: 'documents',
    label: 'Documents',
    ok: (r) => r.documents_ready >= 5,
    detail: (r) => `${r.documents_ready} ready to analyse`,
    fix: 'Collect adverts or upload at least 5 documents.',
  },
]

/** Whether the programme has what a useful review needs, and who fixes what is missing. */
function Readiness({ programme }: { programme: Programme }) {
  const readiness = useProgrammeReadiness(programme.id)
  const { isAdmin } = useAuth()
  if (!readiness.data) return null
  const r = readiness.data
  const done = CHECKS.filter((check) => check.ok(r)).length

  return (
    <section
      aria-labelledby="readiness-title"
      className="animate-rise rounded-[14px] border border-line bg-white px-5 py-4 [animation-delay:0.08s]"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 id="readiness-title" className="flex items-center gap-2.5 text-sm font-extrabold">
          <span
            className={cn(
              'size-2.5 rounded-full',
              r.ready ? 'animate-live bg-[#1f8a6b]' : 'bg-amber',
            )}
            aria-hidden="true"
          />
          {r.ready
            ? `${programme.name} is ready to analyse`
            : `${programme.name} needs setting up before a review`}
        </h3>
        <div className="flex items-center gap-3">
          <span className="num text-xs text-muted-ink">{done} of 4 ready</span>
          {isAdmin && !r.ready && (
            <Link
              to="/admin/benchmarks"
              className="text-[13px] font-bold text-primary hover:underline"
            >
              Set up programme
            </Link>
          )}
        </div>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {CHECKS.map((check) => {
          const ok = check.ok(r)
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
              <span className="truncate text-xs text-body-soft">{check.detail(r)}</span>
              {!ok && <span className="text-xs text-amber-ink">{check.fix}</span>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function RecentSessions({
  data,
  programme,
}: {
  data: DashboardSummary
  programme: Programme | undefined
}) {
  const { canEdit } = useAuth()
  return (
    <section
      aria-labelledby="recent-sessions"
      className="animate-rise overflow-hidden rounded-[14px] border border-line bg-white [animation-delay:0.14s]"
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-2">
        <h3 id="recent-sessions" className="card-title">
          {programme ? `Reviews for ${programme.name}` : 'Recent reviews'}
        </h3>
        <Link to="/sessions" className="text-[13px] font-bold text-primary hover:underline">
          See all
        </Link>
      </div>
      {data.recent_sessions.length === 0 ? (
        <p className="px-5 pb-5 text-sm text-body-soft">
          No reviews yet.
          {canEdit && (
            <>
              {' '}
              <Link to="/sessions/new" className="font-bold text-primary hover:underline">
                Start one
              </Link>{' '}
              from the ready documents.
            </>
          )}
        </p>
      ) : (
        <Table aria-label="Recent sessions">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Review</TableHead>
              <TableHead className="w-36">Status</TableHead>
              <TableHead className="w-24 pr-5 text-right">Topics</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.recent_sessions.map((session) => (
              <TableRow key={session.id} className="transition-colors hover:bg-sand/60">
                <TableCell className="pl-5 whitespace-normal">
                  <Link
                    to={`/sessions/${session.id}`}
                    className="font-bold break-words text-ink hover:text-primary"
                  >
                    {session.session_name}
                  </Link>
                  <span className="mt-0.5 block text-xs text-muted-ink">
                    <span className="num">{formatDate(session.created_at)}</span> ·{' '}
                    {session.document_count} document{session.document_count === 1 ? '' : 's'}
                  </span>
                </TableCell>
                <TableCell className="w-36 whitespace-normal">
                  <SessionStatusBadge status={session.status} stage={session.current_stage} />
                </TableCell>
                <TableCell className="w-24 pr-5 text-right num text-[13px] font-semibold text-ink">
                  {session.recommendation_count}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}

/** Job adverts for the programme and where to get more. */
function JobMarket({ data }: { data: DashboardSummary }) {
  const { canEdit } = useAuth()
  const adverts = data.documents.by_category.job_market ?? 0
  return (
    <section
      aria-labelledby="job-market"
      className="flex lift animate-rise flex-col gap-3 rounded-[14px] border border-line bg-white px-5 py-4 [animation-delay:0.2s]"
    >
      <h3 id="job-market" className="section-label">
        Job market
      </h3>
      <p className="flex items-baseline gap-2">
        <span className="num text-[32px] leading-none font-semibold tracking-[-0.02em] text-ink">
          {adverts}
        </span>
        <span className="text-sm text-body">
          job advert{adverts === 1 ? '' : 's'} in the library
        </span>
      </p>
      {canEdit && (
        <Button variant="outline" size="sm" className="self-start" asChild>
          <Link to="/sessions/new">
            <BriefcaseBusiness aria-hidden="true" /> Collect new adverts
          </Link>
        </Button>
      )}
    </section>
  )
}

function QuickActions({ data }: { data: DashboardSummary }) {
  const actions = [
    { to: '/sessions/new', icon: Plus, label: 'New review' },
    { to: '/documents', icon: Upload, label: 'Upload documents' },
    { to: '/sessions', icon: Search, label: 'All reviews' },
    { to: '/reports', icon: FileText, label: 'Reports' },
  ]
  return (
    <section
      aria-labelledby="quick-actions"
      className="flex animate-rise flex-col gap-3 rounded-[14px] border border-line bg-white px-5 py-4 [animation-delay:0.26s]"
    >
      <div>
        <h3 id="quick-actions" className="card-title">
          Quick actions
        </h3>
        <p className="text-xs text-muted-ink">
          NUC core: {data.nuc_core_version?.version_label ?? 'not set'}
        </p>
      </div>
      <div className="grid gap-2">
        {actions.map((action) => (
          <Button key={action.to} variant="outline" className="justify-start" asChild>
            <Link to={action.to}>
              <action.icon aria-hidden="true" /> {action.label}
            </Link>
          </Button>
        ))}
      </div>
    </section>
  )
}

/** For viewers instead of the next steps: what has been decided so far, read-only. */
function ReadOnlySummary({ data }: { data: DashboardSummary }) {
  const latest = data.recent_sessions[0]
  return (
    <section
      aria-labelledby="summary"
      className="flex animate-rise flex-col gap-3 rounded-[14px] border border-line bg-white px-5 py-4 [animation-delay:0.26s]"
    >
      <div>
        <h3 id="summary" className="card-title">
          Summary
        </h3>
        <p className="text-xs text-muted-ink">
          NUC core: {data.nuc_core_version?.version_label ?? 'not set'}
        </p>
      </div>
      <dl className="divide-y divide-divider text-sm">
        <div className="flex flex-col gap-0.5 pb-3">
          <dt className="text-body-soft">Latest review</dt>
          <dd className="font-bold text-ink">
            {latest ? (
              <Link to={`/sessions/${latest.id}`} className="hover:text-primary">
                {latest.session_name}
              </Link>
            ) : (
              'None yet'
            )}
          </dd>
        </div>
        <div className="flex items-center justify-between py-3">
          <dt className="text-body-soft">Accepted topics</dt>
          <dd className="num text-lg font-semibold text-ink">{data.recommendations.accepted}</dd>
        </div>
        <div className="flex items-center justify-between pt-3">
          <dt className="text-body-soft">Proposed courses</dt>
          <dd className="num text-lg font-semibold text-ink">{data.courses_mapped}</dd>
        </div>
      </dl>
    </section>
  )
}

const HELP_DISMISSED_KEY = 'nlprs.howThisWorks.dismissed'

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(HELP_DISMISSED_KEY) === '1'
  } catch {
    return false
  }
}

function storeDismissed(value: boolean) {
  try {
    if (value) window.localStorage.setItem(HELP_DISMISSED_KEY, '1')
    else window.localStorage.removeItem(HELP_DISMISSED_KEY)
  } catch {
    // Private mode or blocked storage: it simply shows again next time.
  }
}

const HOW_STEPS = [
  {
    title: 'Evidence',
    text: 'Start a review: collect current job adverts for the programme, or pick and upload documents.',
  },
  {
    title: 'Analyse',
    text: 'SkillBridge reads every document, finds recurring topics and compares them with the NUC core.',
  },
  {
    title: 'Review',
    text: 'Read each topic with its evidence. Accept, reject or mark it to discuss later.',
  },
  {
    title: 'Design courses',
    text: 'Give every accepted topic a course code, title, credit units and learning outcomes.',
  },
  {
    title: 'Report',
    text: 'Download the report with the evidence, decisions and proposed courses, as PDF or Word.',
  },
]

/**
 * A dismissible five-step introduction (remembered in this browser); the sidebar's "See how
 * it works" link (?help=1) shows it again.
 */
function HowThisWorks() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [dismissed, setDismissed] = useState(readDismissed)
  const asked = searchParams.get('help') === '1'

  // Asked for again from the sidebar: show it (a render-time update, not an effect).
  if (asked && dismissed) setDismissed(false)

  useEffect(() => {
    if (!asked) return
    storeDismissed(false)
    setSearchParams(
      (params) => {
        params.delete('help')
        return params
      },
      { replace: true },
    )
  }, [asked, setSearchParams])

  if (dismissed && !asked) return null
  const dismiss = () => {
    setDismissed(true)
    storeDismissed(true)
  }
  return (
    <section
      aria-labelledby="how-this-works"
      className="flex animate-rise flex-col gap-3.5 rounded-[14px] bg-night px-5 py-5 text-white [animation-delay:0.18s]"
    >
      <div className="flex items-center justify-between">
        <h3 id="how-this-works" className="text-base font-extrabold">
          How this works
        </h3>
        <button
          type="button"
          className="h-8 cursor-pointer rounded-lg px-1 text-[13px] font-bold text-ember-soft hover:underline focus-visible:ring-2 focus-visible:ring-ember focus-visible:outline-none"
          aria-label="Hide “How this works”"
          onClick={dismiss}
        >
          Hide
        </button>
      </div>
      <ol className="flex flex-col gap-3 [counter-reset:how]">
        {HOW_STEPS.map((step, index) => (
          <li
            key={step.title}
            className="relative pl-[38px] [counter-increment:how] before:absolute before:top-0 before:left-0 before:flex before:size-[26px] before:items-center before:justify-center before:rounded-full before:bg-terracotta before:font-mono before:text-[12px] before:font-semibold before:text-white before:content-[counter(how)]"
          >
            <p className="text-sm font-bold">
              <span className="sr-only">{index + 1}. </span>
              {step.title}
            </p>
            <p className="mt-0.5 text-[12.5px] leading-normal text-night-text">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

/** A headline number in the hero; the whole tile is a link. */
function StatTile({
  label,
  value,
  detail,
  to,
  linkHint,
}: {
  label: string
  value: number
  detail: ReactNode
  to: string
  /** Where the tile leads, for screen readers (defaults to the label). */
  linkHint?: string
}) {
  return (
    <Link
      to={to}
      aria-label={`${label}: ${value}${linkHint ? `. ${linkHint}` : ''}`}
      className="group flex flex-col gap-1 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3.5 transition-colors hover:border-white/25 hover:bg-white/[0.08] focus-visible:ring-3 focus-visible:ring-ember/50 focus-visible:outline-none"
    >
      <span className="num text-[28px] leading-tight font-semibold tracking-[-0.02em]">
        {value.toLocaleString()}
      </span>
      <span className="text-[13px] font-bold">{label}</span>
      <span className="text-xs text-night-text">{detail}</span>
    </Link>
  )
}

function NucCoreHint({ isAdmin }: { isAdmin: boolean }) {
  return (
    <Alert variant="warning" className="text-left">
      <AlertTriangle aria-hidden="true" />
      <AlertTitle>No active NUC core reference</AlertTitle>
      <AlertDescription>
        Reviews cannot run until an administrator uploads the NUC CCMAS core for this programme.
        {isAdmin && (
          <>
            {' '}
            <Link to="/admin/benchmarks">Upload it now</Link>.
          </>
        )}
      </AlertDescription>
    </Alert>
  )
}
