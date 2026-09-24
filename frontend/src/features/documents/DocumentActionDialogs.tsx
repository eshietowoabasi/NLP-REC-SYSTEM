import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { DocumentSummary } from '@/types/api'

import { useArchiveDocument, useDeleteDocument } from './api'

export type DocumentAction = { kind: 'archive' | 'delete'; document: DocumentSummary }

interface DocumentActionDialogsProps {
  action: DocumentAction | null
  onClose: () => void
  /** Called after a successful delete (e.g. to leave the detail page). */
  onDeleted?: () => void
}

/** Confirmation dialogs for archiving and deleting a document. */
export function DocumentActionDialogs({ action, onClose, onDeleted }: DocumentActionDialogsProps) {
  const archive = useArchiveDocument()
  const remove = useDeleteDocument()
  const pending = archive.isPending || remove.isPending
  const document = action?.document

  const confirm = () => {
    if (!action || !document) return
    if (action.kind === 'archive') {
      archive.mutate(document.id, {
        onSuccess: () => {
          toast.success(`“${document.title}” archived.`)
          onClose()
        },
        onError: (error) => toast.error(error.message),
      })
    } else {
      remove.mutate(document.id, {
        onSuccess: () => {
          toast.success(`“${document.title}” deleted.`)
          onClose()
          onDeleted?.()
        },
        // 409 when a session uses it: the message tells the user to archive instead.
        onError: (error) => {
          toast.error(error.message)
          onClose()
        },
      })
    }
  }

  const isDelete = action?.kind === 'delete'
  return (
    <AlertDialog open={action !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {isDelete ? 'Delete' : 'Archive'} “{document?.title}”?
          </AlertDialogTitle>
          <AlertDialogDescription>
            {isDelete
              ? 'The file and its extracted text are removed permanently. Documents used by an analysis session cannot be deleted; archive them instead.'
              : 'The document is hidden from the library and cannot be added to new sessions. Sessions that already used it keep it.'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant={isDelete ? 'destructive' : 'default'}
            disabled={pending}
            onClick={(event) => {
              event.preventDefault()
              confirm()
            }}
          >
            {isDelete ? 'Delete' : 'Archive'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
