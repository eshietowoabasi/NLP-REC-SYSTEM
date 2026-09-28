import { AlertTriangle, BookOpen, CheckCircle2, FileBarChart, FilePlus } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCard,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { DownloadReportButton } from '@/features/reports/DownloadReportButton'
import type { ProposedCurriculum } from '@/types/api'

import { useCurriculum } from './api'
import {
  CompletedSessionGate,
  EmptyPanel,
  ErrorPanel,
  LoadingBlock,
  OverlapBadge,
  SessionReviewHeader,
} from './components'
import { formatOutOf100 } from './labels'

export function CurriculumPage() {
  const sessionId = Number(useParams().sessionId)
  return (
    <CompletedSessionGate sessionId={sessionId} title="Proposed courses">
      {(session) => (
        <div className="mx-auto max-w-6xl space-y-5">
          <SessionReviewHeader
            sessionId={session.id}
            sessionName={session.session_name}
            title="Proposed courses"
          />
          <CurriculumView sessionId={session.id} />
        </div>
      )}
    </CompletedSessionGate>
  )
}

function CurriculumView({ sessionId }: { sessionId: number }) {
  const curriculum = useCurriculum(sessionId)
  const { canEdit } = useAuth()
  if (curriculum.isPending) return <LoadingBlock label="Loading the proposed courses" />
  if (curriculum.isError) {
    return (
      <ErrorPanel
        title="Could not load the proposed courses"
        error={curriculum.error}
        onRetry={() => void curriculum.refetch()}
      />
    )
  }
  const data = curriculum.data
  if (data.courses.length === 0) {
    return (
      <EmptyPanel icon={BookOpen} title="No courses yet">
        Accept recommendations and design their courses; they appear here with their credit units.{' '}
        <Link to={`/sessions/${sessionId}/recommendations`} className="underline">
          Review recommendations
        </Link>
      </EmptyPanel>
    )
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="page-lead">Courses designed for accepted recommendations of this session.</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/reports?session=${sessionId}`}>
              <FileBarChart aria-hidden="true" /> Reports
            </Link>
          </Button>
          {canEdit && (
            <>
              <Button variant="outline" size="sm" asChild>
                <Link to={`/reports?session=${sessionId}&generate=1`}>
                  <FilePlus aria-hidden="true" /> More options…
                </Link>
              </Button>
              <DownloadReportButton sessionId={sessionId} size="sm" />
            </>
          )}
        </div>
      </div>
      <AllowanceCard curriculum={data} />
      <TableCard>
        <Table aria-label="Proposed courses">
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead className="min-w-44">Title</TableHead>
              <TableHead className="text-right">Units</TableHead>
              <TableHead>Prerequisites</TableHead>
              <TableHead className="min-w-72">Learning outcomes</TableHead>
              <TableHead>From recommendation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.courses.map((course) => (
              <TableRow key={course.id} className="align-top">
                <TableCell className="font-extrabold whitespace-nowrap">
                  {course.course_code}
                </TableCell>
                <TableCell className="font-bold whitespace-normal">{course.course_title}</TableCell>
                <TableCell className="text-right tabular-nums">{course.credit_units}</TableCell>
                <TableCell className="whitespace-normal">
                  {course.prerequisites.length ? course.prerequisites.join(', ') : '—'}
                </TableCell>
                <TableCell className="whitespace-normal">
                  <ul className="list-disc space-y-0.5 pl-4 text-body marker:text-faint">
                    {course.learning_outcomes.map((outcome) => (
                      <li key={outcome}>{outcome}</li>
                    ))}
                  </ul>
                </TableCell>
                <TableCell className="space-y-1 whitespace-normal">
                  <Link
                    to={`/recommendations/${course.recommendation.id}`}
                    className="block font-bold text-primary hover:underline"
                  >
                    #{course.recommendation.rank} {course.recommendation.topic_title}
                  </Link>
                  <span className="block text-xs text-muted-ink tabular-nums">
                    Score {formatOutOf100(course.recommendation.composite_score)}
                  </span>
                  <OverlapBadge status={course.recommendation.overlap_status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={2} className="font-extrabold">
                Total ({data.courses.length} course{data.courses.length === 1 ? '' : 's'})
              </TableCell>
              <TableCell className="text-right font-extrabold tabular-nums">
                {data.total_units}
              </TableCell>
              <TableCell colSpan={3} />
            </TableRow>
          </TableFooter>
        </Table>
      </TableCard>
    </div>
  )
}

/** A white tile with a label and one big number or line (ProposedCourses.dc.html). */
function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-[18px] border border-line bg-white px-5 py-[18px]">
      <span className="text-[13px] text-muted-ink">{label}</span>
      {children}
    </div>
  )
}

function AllowanceCard({ curriculum }: { curriculum: ProposedCurriculum }) {
  const { total_units: total, credit_unit_allowance: allowance } = curriculum
  const count = curriculum.courses.length
  const tiles = (
    <div className="grid gap-3.5 sm:grid-cols-3">
      <Tile label="Courses designed">
        <span className="text-[28px] font-extrabold text-ink tabular-nums">{count}</span>
      </Tile>
      <Tile label="Total credit units">
        <span className="text-[28px] font-extrabold text-ink tabular-nums">{total}</span>
      </Tile>
      <Tile label="Units available for the 30%">
        {allowance === null ? (
          <span className="text-base font-bold text-ink">Not set yet</span>
        ) : (
          <span className="text-[28px] font-extrabold text-ink tabular-nums">{allowance}</span>
        )}
      </Tile>
    </div>
  )
  if (allowance === null) {
    return (
      <div className="space-y-3">
        {tiles}
        <Card size="sm">
          <CardHeader>
            <CardTitle className="tabular-nums">{total} credit units proposed</CardTitle>
            <CardDescription>
              No 30% credit-unit allowance has been set, so the total cannot be checked against it.
              An administrator can set it in the system settings.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }
  const over = total > allowance
  return (
    <div className="space-y-3">
      {tiles}
      <Card size="sm">
        <CardHeader>
          <CardTitle className="tabular-nums">
            {total} of {allowance} credit units
          </CardTitle>
          <CardDescription>
            The university-designed 30% of the curriculum allows {allowance} credit units.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Progress
            value={Math.min((total / allowance) * 100, 100)}
            aria-label="Credit units used of the allowance"
          />
        </CardContent>
      </Card>
      {over ? (
        <Alert variant="destructive">
          <AlertTriangle aria-hidden="true" />
          <AlertTitle>Over the allowance by {total - allowance} units</AlertTitle>
          <AlertDescription>
            Remove courses or reduce credit units to fit the 30% allowance.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="success">
          <CheckCircle2 aria-hidden="true" />
          <AlertTitle>Within the allowance</AlertTitle>
          <AlertDescription>{allowance - total} credit units remain.</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
