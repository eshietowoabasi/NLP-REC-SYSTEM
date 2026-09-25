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

import { useDeleteSession } from './api'

interface DeleteSessionDialogProps {
  session: { id: number; session_name: string } | null
  onClose: () => void
  onDeleted?: () => void
}

export function DeleteSessionDialog({ session, onClose, onDeleted }: DeleteSessionDialogProps) {
  const remove = useDeleteSession()

  const confirm = () => {
    if (!session) return
    remove.mutate(session.id, {
      onSuccess: () => {
        toast.success(`“${session.session_name}” deleted.`)
        onClose()
        onDeleted?.()
      },
      onError: (error) => {
        toast.error(error.message)
        onClose()
      },
    })
  }

  return (
    <AlertDialog open={session !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete “{session?.session_name}”?</AlertDialogTitle>
          <AlertDialogDescription>
            Its results, recommendations, decisions and course mappings are removed permanently. The
            documents stay in the library.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={remove.isPending}
            onClick={(event) => {
              event.preventDefault()
              confirm()
            }}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
