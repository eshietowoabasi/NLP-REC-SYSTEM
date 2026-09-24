import { AlertCircle, Archive, ArrowLeft, Download, Loader2, Trash2 } from 'lucide-react'
import { useState } from 'react'
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
import { CATEGORY_LABELS } from './labels'

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
  const status = document.processing_status
  const processing = status === 'uploaded' || status === 'parsing'
  const backTo = document.is_nuc_core && isAdmin ? '/admin/nuc-core' : '/documents'

  const metadata: [string, string][] = [
    ['File', document.original_filename],
    ['Type', document.file_type.toUpperCase()],
    ['Size', formatBytes(document.file_size)],
    ['Pages', document.page_count === null ? 'Not paginated' : String(document.page_count)],
    ['Words', formatNumber(document.word_count)],
    ['Passages', String(document.passage_count)],
    ['Uploaded', `${formatDateTime(document.uploaded_at)} by ${document.uploaded_by.full_name}`],
    ['Processed', formatDateTime(document.parsed_at, 'Not yet')],
  ]

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={backTo}>
          <ArrowLeft aria-hidden="true" />
          {document.is_nuc_core ? 'NUC core reference' : 'Document library'}
        </Link>
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight break-words">{document.title}</h2>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{CATEGORY_LABELS[document.source_category]}</Badge>
            <DocumentStatusBadge status={status} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <a href={documentFileUrl(document.id)} download>
              <Download aria-hidden="true" /> Download
            </a>
          </Button>
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
              <Button variant="outline" onClick={() => setAction({ kind: 'delete', document })}>
                <Trash2 aria-hidden="true" /> Delete
              </Button>
            </>
          )}
        </div>
      </div>

      {processing && (
        <Alert>
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

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[9rem_1fr]">
            {metadata.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="font-medium break-all">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      {status === 'ready' || status === 'archived' ? (
        <PassagesCard documentId={document.id} total={document.passage_count} />
      ) : null}

      {!document.is_nuc_core && <SessionsCard document={document} />}

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
          The document split into {total} passage{total === 1 ? '' : 's'} of a few sentences each,
          as used for analysis and shown as evidence.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {total === 0 ? (
          <p className="text-sm text-muted-foreground">No passages were extracted.</p>
        ) : passages.isError ? (
          <p className="text-sm text-destructive">{passages.error.message}</p>
        ) : passages.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <>
            <ol className="space-y-3">
              {passages.data.items.map((passage) => (
                <li key={passage.id} className="rounded-md border p-3">
                  <div className="mb-1 flex gap-2 text-xs text-muted-foreground">
                    <span>Passage {passage.position + 1}</span>
                    {passage.page_number !== null && <span>· Page {passage.page_number}</span>}
                  </div>
                  <p className="text-sm leading-relaxed">{passage.text}</p>
                </li>
              ))}
            </ol>
            {passages.data.pagination.pages > 1 && (
              <PaginationControls
                pagination={passages.data.pagination}
                onPageChange={setPage}
                itemLabel="passages"
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
          <p className="text-sm text-muted-foreground">Not used in any analysis session yet.</p>
        ) : (
          <ul className="divide-y text-sm">
            {document.sessions.map((session) => (
              <li key={session.id} className="flex justify-between gap-4 py-2">
                <span className="font-medium">{session.session_name}</span>
                <span className="text-muted-foreground">
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
