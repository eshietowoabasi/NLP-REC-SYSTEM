import {
  AlertTriangle,
  BookOpenCheck,
  ChevronRight,
  FileBarChart,
  FileText,
  FlaskConical,
  Lightbulb,
  ListChecks,
  Plus,
  Upload,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
import { formatDate } from '@/lib/format'
import type { DashboardSummary } from '@/types/api'

import { useDashboardSummary } from './api'

export function DashboardPage() {
  const summary = useDashboardSummary()
  const { user, isAdmin } = useAuth()

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">
          Welcome, {user.full_name.split(' ')[0]}
        </h2>
        <p className="max-w-prose text-sm text-muted-foreground">
          Evidence-based recommendations for the institution-designed 30% of the Computer Science
          curriculum under the NUC CCMAS framework.
        </p>
      </section>

      <HowThisWorks />

      {summary.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Loading summary">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : summary.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load the dashboard</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{summary.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void summary.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
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

function Overview({ data }: { data: DashboardSummary }) {
  const { canEdit, isAdmin } = useAuth()
  const firstRun = data.documents.total === 0 && data.sessions.total === 0
  const review = data.recommendations.review_session
  const curriculum = data.curriculum_session

  if (firstRun) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
        <Upload className="size-10 text-muted-foreground" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Start by uploading documents</h3>
        <p className="max-w-md text-sm text-muted-foreground">
          Upload job adverts, policy, institutional and academic documents. Once they are processed,
          create an analysis session to discover candidate course topics.
        </p>
        {canEdit && (
          <Button asChild>
            <Link to="/documents">Upload documents</Link>
          </Button>
        )}
        {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={FileText}
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
          icon={FlaskConical}
          label="Analysis sessions"
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
          label="Awaiting review"
          value={data.recommendations.pending_review}
          to={review ? `/sessions/${review.id}/recommendations?decision=undecided` : '/sessions'}
          linkHint={review ? `Review ${review.session_name}` : 'Analysis sessions'}
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
          icon={BookOpenCheck}
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

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <Card>
          <CardHeader>
            <CardTitle>Recent sessions</CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_sessions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No analysis sessions yet.
                {canEdit && (
                  <>
                    {' '}
                    <Link to="/sessions/new" className="underline">
                      Create one
                    </Link>{' '}
                    from the ready documents.
                  </>
                )}
              </p>
            ) : (
              <Table aria-label="Recent sessions" className="table-fixed">
                <TableHeader>
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
                    <TableRow key={session.id}>
                      <TableCell className="whitespace-normal">
                        <Link
                          to={`/sessions/${session.id}`}
                          className="font-medium break-words hover:underline"
                        >
                          {session.session_name}
                        </Link>
                        <span className="block text-xs text-muted-foreground">
                          {formatDate(session.created_at)} · {session.document_count} document
                          {session.document_count === 1 ? '' : 's'}
                        </span>
                      </TableCell>
                      <TableCell className="whitespace-normal">
                        <SessionStatusBadge status={session.status} stage={session.current_stage} />
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {session.recommendation_count}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card className="self-start">
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
            <CardDescription>
              NUC core: {data.nuc_core_version?.version_label ?? 'not set'}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            {canEdit && (
              <>
                <Button variant="outline" className="justify-start" asChild>
                  <Link to="/documents">
                    <Upload aria-hidden="true" /> Upload documents
                  </Link>
                </Button>
                <Button variant="outline" className="justify-start" asChild>
                  <Link to="/sessions/new">
                    <Plus aria-hidden="true" /> New analysis session
                  </Link>
                </Button>
              </>
            )}
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/sessions">
                <FlaskConical aria-hidden="true" /> Review sessions
              </Link>
            </Button>
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/reports">
                <FileBarChart aria-hidden="true" /> Reports
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
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

/** A dismissible three-step introduction for first-time users (remembered in this browser). */
function HowThisWorks() {
  const [dismissed, setDismissed] = useState(readDismissed)
  if (dismissed) return null
  const dismiss = () => {
    setDismissed(true)
    try {
      window.localStorage.setItem(HELP_DISMISSED_KEY, '1')
    } catch {
      // Private mode or blocked storage: it simply shows again next time.
    }
  }
  return (
    <section
      aria-labelledby="how-this-works"
      className="relative rounded-lg border bg-muted/40 p-4 pr-12"
    >
      <h3 id="how-this-works" className="flex items-center gap-2 font-semibold">
        <Lightbulb className="size-4" aria-hidden="true" /> How this works
      </h3>
      <ol className="mt-3 grid gap-4 sm:grid-cols-3">
        {HOW_STEPS.map((step, index) => (
          <li key={step.title} className="space-y-1">
            <p className="text-sm font-medium">
              {index + 1}. {step.title}
            </p>
            <p className="text-sm text-muted-foreground">{step.text}</p>
          </li>
        ))}
      </ol>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2"
        aria-label="Hide “How this works”"
        onClick={dismiss}
      >
        <X aria-hidden="true" />
      </Button>
    </section>
  )
}

/** A clickable headline number with its label and one line of context. */
function StatTile({
  icon: Icon,
  label,
  value,
  detail,
  to,
  linkHint,
}: {
  icon: LucideIcon
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
      className="group rounded-xl focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
    >
      <Card className="h-full transition-colors group-hover:border-foreground/20 group-hover:bg-muted/40">
        <CardContent className="space-y-1">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Icon className="size-4" aria-hidden="true" /> {label}
            <ChevronRight
              className="ml-auto size-4 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
              aria-hidden="true"
            />
          </p>
          <p className="text-3xl font-semibold">{value.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">{detail}</p>
        </CardContent>
      </Card>
    </Link>
  )
}

function NucCoreHint({ isAdmin }: { isAdmin: boolean }) {
  return (
    <Alert className="text-left">
      <AlertTriangle aria-hidden="true" className="text-amber-600" />
      <AlertTitle>No active NUC core reference</AlertTitle>
      <AlertDescription>
        Sessions cannot run until an administrator uploads the NUC CCMAS core.
        {isAdmin && (
          <>
            {' '}
            <Link to="/admin/nuc-core" className="underline">
              Upload it now
            </Link>
            .
          </>
        )}
      </AlertDescription>
    </Alert>
  )
}
