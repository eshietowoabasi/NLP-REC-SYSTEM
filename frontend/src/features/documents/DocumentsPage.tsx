import { Archive, Download, Eye, FileUp, MoreHorizontal, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { EmptyState } from '@/components/shared/EmptyState'
import { FilterChip } from '@/components/shared/FilterChip'
import { PageHeader } from '@/components/shared/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCard,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { formatDate } from '@/lib/format'
import type { DocumentStatus, DocumentSummary, UploadCategory } from '@/types/api'

import { documentFileUrl, useDocuments } from './api'
import { DocumentActionDialogs, type DocumentAction } from './DocumentActionDialogs'
import { DocumentStatusBadge } from './DocumentStatusBadge'
import {
  CATEGORY_BADGES,
  CATEGORY_LABELS,
  documentType,
  monthYear,
  STATUS_LABELS,
  UPLOAD_CATEGORIES,
} from './labels'
import { UploadDialog } from './UploadDialog'

const PER_PAGE = 20
type StatusFilter = DocumentStatus | 'active'
const STATUS_FILTERS: StatusFilter[] = [
  'active',
  'ready',
  'parsing',
  'uploaded',
  'failed',
  'archived',
]

export function DocumentsPage() {
  const { canEdit } = useAuth()
  const [category, setCategory] = useState<UploadCategory | null>(null)
  const [status, setStatus] = useState<StatusFilter>('active')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [action, setAction] = useState<DocumentAction | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim())

  const documents = useDocuments({
    page,
    per_page: PER_PAGE,
    category: category ?? undefined,
    status: status === 'active' ? undefined : status,
    search: debouncedSearch || undefined,
  })

  const counts = documents.data?.category_counts
  const total = counts ? Object.values(counts).reduce((sum, n) => sum + n, 0) : 0
  const filtersActive = category !== null || status !== 'active' || debouncedSearch !== ''
  const libraryEmpty = !filtersActive && documents.data?.pagination.total === 0

  const chooseCategory = (next: UploadCategory | null) => {
    setCategory(next)
    setPage(1)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-[18px]">
      <PageHeader
        title="Document library"
        description="Source documents for analysis: job adverts, policy, institutional and academic documents."
        actions={
          canEdit && (
            <Button onClick={() => setUploadOpen(true)}>
              <FileUp aria-hidden="true" /> Upload documents
            </Button>
          )
        }
      />

      <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-2">
        <CategoryChip
          label="All"
          count={total}
          active={category === null}
          onClick={() => chooseCategory(null)}
        />
        {UPLOAD_CATEGORIES.map((value) => (
          <CategoryChip
            key={value}
            label={CATEGORY_LABELS[value]}
            count={counts?.[value] ?? 0}
            active={category === value}
            onClick={() => chooseCategory(value)}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-3" role="search">
        <div className="grid min-w-56 flex-1 gap-1.5">
          <Label htmlFor="document-search">Search</Label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="document-search"
              className="pl-8"
              placeholder="Search by title"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="document-status">Status</Label>
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as StatusFilter)
              setPage(1)
            }}
          >
            <SelectTrigger id="document-status" className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_FILTERS.map((value) => (
                <SelectItem key={value} value={value}>
                  {value === 'active' ? 'All (not archived)' : STATUS_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {documents.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load documents</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{documents.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void documents.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : libraryEmpty ? (
        <EmptyLibrary canEdit={canEdit} onUpload={() => setUploadOpen(true)} />
      ) : (
        <TableCard>
          <Table aria-label="Documents">
            <TableHeader>
              <TableRow>
                <TableHead>Document</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Uploaded by</TableHead>
                <TableHead>Added</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-12">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.isPending ? (
                Array.from({ length: 5 }, (_, index) => (
                  <TableRow key={index} aria-hidden="true">
                    <TableCell colSpan={6}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : documents.data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-ink">
                    No documents match these filters.
                  </TableCell>
                </TableRow>
              ) : (
                documents.data.items.map((document) => (
                  <DocumentRow
                    key={document.id}
                    document={document}
                    canEdit={canEdit}
                    onAction={setAction}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </TableCard>
      )}

      {documents.data && documents.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={documents.data.pagination}
          onPageChange={setPage}
          itemLabel="documents"
        />
      )}

      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
      <DocumentActionDialogs action={action} onClose={() => setAction(null)} />
    </div>
  )
}

function CategoryChip(props: {
  label: string
  count: number
  active: boolean
  onClick: () => void
}) {
  return (
    <FilterChip active={props.active} onClick={props.onClick} count={props.count}>
      {props.label}
    </FilterChip>
  )
}

function EmptyLibrary({ canEdit, onUpload }: { canEdit: boolean; onUpload: () => void }) {
  return (
    <EmptyState
      icon={FileUp}
      title="No documents yet"
      action={canEdit && <Button onClick={onUpload}>Upload documents</Button>}
    >
      <p>
        Start by uploading job adverts, policy, institutional and academic documents. Each file is
        processed in the background and becomes ready for analysis in a few moments.
      </p>
      {!canEdit && (
        <p className="mt-2">A curriculum planner or administrator can upload documents.</p>
      )}
    </EmptyState>
  )
}

function DocumentRow({
  document,
  canEdit,
  onAction,
}: {
  document: DocumentSummary
  canEdit: boolean
  onAction: (action: DocumentAction) => void
}) {
  const busy = document.processing_status === 'uploaded' || document.processing_status === 'parsing'
  return (
    <TableRow>
      <TableCell className="max-w-80">
        <Link
          to={`/documents/${document.id}`}
          className="block truncate font-bold text-ink hover:text-primary"
        >
          {document.title}
        </Link>
        <span className="block truncate text-xs text-muted-ink">
          {[document.source, monthYear(document.published_on)].filter(Boolean).join(' · ') ||
            'Source not given'}
        </span>
      </TableCell>
      <TableCell>
        <Badge variant={CATEGORY_BADGES[document.source_category]}>
          {documentType(document.source_category)}
        </Badge>
      </TableCell>
      <TableCell className="text-[13px] text-body">{document.uploaded_by.full_name}</TableCell>
      <TableCell className="text-[13px] whitespace-nowrap text-body">
        {formatDate(document.uploaded_at)}
      </TableCell>
      <TableCell>
        <DocumentStatusBadge
          status={document.processing_status}
          errorMessage={document.error_message}
        />
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label={`Actions for ${document.title}`}>
              <MoreHorizontal aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link to={`/documents/${document.id}`}>
                <Eye aria-hidden="true" /> View
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <a href={documentFileUrl(document.id)} download>
                <Download aria-hidden="true" /> Download original
              </a>
            </DropdownMenuItem>
            {canEdit && (
              <>
                <DropdownMenuSeparator />
                {document.processing_status !== 'archived' && (
                  <DropdownMenuItem
                    disabled={busy}
                    onSelect={() => onAction({ kind: 'archive', document })}
                  >
                    <Archive aria-hidden="true" /> Archive
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  variant="destructive"
                  onSelect={() => onAction({ kind: 'delete', document })}
                >
                  <Trash2 aria-hidden="true" /> Delete
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  )
}
