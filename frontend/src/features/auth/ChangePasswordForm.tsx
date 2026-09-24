import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { applyServerErrors } from '@/lib/forms'

import { useChangePassword } from './api'
import { newPasswordSchema } from './passwordSchema'

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password.'),
    new_password: newPasswordSchema,
    confirm_password: z.string(),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: 'Passwords do not match.',
    path: ['confirm_password'],
  })
  .refine((values) => values.new_password !== values.current_password, {
    message: 'The new password must be different from the current one.',
    path: ['new_password'],
  })

type ChangePasswordValues = z.infer<typeof changePasswordSchema>

const EMPTY: ChangePasswordValues = { current_password: '', new_password: '', confirm_password: '' }

export function ChangePasswordForm() {
  const changePassword = useChangePassword()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: EMPTY,
  })

  const onSubmit = handleSubmit(({ current_password, new_password }) => {
    setFormError(null)
    changePassword.mutate(
      { current_password, new_password },
      {
        onSuccess: () => {
          reset(EMPTY)
          toast.success('Password changed. You have been signed out on other devices.')
        },
        onError: (error) =>
          setFormError(applyServerErrors(error, setError, ['current_password', 'new_password'])),
      },
    )
  })

  return (
    <form onSubmit={onSubmit} noValidate className="max-w-md">
      <FieldGroup>
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.current_password}>
          <FieldLabel htmlFor="current_password">Current password</FieldLabel>
          <Input
            id="current_password"
            type="password"
            autoComplete="current-password"
            aria-invalid={!!errors.current_password}
            {...register('current_password')}
          />
          <FieldError errors={[errors.current_password]} />
        </Field>
        <Field data-invalid={!!errors.new_password}>
          <FieldLabel htmlFor="new_password">New password</FieldLabel>
          <Input
            id="new_password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.new_password}
            {...register('new_password')}
          />
          <FieldDescription>At least 8 characters.</FieldDescription>
          <FieldError errors={[errors.new_password]} />
        </Field>
        <Field data-invalid={!!errors.confirm_password}>
          <FieldLabel htmlFor="confirm_password">Confirm new password</FieldLabel>
          <Input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.confirm_password}
            {...register('confirm_password')}
          />
          <FieldError errors={[errors.confirm_password]} />
        </Field>
        <div>
          <Button type="submit" disabled={changePassword.isPending}>
            {changePassword.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
            Change password
          </Button>
        </div>
      </FieldGroup>
    </form>
  )
}
