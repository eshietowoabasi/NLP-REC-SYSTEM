import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import type { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { passwordWithConfirmSchema } from '@/features/auth/passwordSchema'
import { applyServerErrors } from '@/lib/forms'
import type { User } from '@/types/api'

import { useUpdateUser } from './api'

type ResetValues = z.infer<typeof passwordWithConfirmSchema>

interface ResetPasswordDialogProps {
  user: User | null
  onOpenChange: (open: boolean) => void
}

export function ResetPasswordDialog({ user, onOpenChange }: ResetPasswordDialogProps) {
  return (
    <Dialog open={user !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {user && <ResetPasswordForm user={user} onDone={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function ResetPasswordForm({ user, onDone }: { user: User; onDone: () => void }) {
  const updateUser = useUpdateUser()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<ResetValues>({
    resolver: zodResolver(passwordWithConfirmSchema),
    defaultValues: { new_password: '', confirm_password: '' },
  })

  const onSubmit = handleSubmit(({ new_password }) => {
    setFormError(null)
    updateUser.mutate(
      { id: user.id, changes: { new_password } },
      {
        onSuccess: () => {
          toast.success(`Password reset for ${user.username}. Their sessions have been ended.`)
          onDone()
        },
        onError: (error) => setFormError(applyServerErrors(error, setError, ['new_password'])),
      },
    )
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Reset password</DialogTitle>
        <DialogDescription>
          Set a new password for {user.full_name} ({user.username}). They will be signed out
          everywhere.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.new_password}>
          <FieldLabel htmlFor="reset_new_password">New password</FieldLabel>
          <Input
            id="reset_new_password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.new_password}
            {...register('new_password')}
          />
          <FieldError errors={[errors.new_password]} />
        </Field>
        <Field data-invalid={!!errors.confirm_password}>
          <FieldLabel htmlFor="reset_confirm_password">Confirm new password</FieldLabel>
          <Input
            id="reset_confirm_password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.confirm_password}
            {...register('confirm_password')}
          />
          <FieldError errors={[errors.confirm_password]} />
        </Field>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={updateUser.isPending}>
          {updateUser.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Reset password
        </Button>
      </DialogFooter>
    </form>
  )
}
