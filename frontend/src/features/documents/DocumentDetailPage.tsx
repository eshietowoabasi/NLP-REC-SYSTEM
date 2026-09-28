import {
  AlertCircle,
  Archive,
  ArrowLeft,
  Download,
  ExternalLink,
  Loader2,
  Pencil,
  Trash2,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/useAuth'
import { ApiError } from '@/lib/api'
import { formatBytes, formatDate, formatDateTime, formatNumber } from '@/lib/format'
import { NotFoundPage } from '@/routes/NotFoundPage'
import type { DocumentDetail } from '@/types/api'

import { documentFileUrl, useDocument, usePassages } from './api'
import { DocumentActionDialogs, type DocumentAction } from './DocumentActionDialogs'
import { DocumentStatusBadge } from './DocumentStatusBadge'
import { EditDocumentDialog } from './EditDocumentDialog'
import { CATEGORY_BADGES, CATEGORY_LABELS, monthYear } from './labels'

export function DocumentDetailPage() {
  const params = useParams()
  const id = Number(params.documentId)
  const document = useDocument(id)

  if (
    !Number.isInteger(id) ||
    (document.error instanceof ApiError && document.error.status === 404)
  ) {
    return <NotFoundPage />
  }
  if (document.isPending) {
    return (
      <div className="mx-auto max-w-5xl space-y-4" aria-label="Loading document">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }
  if (document.isError) {
    return (
      <Alert variant="destructive" className="mx-auto max-w-5xl">
        <AlertTitle>Could not load the document</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>{document.error.message}</p>
          <Button variant="outline" size="sm" onClick={() => void document.refetch()}>
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  return <DocumentDetailView document={document.data} />
}

function DocumentDetailView({ document }: { document: DocumentDetail }) {
  const { canEdit, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [action, setAction] = useState<DocumentAction | null>(null)
  const [editing, setEditing] = useState(false)
  const status = document.processing_status
  const processing = status === 'uploaded' || status === 'parsing'
  const backTo = document.is_nuc_core && isAdmin ? '/admin/nuc-core' : '/documents'

  const subtitle = [document.source, monthYear(document.published_on)].filter(Boolean).join(' · ')
  const metadata: [string, ReactNode][] = [
    ['Source', document.source ?? 'Not given'],
    [
      'Original',
      document.source_url ? (
        <a
          href={document.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 break-all text-primary hover:underline"
        >
          {document.source_url}
          <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      ) : (
        'Not given'
      ),
    ],
    ['Published', formatDate(document.published_on, 'Not given')],
    ['File', document.original_filename],
    ['Type', document.file_type.toUpperCase()],
    ['Size', formatBytes(document.file_size)],
    ['Pages', document.page_count === null ? 'Not paginated' : String(document.page_count)],
    ['Words', formatNumber(document.word_count)],
    ['Extracts', String(document.passage_count)],
    ['Uploaded', `${formatDateTime(document.uploaded_at)} by ${document.uploaded_by.full_name}`],
    ['Processed', formatDateTime(document.parsed_at, 'Not yet')],
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <Link
        to={backTo}
        className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        {document.is_nuc_core ? 'NUC core reference' : 'Document library'}
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2.5">
          <h2 className="page-title break-words">{document.title}</h2>
          <div className="flex flex-wrap items-center gap-2 text-[13px] text-body">
            <Badge variant={CATEGORY_BADGES[document.source_category]}>
              {CATEGORY_LABELS[document.source_category]}
            </Badge>
            <DocumentStatusBadge status={status} />
            {subtitle && <span>From {subtitle}</span>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Button variant="outline" asChild>
            <a href={documentFileUrl(document.id)} download>
              <Download aria-hidden="true" /> Download
            </a>
          </Button>
          {canEdit && (
            <Button variant="outline" onClick={() => setEditing(true)}>
              <Pencil aria-hidden="true" /> Edit details
            </Button>
          )}
          {canEdit && !document.is_nuc_core && (
            <>
              {status !== 'archived' && (
                <Button
                  variant="outline"
                  disabled={processing}
                  onClick={() => setAction({ kind: 'archive', document })}
                >
                  <Archive aria-hidden="true" /> Archive
                </Button>
              )}
              <Button variant="destructive" onClick={() => setAction({ kind: 'delete', document })}>
                <Trash2 aria-hidden="true" /> Delete
              </Button>
            </>
          )}
        </div>
      </div>

      {processing && (
        <Alert variant="info">
          <Loader2 className="animate-spin" aria-hidden="true" />
          <AlertTitle>Processing</AlertTitle>
          <AlertDescription>
            The text is being extracted and analysed. This page updates automatically.
          </AlertDescription>
        </Alert>
      )}
      {status === 'failed' && (
        <Alert variant="destructive">
          <AlertCircle aria-hidden="true" />
          <AlertTitle>Processing failed</AlertTitle>
          <AlertDescription>{document.error_message}</AlertDescription>
        </Alert>
      )}

      <div className="grid items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-4">
          {status === 'ready' || status === 'archived' ? (
            <PassagesCard documentId={document.id} total={document.passage_count} />
          ) : null}
          {!document.is_nuc_core && <SessionsCard document={document} />}
        </div>
        <Card size="sm" className="lg:order-last">
          <CardHeader>
            <CardTitle>At a glance</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="flex flex-col gap-3 text-sm">
              {metadata.map(([label, value]) => (
                <div key={label} className="flex flex-col gap-0.5">
                  <dt className="text-body-soft">{label}</dt>
                  <dd className="font-bold break-words text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      </div>

      <EditDocumentDialog document={document} open={editing} onOpenChange={setEditing} />
      <DocumentActionDialogs
        action={action}
        onClose={() => setAction(null)}
        onDeleted={() => navigate('/documents', { replace: true })}
      />
    </div>
  )
}

function PassagesCard({ documentId, total }: { documentId: number; total: number }) {
  const [page, setPage] = useState(1)
  const passages = usePassages(documentId, page, total > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Extracted text</CardTitle>
        <CardDescription>
          The document split into {total} extract{total === 1 ? '' : 's'} of a few sentences each,
          as used for analysis and shown as evidence.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {total === 0 ? (
          <p className="text-sm text-muted-ink">No text could be read from this document.</p>
        ) : passages.isError ? (
          <p className="text-sm text-destructive">{passages.error.message}</p>
        ) : passages.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <>
            <ol className="space-y-2.5">
              {passages.data.items.map((passage) => (
                <li key={passage.id} className="flex gap-3.5 rounded-[14px] bg-sand px-4 py-3.5">
                  <span
                    className="flex size-7 shrink-0 items-center justify-center rounded-lg border border-line bg-white text-xs font-extrabold text-muted-ink tabular-nums"
                    aria-hidden="true"
                  >
                    {passage.position + 1}
                  </span>
                  <div className="min-w-0">
                    <div className="mb-1 flex gap-2 text-xs font-bold text-muted-ink">
                      <span>Extract {passage.position + 1}</span>
                      {passage.page_number !== null && <span>· Page {passage.page_number}</span>}
                    </div>
                    <p className="text-sm leading-relaxed text-[#2e2620]">{passage.text}</p>
                  </div>
                </li>
              ))}
            </ol>
            {passages.data.pagination.pages > 1 && (
              <PaginationControls
                pagination={passages.data.pagination}
                onPageChange={setPage}
                itemLabel="extracts"
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function SessionsCard({ document }: { document: DocumentDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Analysis sessions using this document</CardTitle>
      </CardHeader>
      <CardContent>
        {document.sessions.length === 0 ? (
          <p className="text-sm text-muted-ink">Not used in any analysis session yet.</p>
        ) : (
          <ul className="divide-y divide-divider text-sm">
            {document.sessions.map((session) => (
              <li key={session.id} className="flex justify-between gap-4 py-2.5">
                <Link
                  to={`/sessions/${session.id}`}
                  className="font-bold text-ink hover:text-primary"
                >
                  {session.session_name}
                </Link>
                <span className="text-muted-ink">
                  {session.status} · {formatDate(session.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
