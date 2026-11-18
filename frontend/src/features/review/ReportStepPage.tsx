import { AlertTriangle, Check, FileText, Settings2 } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { useAuth } from '@/features/auth/useAuth'
import { DownloadReportButton } from '@/features/reports/DownloadReportButton'
import type { SessionDetail, SessionProgress } from '@/types/api'

import { useSessionProgress } from './api'
import {
  CompletedSessionGate,
  ErrorPanel,
  LoadingBlock,
  SessionReviewHeader,
  StepFooter,
} from './components'

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`

/**
 * Report (step 5): what the report will contain, any review work still open, and one-click
 * PDF or Word downloads. Choosing sections and earlier reports stay on the Reports page.
 */
export function ReportStepPage() {
  const sessionId = Number(useParams().sessionId)
  return (
    <CompletedSessionGate sessionId={sessionId} title="Report">
      {(session) => (
        <div className="mx-auto max-w-6xl space-y-5">
          <SessionReviewHeader
            sessionId={session.id}
            sessionName={session.session_name}
            title="Report"
          />
          <ReportStep session={session} />
          <StepFooter sessionId={session.id} step={5} />
        </div>
      )}
    </CompletedSessionGate>
  )
}

function ReportStep({ session }: { session: SessionDetail }) {
  const progress = useSessionProgress(session.id, true)
  const { canEdit } = useAuth()
  if (progress.isPending) return <LoadingBlock label="Loading the review's progress" />
  if (progress.isError) {
    return (
      <ErrorPanel
        title="Could not load the review's progress"
        error={progress.error}
        onRetry={() => void progress.refetch()}
      />
    )
  }
  const p = progress.data
  const open = p.total - p.reviewed
  const noCourse = p.accepted - p.accepted_with_courses
  const contents = [
    `Evidence from ${plural(session.document_count, 'document')}`,
    `Every topic (${p.total}) with its decision: ${p.accepted} accepted, ${p.rejected} rejected, ${p.flagged} to discuss later`,
    `${plural(p.courses, 'proposed course')} with codes, units and learning outcomes`,
    'How each topic was scored and compared with the NUC core',
  ]
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section
        aria-labelledby="report-title"
        className="flex animate-rise flex-col gap-5 rounded-[18px] border border-line bg-white px-6 py-6"
      >
        <div className="flex items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-[12px] bg-sand-deep text-terracotta">
            <FileText className="size-6" aria-hidden="true" />
          </span>
          <div className="flex flex-col gap-1">
            <h3 id="report-title" className="text-xl font-extrabold text-ink">
              {open === 0 && noCourse === 0
                ? 'Your report is ready to download'
                : 'Download the report as it stands'}
            </h3>
            <p className="text-sm text-body-soft">
              {session.programme ? `For ${session.programme.name}, compared` : 'Compared'} with{' '}
              {session.nuc_core_version?.version_label ?? 'the NUC core'}.
            </p>
          </div>
        </div>
        <ul className="flex flex-col gap-2.5" aria-label="What the report contains">
          {contents.map((item) => (
            <li key={item} className="flex items-start gap-2.5 text-sm text-body">
              <Check
                className="mt-0.5 size-4 shrink-0 rounded-full bg-green-tint p-0.5 text-green-ink"
                aria-hidden="true"
              />
              {item}
            </li>
          ))}
        </ul>
        {(open > 0 || noCourse > 0) && <OpenWork progress={p} sessionId={session.id} />}
        {canEdit ? (
          <div className="flex flex-wrap gap-3">
            <DownloadReportButton sessionId={session.id} format="pdf">
              Download PDF
            </DownloadReportButton>
            <DownloadReportButton sessionId={session.id} format="docx" variant="outline">
              Download Word
            </DownloadReportButton>
          </div>
        ) : (
          <p className="text-sm text-body-soft">
            Planners generate reports. Reports already made for this review are on the{' '}
            <Link to={`/reports?session=${session.id}`} className="font-bold text-primary">
              Reports
            </Link>{' '}
            page.
          </p>
        )}
      </section>
      <aside className="flex flex-col gap-3 rounded-[18px] border border-line bg-white px-5 py-5">
        <h3 className="card-title">More options</h3>
        <p className="text-sm text-body-soft">
          Choose which sections to include, or download a report made earlier.
        </p>
        <Link
          to={`/reports?session=${session.id}${canEdit ? '&generate=1' : ''}`}
          className="inline-flex items-center gap-2 text-sm font-bold text-primary hover:underline"
        >
          <Settings2 className="size-4" aria-hidden="true" /> Reports for this review
        </Link>
      </aside>
    </div>
  )
}

function OpenWork({ progress: p, sessionId }: { progress: SessionProgress; sessionId: number }) {
  const open = p.total - p.reviewed
  const noCourse = p.accepted - p.accepted_with_courses
  return (
    <Alert variant="warning">
      <AlertTriangle aria-hidden="true" />
      <AlertDescription className="flex flex-col gap-1">
        {open > 0 && (
          <span>
            {plural(open, 'topic')} not reviewed yet.{' '}
            <Link
              to={`/sessions/${sessionId}/recommendations?decision=undecided`}
              className="font-bold underline"
            >
              Review them
            </Link>
          </span>
        )}
        {noCourse > 0 && (
          <span>
            {plural(noCourse, 'accepted topic')} without a course.{' '}
            <Link to={`/sessions/${sessionId}/curriculum`} className="font-bold underline">
              Design the courses
            </Link>
          </span>
        )}
      </AlertDescription>
    </Alert>
  )
}
