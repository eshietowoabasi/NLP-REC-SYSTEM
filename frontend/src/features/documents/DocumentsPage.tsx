import { Archive, Download, Eye, FileUp, MoreHorizontal, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
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
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { DocumentStatus, DocumentSummary, UploadCategory } from '@/types/api'

import { documentFileUrl, useDocuments } from './api'
import { DocumentActionDialogs, type DocumentAction } from './DocumentActionDialogs'
import { DocumentStatusBadge } from './DocumentStatusBadge'
import { CATEGORY_LABELS, STATUS_LABELS, UPLOAD_CATEGORIES } from './labels'
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
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Document library</h2>
          <p className="text-sm text-muted-foreground">
            Source documents for analysis: job adverts, policy, institutional and academic
            documents.
          </p>
        </div>
        {canEdit && (
          <Button onClick={() => setUploadOpen(true)}>
            <FileUp aria-hidden="true" /> Upload documents
          </Button>
        )}
      </div>

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
              placeholder="Title or file name"
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
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Uploaded by</TableHead>
                <TableHead>Date</TableHead>
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
                    <TableCell colSpan={7}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : documents.data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
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
        </div>
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
    <Button
      variant={props.active ? 'default' : 'outline'}
      size="sm"
      aria-pressed={props.active}
      onClick={props.onClick}
    >
      {props.label}
      <Badge
        variant={props.active ? 'secondary' : 'outline'}
        className={cn('ml-1 px-1.5', props.active && 'bg-primary-foreground/20 text-inherit')}
      >
        {props.count}
      </Badge>
    </Button>
  )
}

function EmptyLibrary({ canEdit, onUpload }: { canEdit: boolean; onUpload: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
      <FileUp className="size-10 text-muted-foreground" aria-hidden="true" />
      <h3 className="text-lg font-semibold">No documents yet</h3>
      <p className="max-w-md text-sm text-muted-foreground">
        Start by uploading job adverts, policy, institutional and academic documents. Each file is
        processed in the background and becomes ready for analysis in a few moments.
      </p>
      {canEdit ? (
        <Button onClick={onUpload}>Upload documents</Button>
      ) : (
        <p className="text-sm text-muted-foreground">
          A curriculum planner or administrator can upload documents.
        </p>
      )}
    </div>
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
      <TableCell className="max-w-72">
        <Link
          to={`/documents/${document.id}`}
          className="block truncate font-medium text-foreground hover:underline"
        >
          {document.title}
        </Link>
        <span className="block truncate text-xs text-muted-foreground">
          {document.original_filename}
        </span>
      </TableCell>
      <TableCell>{CATEGORY_LABELS[document.source_category]}</TableCell>
      <TableCell className="uppercase">{document.file_type}</TableCell>
      <TableCell>{document.uploaded_by.full_name}</TableCell>
      <TableCell className="whitespace-nowrap">{formatDate(document.uploaded_at)}</TableCell>
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
