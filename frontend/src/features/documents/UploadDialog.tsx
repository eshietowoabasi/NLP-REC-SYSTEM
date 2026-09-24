import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileText, Loader2, Upload, X, XCircle } from 'lucide-react'
import { useId, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ApiError } from '@/lib/api'
import { formatBytes } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { RejectedFile, UploadCategory } from '@/types/api'

import { documentsQueryKey, uploadDocument } from './api'
import {
  ACCEPTED_EXTENSIONS,
  CATEGORY_HINTS,
  CATEGORY_LABELS,
  checkFile,
  UPLOAD_CATEGORIES,
} from './labels'

type RowStatus = 'waiting' | 'invalid' | 'uploading' | 'accepted' | 'rejected'

interface Row {
  key: string
  file: File
  category: UploadCategory | null
  status: RowStatus
  progress: number
  message: string | null
}

function rejectionReason(error: unknown): string {
  if (error instanceof ApiError) {
    const rejected = (error.details as { rejected?: RejectedFile[] }).rejected
    return rejected?.[0]?.reason ?? error.message
  }
  return 'Upload failed. Please try again.'
}

interface UploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function UploadDialog({ open, onOpenChange }: UploadDialogProps) {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()
  const [rows, setRows] = useState<Row[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)

  const update = (key: string, changes: Partial<Row>) =>
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...changes } : row)))

  const addFiles = (files: FileList | File[]) => {
    const added = Array.from(files).map((file, index): Row => {
      const problem = checkFile(file)
      return {
        key: `${file.name}-${file.size}-${file.lastModified}-${Date.now()}-${index}`,
        file,
        category: null,
        status: problem ? 'invalid' : 'waiting',
        progress: 0,
        message: problem,
      }
    })
    setRows((current) => [...current, ...added])
  }

  const waiting = rows.filter((row) => row.status === 'waiting')
  const missingCategory = waiting.some((row) => row.category === null)
  // "Done" only once something was actually sent (not when every file failed local checks).
  const sent = rows.some((row) => row.status === 'accepted' || row.status === 'rejected')
  const finished = sent && waiting.length === 0 && !uploading

  const setAll = (category: UploadCategory) =>
    setRows((current) =>
      current.map((row) => (row.status === 'waiting' ? { ...row, category } : row)),
    )

  const uploadAll = async () => {
    setUploading(true)
    for (const row of waiting) {
      if (!row.category) continue
      update(row.key, { status: 'uploading', progress: 0 })
      try {
        const result = await uploadDocument(row.file, row.category, (progress) =>
          update(row.key, { progress }),
        )
        const rejected = result.rejected[0]
        update(
          row.key,
          rejected
            ? { status: 'rejected', message: rejected.reason }
            : { status: 'accepted', progress: 1, message: 'Uploaded; processing has started.' },
        )
      } catch (error) {
        update(row.key, { status: 'rejected', message: rejectionReason(error) })
      }
    }
    setUploading(false)
    await queryClient.invalidateQueries({ queryKey: documentsQueryKey })
  }

  const close = (next: boolean) => {
    if (uploading) return
    if (!next) setRows([])
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upload documents</DialogTitle>
          <DialogDescription>
            PDF, DOCX or TXT, up to 25 MB each. Choose a category for every file. The NUC core
            reference is uploaded by an administrator on its own screen.
          </DialogDescription>
        </DialogHeader>

        <div
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            if (!uploading) addFiles(event.dataTransfer.files)
          }}
          className={cn(
            'flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors',
            dragging ? 'border-primary bg-primary/5' : 'border-border',
          )}
        >
          <Upload className="size-6 text-muted-foreground" aria-hidden="true" />
          <p className="text-sm">Drag files here, or</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            Choose files
          </Button>
          <label htmlFor={inputId} className="sr-only">
            Files to upload
          </label>
          <input
            id={inputId}
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED_EXTENSIONS.join(',')}
            className="hidden"
            onChange={(event) => {
              if (event.target.files) addFiles(event.target.files)
              event.target.value = ''
            }}
          />
        </div>

        {waiting.length > 1 && (
          <div className="flex items-center justify-end gap-2">
            <Label htmlFor="set-all-category" className="text-sm text-muted-foreground">
              Set all to
            </Label>
            <Select onValueChange={(value) => setAll(value as UploadCategory)}>
              <SelectTrigger id="set-all-category" className="w-44">
                <SelectValue placeholder="Category…" />
              </SelectTrigger>
              <SelectContent>
                {UPLOAD_CATEGORIES.map((category) => (
                  <SelectItem key={category} value={category}>
                    {CATEGORY_LABELS[category]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {rows.length > 0 && (
          <ul className="max-h-72 space-y-2 overflow-y-auto" aria-label="Selected files">
            {rows.map((row) => (
              <FileRow
                key={row.key}
                row={row}
                disabled={uploading}
                onCategory={(category) => update(row.key, { category })}
                onRemove={() => setRows((current) => current.filter((r) => r.key !== row.key))}
              />
            ))}
          </ul>
        )}

        <DialogFooter className="sm:items-center">
          {missingCategory && !uploading && (
            <p className="text-xs text-muted-foreground sm:mr-auto">
              Choose a category for each file to continue.
            </p>
          )}
          {finished ? (
            <Button onClick={() => close(false)}>Done</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => close(false)} disabled={uploading}>
                Cancel
              </Button>
              <Button
                onClick={() => void uploadAll()}
                disabled={uploading || waiting.length === 0 || missingCategory}
              >
                {uploading && <Loader2 className="animate-spin" aria-hidden="true" />}
                Upload{' '}
                {waiting.length > 0 ? `${waiting.length} file${waiting.length > 1 ? 's' : ''}` : ''}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface FileRowProps {
  row: Row
  disabled: boolean
  onCategory: (category: UploadCategory) => void
  onRemove: () => void
}

function FileRow({ row, disabled, onCategory, onRemove }: FileRowProps) {
  const selectId = useId()
  const editable = row.status === 'waiting'
  return (
    <li className="rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-3">
        <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{row.file.name}</p>
          <p className="text-xs text-muted-foreground">{formatBytes(row.file.size)}</p>
        </div>
        {editable && (
          <>
            <label htmlFor={selectId} className="sr-only">
              Category for {row.file.name}
            </label>
            <Select
              value={row.category ?? undefined}
              onValueChange={(value) => onCategory(value as UploadCategory)}
              disabled={disabled}
            >
              <SelectTrigger id={selectId} className="w-44">
                <SelectValue placeholder="Choose category" />
              </SelectTrigger>
              <SelectContent>
                {UPLOAD_CATEGORIES.map((category) => (
                  <SelectItem key={category} value={category}>
                    <span>{CATEGORY_LABELS[category]}</span>
                    <span className="sr-only"> — {CATEGORY_HINTS[category]}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        )}
        {(editable || row.status === 'invalid') && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onRemove}
            disabled={disabled}
            aria-label={`Remove ${row.file.name}`}
          >
            <X aria-hidden="true" />
          </Button>
        )}
      </div>
      {row.status === 'uploading' && (
        <Progress
          value={Math.round(row.progress * 100)}
          className="mt-2"
          aria-label={`Uploading ${row.file.name}`}
        />
      )}
      {row.message && (
        <p
          className={cn(
            'mt-2 flex items-start gap-1.5 text-xs',
            row.status === 'accepted'
              ? 'text-emerald-700 dark:text-emerald-400'
              : 'text-destructive',
          )}
        >
          {row.status === 'accepted' ? (
            <CheckCircle2 className="mt-px size-3.5 shrink-0" aria-hidden="true" />
          ) : (
            <XCircle className="mt-px size-3.5 shrink-0" aria-hidden="true" />
          )}
          {row.message}
        </p>
      )}
    </li>
  )
}
