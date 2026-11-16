import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  File,
  FileText,
  ListChecks,
  Plus,
  Search,
  Upload,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'

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
import { SessionStatusBadge } from '@/features/sessions/SessionStatusBadge'
import { SystemStatusCard } from '@/features/system/SystemStatusCard'
import { firstName, formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { DashboardSummary } from '@/types/api'

import { useDashboardSummary } from './api'

/** Home (Dashboard.dc.html): the next step, headline numbers, recent analyses and help. */
export function DashboardPage() {
  const summary = useDashboardSummary()
  const { user, isAdmin } = useAuth()

  return (
    <div className="mx-auto max-w-6xl space-y-[22px]">
      {summary.isPending ? (
        <div className="space-y-[22px]" aria-label="Loading summary">
          <Skeleton className="h-28 rounded-3xl" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-40 rounded-[20px]" />
            ))}
          </div>
        </div>
      ) : summary.isError ? (
        <>
          <Welcome name={user.full_name} />
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
        <Overview data={summary.data} />
      )}

      {isAdmin && (
        <div className="max-w-xl">
          <SystemStatusCard />
        </div>
      )}
    </div>
  )
}

/** The welcome card; `action` is the next step (editors) and `children` one line about it. */
function Welcome({
  name,
  children,
  action,
}: {
  name: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="flex flex-wrap items-center justify-between gap-6 rounded-3xl border border-line bg-white px-7 py-6">
      <div className="flex max-w-3xl flex-col gap-1.5">
        <h2 className="text-[30px] leading-tight font-extrabold tracking-[-0.03em] text-ink">
          Welcome, {firstName(name)}
        </h2>
        <p className="text-[15px] leading-relaxed text-body-soft">
          Evidence-based recommendations for the institution-designed 30% of the Computer Science
          curriculum under the NUC CCMAS framework.
        </p>
        {children && <p className="text-[15px] text-body-soft">{children}</p>}
      </div>
      {action}
    </section>
  )
}

