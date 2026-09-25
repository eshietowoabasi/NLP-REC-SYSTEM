import { Loader2, Plus, Search, SpellCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import { ApiError } from '@/lib/api'
import { formatDate } from '@/lib/format'
import type { FieldErrorDetails, StopWord } from '@/types/api'

import { useAddStopWord, useStopWords, useToggleStopWord } from './api'

const PER_PAGE = 50
const WORD = /^[a-z0-9][a-z0-9+#.'-]{0,63}$/

export function StopWordsPanel() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<'all' | 'active' | 'inactive'>('all')
  const [page, setPage] = useState(1)
  const [draft, setDraft] = useState('')
  const [draftError, setDraftError] = useState<string | null>(null)
  const words = useStopWords({
    page,
    per_page: PER_PAGE,
    search: search.trim(),
    is_active: status === 'all' ? undefined : status === 'active',
  })
  const add = useAddStopWord()
  const toggle = useToggleStopWord()

  const onAdd = (event: FormEvent) => {
    event.preventDefault()
    const word = draft.trim().toLowerCase()
    if (!WORD.test(word)) {
      setDraftError("Enter a single word (letters, digits and + # . ' - only).")
      return
    }
    setDraftError(null)
    add.mutate(word, {
      onSuccess: (saved) => {
        toast.success(`"${saved.word}" added.`)
        setDraft('')
      },
      onError: (error) => {
        const fields =
          error instanceof ApiError ? (error.details as FieldErrorDetails).fields : null
        setDraftError(fields?.word?.join(' ') ?? error.message)
      },
    })
  }
  const flip = (word: StopWord) =>
    toggle.mutate(
      { id: word.id, is_active: !word.is_active },
      {
        onSuccess: (saved) =>
          toast.success(`"${saved.word}" ${saved.is_active ? 'activated' : 'deactivated'}.`),
        onError: (error) => toast.error(error.message),
      },
    )

  return (
    <div className="space-y-4">
      <p className="max-w-3xl text-sm text-muted-foreground">
        Domain words such as &ldquo;applicant&rdquo; or &ldquo;Lagos&rdquo; that say nothing about
        course content. Active stop words are left out of keywords and theme words in sessions run
        afterwards.
      </p>

      <form onSubmit={onAdd} noValidate className="flex flex-wrap items-start gap-2">
        <div className="grid gap-1.5">
          <Label htmlFor="new-stop-word">Add a stop word</Label>
          <Input
            id="new-stop-word"
            className="w-56"
            value={draft}
            aria-invalid={!!draftError}
            aria-describedby={draftError ? 'new-stop-word-error' : undefined}
            onChange={(event) => setDraft(event.target.value)}
          />
          {draftError && (
            <p id="new-stop-word-error" role="alert" className="text-sm text-destructive">
              {draftError}
            </p>
          )}
        </div>
        <Button type="submit" className="mt-6" disabled={add.isPending || !draft.trim()}>
          {add.isPending ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <Plus aria-hidden="true" />
          )}
          Add
        </Button>
      </form>

      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="stop-word-search">Search</Label>
          <div className="relative">
            <Search
              className="absolute top-2.5 left-2.5 size-4 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="stop-word-search"
              className="w-56 pl-8"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="stop-word-status">Status</Label>
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as typeof status)
              setPage(1)
            }}
          >
            <SelectTrigger id="stop-word-status" className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {words.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load stop words</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{words.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void words.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : words.isSuccess && words.data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center">
          <SpellCheck className="size-8 text-muted-foreground" aria-hidden="true" />
          <p className="font-medium">No stop words match</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table aria-label="Stop words">
            <TableHeader>
              <TableRow>
                <TableHead>Word</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Added</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {words.isPending
                ? Array.from({ length: 4 }, (_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={4}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : words.data.items.map((word) => (
                    <TableRow key={word.id}>
                      <TableCell className="font-medium">{word.word}</TableCell>
                      <TableCell>
                        {word.is_active ? (
                          <Badge variant="secondary">Active</Badge>
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground">
                            Inactive
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>{formatDate(word.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={toggle.isPending}
                          onClick={() => flip(word)}
                          aria-label={`${word.is_active ? 'Deactivate' : 'Activate'} "${word.word}"`}
                        >
                          {word.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>
        </div>
      )}
      {words.data && words.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={words.data.pagination}
          onPageChange={setPage}
          itemLabel="stop words"
        />
      )}
    </div>
  )
}
