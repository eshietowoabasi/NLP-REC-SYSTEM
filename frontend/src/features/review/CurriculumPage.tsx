import { AlertTriangle, BookOpen, CheckCircle2 } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { formatScore } from './labels'

export function CurriculumPage() {
  const sessionId = Number(useParams().sessionId)
  return (
    <CompletedSessionGate sessionId={sessionId} title="Proposed curriculum">
      {(session) => (
        <div className="mx-auto max-w-6xl space-y-6">
          <SessionReviewHeader
            sessionId={session.id}
            sessionName={session.session_name}
            title="Proposed curriculum"
          />
          <CurriculumView sessionId={session.id} />
        </div>
      )}
    </CompletedSessionGate>
  )
}

function CurriculumView({ sessionId }: { sessionId: number }) {
  const curriculum = useCurriculum(sessionId)
  if (curriculum.isPending) return <LoadingBlock label="Loading the proposed curriculum" />
  if (curriculum.isError) {
    return (
      <ErrorPanel
        title="Could not load the proposed curriculum"
        error={curriculum.error}
        onRetry={() => void curriculum.refetch()}
      />
    )
  }
  const data = curriculum.data
  if (data.courses.length === 0) {
    return (
      <EmptyPanel icon={BookOpen} title="No courses yet">
        Accept recommendations and map them to courses; they appear here with their credit units.{' '}
        <Link to={`/sessions/${sessionId}/recommendations`} className="underline">
          Review recommendations
        </Link>
      </EmptyPanel>
    )
  }
  return (
    <div className="space-y-6">
      <AllowanceCard curriculum={data} />
      <div className="overflow-x-auto rounded-lg border">
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
                <TableCell className="font-medium whitespace-nowrap">
                  {course.course_code}
                </TableCell>
                <TableCell className="whitespace-normal">{course.course_title}</TableCell>
                <TableCell className="text-right tabular-nums">{course.credit_units}</TableCell>
                <TableCell className="whitespace-normal">
                  {course.prerequisites.length ? course.prerequisites.join(', ') : '—'}
                </TableCell>
                <TableCell className="whitespace-normal">
                  <ul className="list-disc space-y-0.5 pl-4">
                    {course.learning_outcomes.map((outcome) => (
                      <li key={outcome}>{outcome}</li>
                    ))}
                  </ul>
                </TableCell>
                <TableCell className="space-y-1 whitespace-normal">
                  <Link
                    to={`/recommendations/${course.recommendation.id}`}
                    className="block hover:underline"
                  >
                    #{course.recommendation.rank} {course.recommendation.topic_title}
                  </Link>
                  <span className="block text-xs text-muted-foreground tabular-nums">
                    score {formatScore(course.recommendation.composite_score)}
                  </span>
                  <OverlapBadge status={course.recommendation.overlap_status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={2} className="font-medium">
                Total ({data.courses.length} course{data.courses.length === 1 ? '' : 's'})
              </TableCell>
              <TableCell className="text-right font-semibold tabular-nums">
                {data.total_units}
              </TableCell>
              <TableCell colSpan={3} />
            </TableRow>
          </TableFooter>
        </Table>
      </div>
    </div>
  )
}

function AllowanceCard({ curriculum }: { curriculum: ProposedCurriculum }) {
  const { total_units: total, credit_unit_allowance: allowance } = curriculum
  if (allowance === null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="tabular-nums">{total} credit units proposed</CardTitle>
          <CardDescription>
            No 30% credit-unit allowance has been set, so the total cannot be checked against it. An
            administrator can set it in the system settings.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }
  const over = total > allowance
  return (
    <div className="space-y-3">
      <Card>
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
        <Alert>
          <CheckCircle2 aria-hidden="true" className="text-emerald-600" />
          <AlertTitle>Within the allowance</AlertTitle>
          <AlertDescription>{allowance - total} credit units remain.</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