function Overview({ data }: { data: DashboardSummary }) {
  const { user, canEdit, isAdmin } = useAuth()
  const firstRun = data.documents.total === 0 && data.sessions.total === 0
  const review = data.recommendations.review_session
  const curriculum = data.curriculum_session

  if (firstRun) {
    return (
      <>
        <Welcome name={user.full_name} />
        <EmptyState
          icon={Upload}
          title="Start by uploading documents"
          action={
            canEdit && (
              <Button asChild>
                <Link to="/documents">Upload documents</Link>
              </Button>
            )
          }
        >
          Upload job adverts, policy, institutional and academic documents. Once they are processed,
          create an analysis session to discover candidate course topics.
        </EmptyState>
        {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}
      </>
    )
  }

  return (
    <>
      <Welcome
        name={user.full_name}
        action={
          canEdit &&
          review && (
            <Button size="lg" asChild>
              <Link to={`/sessions/${review.id}/recommendations?decision=undecided`}>
                Continue reviewing <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          )
        }
      >
        {canEdit && review && (
          <>
            <strong className="text-ink">
              {review.undecided} topic{review.undecided === 1 ? '' : 's'}
            </strong>{' '}
            not reviewed yet in “{review.session_name}”.
          </>
        )}
      </Welcome>

      {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={File}
          tone="terracotta"
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
          icon={Search}
          tone="amber"
          label="Analyses"
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
          icon={ListChecks}
          tone="teal"
          label="Awaiting review"
          value={data.recommendations.pending_review}
          to={review ? `/sessions/${review.id}/recommendations?decision=undecided` : '/sessions'}
          linkHint={review ? `Review ${review.session_name}` : 'Analyses'}
          detail={
            review ? (
              <>
                {review.undecided} not reviewed yet in “{review.session_name}”
              </>
            ) : (
              <>
                of {data.recommendations.total} recommendation
                {data.recommendations.total === 1 ? '' : 's'} · {data.recommendations.accepted}{' '}
                accepted
              </>
            )
          }
        />
        <StatTile
          icon={BookOpen}
          tone="plum"
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

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <RecentSessions data={data} />
        <div className="flex flex-col gap-4">
          <HowThisWorks />
          {canEdit ? <QuickActions data={data} /> : <ReadOnlySummary data={data} />}
        </div>
      </div>
    </>
  )
}

function RecentSessions({ data }: { data: DashboardSummary }) {
  const { canEdit } = useAuth()
  return (
    <section
      aria-labelledby="recent-sessions"
      className="self-start rounded-[20px] border border-line bg-white px-6 py-[22px]"
    >
      <div className="mb-2 flex items-center justify-between">
        <h3 id="recent-sessions" className="card-title">
          Recent sessions
        </h3>
        <Link to="/sessions" className="text-[13px] font-bold text-primary hover:underline">
          See all
        </Link>
      </div>
      {data.recent_sessions.length === 0 ? (
        <p className="text-sm text-body-soft">
          No analysis sessions yet.
          {canEdit && (
            <>
              {' '}
              <Link to="/sessions/new" className="font-bold text-primary hover:underline">
                Create one
              </Link>{' '}
              from the ready documents.
            </>
          )}
        </p>
      ) : (
        <Table aria-label="Recent sessions">
          <TableHeader className="sr-only">
            <TableRow>
              <TableHead>Session</TableHead>
              <TableHead className="w-32">Status</TableHead>
              <TableHead className="w-20 text-right">
                <abbr title="Recommendations" className="no-underline">
                  Topics
                </abbr>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.recent_sessions.map((session) => (
              <TableRow key={session.id} className="hover:bg-transparent">
                <TableCell className="pl-0! whitespace-normal">
                  <Link
                    to={`/sessions/${session.id}`}
                    className="font-bold break-words text-ink hover:text-primary"
                  >
                    {session.session_name}
                  </Link>
                  <span className="mt-0.5 block text-xs text-muted-ink">
                    {formatDate(session.created_at)} · {session.document_count} document
                    {session.document_count === 1 ? '' : 's'}
                  </span>
                </TableCell>
                <TableCell className="w-36 whitespace-normal">
                  <SessionStatusBadge status={session.status} stage={session.current_stage} />
                </TableCell>
                <TableCell className="w-24 pr-0! text-right text-[13px] text-body tabular-nums">
                  <span className="font-bold text-ink">{session.recommendation_count}</span>{' '}
                  <span className="text-muted-ink">topics</span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}

function QuickActions({ data }: { data: DashboardSummary }) {
  const actions = [
    { to: '/documents', icon: Upload, label: 'Upload documents' },
    { to: '/sessions/new', icon: Plus, label: 'New analysis session' },
    { to: '/sessions', icon: Search, label: 'Review sessions' },
    { to: '/reports', icon: FileText, label: 'Reports' },
  ]
  return (
    <section
      aria-labelledby="quick-actions"
      className="flex flex-col gap-3 rounded-[20px] border border-line bg-white px-6 py-[22px]"
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
      className="flex flex-col gap-3 rounded-[20px] border border-line bg-white px-6 py-[22px]"
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
          <dt className="text-body-soft">Latest analysis</dt>
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
          <dd className="text-lg font-extrabold text-ink tabular-nums">
            {data.recommendations.accepted}
          </dd>
        </div>
        <div className="flex items-center justify-between pt-3">
          <dt className="text-body-soft">Proposed courses</dt>
          <dd className="text-lg font-extrabold text-ink tabular-nums">{data.courses_mapped}</dd>
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
    title: 'Review',
    text: 'Open a completed analysis session and read its ranked topics with their evidence. Accept, reject or mark each one to discuss later.',
  },
  {
    title: 'Design courses',
    text: 'For every accepted topic, click “Design course”. Give it a code, title, credit units and learning outcomes.',
  },
  {
    title: 'Report',
    text: 'When every accepted topic has a course, click “Download report”. You get a Word report with the evidence, decisions and proposed courses.',
  },
]

/**
 * A dismissible three-step introduction (remembered in this browser); the sidebar's "See how
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
      className="flex flex-col gap-3.5 rounded-[20px] bg-ink px-6 py-[22px] text-white"
    >
      <div className="flex items-center justify-between">
        <h3 id="how-this-works" className="text-base font-extrabold">
          How this works
        </h3>
        <button
          type="button"
          className="h-8 cursor-pointer rounded-lg px-1 text-[13px] font-bold text-amber hover:underline focus-visible:ring-2 focus-visible:ring-amber focus-visible:outline-none"
          aria-label="Hide “How this works”"
          onClick={dismiss}
        >
          Hide
        </button>
      </div>
      <ol className="flex flex-col gap-3.5 [counter-reset:how]">
        {HOW_STEPS.map((step, index) => (
          <li
            key={step.title}
            className="relative pl-[42px] [counter-increment:how] before:absolute before:top-0 before:left-0 before:flex before:size-[30px] before:items-center before:justify-center before:rounded-full before:bg-amber before:text-sm before:font-extrabold before:text-[#3d2600] before:content-[counter(how)]"
          >
            <p className="text-sm font-bold">
              <span className="sr-only">{index + 1}. </span>
              {step.title}
            </p>
            <p className="mt-0.5 text-[13px] leading-normal text-[#d9ccc2]">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

const TONES = {
  terracotta: 'bg-terracotta-tint text-terracotta',
  amber: 'bg-amber-tint text-[#8a5a00]',
  teal: 'bg-teal-tint text-teal',
  plum: 'bg-plum-tint text-plum',
} as const

/** A clickable headline number with its label and one line of context. */
function StatTile({
  icon: Icon,
  tone,
  label,
  value,
  detail,
  to,
  linkHint,
}: {
  icon: LucideIcon
  tone: keyof typeof TONES
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
      className="group flex flex-col gap-3.5 rounded-[20px] border border-line bg-white p-5 transition-colors hover:border-input-line hover:shadow-selected focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none"
    >
      <span className={cn('flex size-11 items-center justify-center rounded-xl', TONES[tone])}>
        <Icon className="size-5" strokeWidth={1.8} aria-hidden="true" />
      </span>
      <span className="flex flex-col gap-0.5">
        <span className="text-[30px] leading-tight font-extrabold tracking-[-0.02em] text-ink tabular-nums">
          {value.toLocaleString()}
        </span>
        <span className="text-sm font-bold text-ink">{label}</span>
        <span className="text-xs text-muted-ink">{detail}</span>
      </span>
    </Link>
  )
}

function NucCoreHint({ isAdmin }: { isAdmin: boolean }) {
  return (
    <Alert variant="warning" className="text-left">
      <AlertTriangle aria-hidden="true" />
      <AlertTitle>No active NUC core reference</AlertTitle>
      <AlertDescription>
        Sessions cannot run until an administrator uploads the NUC CCMAS core.
        {isAdmin && (
          <>
            {' '}
            <Link to="/admin/nuc-core">Upload it now</Link>.
          </>
        )}
      </AlertDescription>
    </Alert>
  )
}
