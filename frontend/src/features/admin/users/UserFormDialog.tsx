import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm, useWatch, type Control } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

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
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { newPasswordSchema } from '@/features/auth/passwordSchema'
import { applyServerErrors } from '@/lib/forms'
import { ROLE_DESCRIPTIONS, ROLE_LABELS, ROLES } from '@/lib/roles'
import type { User, UserRole } from '@/types/api'

import { useCreateUser, useUpdateUser } from './api'
import { ProgrammePicker } from './ProgrammePicker'

const roleSchema = z.enum(['admin', 'planner', 'viewer'])
const detailsSchema = z.object({
  full_name: z.string().trim().min(1, 'Enter the full name.').max(128),
  email: z.email('Enter a valid email address.').trim(),
  role: roleSchema,
  // Planners and viewers only reach these programmes; admins see every programme.
  programme_ids: z.array(z.number().int()),
})
const createSchema = detailsSchema.extend({
  username: z
    .string()
    .trim()
    .min(3, 'At least 3 characters.')
    .max(64)
    .regex(/^[A-Za-z0-9._-]+$/, 'Use letters, numbers, dots, dashes or underscores only.'),
  password: newPasswordSchema,
})

type CreateValues = z.infer<typeof createSchema>
type EditValues = z.infer<typeof detailsSchema>

interface UserFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** The user being edited; omit to create a new user. */
  user?: User
  /** True when the admin is editing their own account (role cannot be changed). */
  isSelf?: boolean
}

export function UserFormDialog({ open, onOpenChange, user, isSelf = false }: UserFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {open &&
          (user ? (
            <EditUserForm user={user} isSelf={isSelf} onDone={() => onOpenChange(false)} />
          ) : (
            <CreateUserForm onDone={() => onOpenChange(false)} />
          ))}
      </DialogContent>
    </Dialog>
  )
}

function RoleSelect({
  id,
  value,
  onChange,
  disabled,
}: {
  id: string
  value: UserRole
  onChange: (role: UserRole) => void
  disabled?: boolean
}) {
  return (
    <Select value={value} onValueChange={(next) => onChange(next as UserRole)} disabled={disabled}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {ROLES.map((role) => (
          <SelectItem key={role} value={role}>
            {ROLE_LABELS[role]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function CreateUserForm({ onDone }: { onDone: () => void }) {
  const createUser = useCreateUser()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      username: '',
      email: '',
      full_name: '',
      role: 'planner',
      password: '',
      programme_ids: [],
    },
  })
  const role = useWatch({ control, name: 'role' })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    createUser.mutate(values, {
      onSuccess: (created) => {
        toast.success(`User ${created.username} created.`)
        onDone()
      },
      onError: (error) =>
        setFormError(
          applyServerErrors(error, setError, [
            'username',
            'email',
            'full_name',
            'role',
            'password',
            'programme_ids',
          ]),
        ),
    })
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Add user</DialogTitle>
        <DialogDescription>
          The user signs in with this username or email and the initial password.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.full_name}>
          <FieldLabel htmlFor="full_name">Full name</FieldLabel>
          <Input id="full_name" aria-invalid={!!errors.full_name} {...register('full_name')} />
          <FieldError errors={[errors.full_name]} />
        </Field>
        <Field data-invalid={!!errors.username}>
          <FieldLabel htmlFor="username">Username</FieldLabel>
          <Input
            id="username"
            autoComplete="off"
            aria-invalid={!!errors.username}
            {...register('username')}
          />
          <FieldError errors={[errors.username]} />
        </Field>
        <Field data-invalid={!!errors.email}>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input id="email" type="email" aria-invalid={!!errors.email} {...register('email')} />
          <FieldError errors={[errors.email]} />
        </Field>
        <Field data-invalid={!!errors.role}>
          <FieldLabel htmlFor="role">Role</FieldLabel>
          <Controller
            control={control}
            name="role"
            render={({ field }) => (
              <RoleSelect id="role" value={field.value} onChange={field.onChange} />
            )}
          />
          <FieldDescription>{ROLE_DESCRIPTIONS[role]}</FieldDescription>
          <FieldError errors={[errors.role]} />
        </Field>
        <ProgrammesField
          control={control}
          role={role}
          id="programmes"
          error={errors.programme_ids}
        />
        <Field data-invalid={!!errors.password}>
          <FieldLabel htmlFor="password">Initial password</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            {...register('password')}
          />
          <FieldDescription>
            At least 8 characters. Share it securely; the user should change it after signing in.
          </FieldDescription>
          <FieldError errors={[errors.password]} />
        </Field>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={createUser.isPending}>
          {createUser.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Create user
        </Button>
      </DialogFooter>
    </form>
  )
}

function EditUserForm({
  user,
  isSelf,
  onDone,
}: {
  user: User
  isSelf: boolean
  onDone: () => void
}) {
  const updateUser = useUpdateUser()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isDirty, dirtyFields },
  } = useForm<EditValues>({
    resolver: zodResolver(detailsSchema),
    defaultValues: {
      full_name: user.full_name,
      email: user.email,
      role: user.role,
      programme_ids: user.programmes.map((programme) => programme.id),
    },
  })
  const role = useWatch({ control, name: 'role' })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    // Send only what changed, so the audit log records exactly what the admin did.
    const changes = Object.fromEntries(
      (Object.keys(dirtyFields) as (keyof EditValues)[]).map((key) => [key, values[key]]),
    )
    updateUser.mutate(
      { id: user.id, changes },
      {
        onSuccess: () => {
          toast.success(`${values.full_name} updated.`)
          onDone()
        },
        onError: (error) =>
          setFormError(
            applyServerErrors(error, setError, ['full_name', 'email', 'role', 'programme_ids']),
          ),
      },
    )
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Edit {user.username}</DialogTitle>
        <DialogDescription>Change the user&apos;s details, role or programmes.</DialogDescription>
      </DialogHeader>
      <FieldGroup className="py-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={!!errors.full_name}>
          <FieldLabel htmlFor="edit_full_name">Full name</FieldLabel>
          <Input id="edit_full_name" aria-invalid={!!errors.full_name} {...register('full_name')} />
          <FieldError errors={[errors.full_name]} />
        </Field>
        <Field data-invalid={!!errors.email}>
          <FieldLabel htmlFor="edit_email">Email</FieldLabel>
          <Input
            id="edit_email"
            type="email"
            aria-invalid={!!errors.email}
            {...register('email')}
          />
          <FieldError errors={[errors.email]} />
        </Field>
        <Field data-invalid={!!errors.role}>
          <FieldLabel htmlFor="edit_role">Role</FieldLabel>
          <Controller
            control={control}
            name="role"
            render={({ field }) => (
              <RoleSelect
                id="edit_role"
                value={field.value}
                onChange={field.onChange}
                disabled={isSelf}
              />
            )}
          />
          <FieldDescription>
            {isSelf ? 'You cannot change your own role.' : ROLE_DESCRIPTIONS[role]}
          </FieldDescription>
          <FieldError errors={[errors.role]} />
        </Field>
        <ProgrammesField
          control={control}
          role={role}
          id="edit_programmes"
          error={errors.programme_ids}
        />
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={!isDirty || updateUser.isPending}>
          {updateUser.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
          Save changes
        </Button>
      </DialogFooter>
    </form>
  )
}

/** Programme ticks for planners and viewers; admins see every programme. */
function ProgrammesField({
  control,
  role,
  id,
  error,
}: {
  // Both forms share the programme_ids field.
  control: Control<EditValues> | Control<CreateValues>
  role: UserRole
  id: string
  error?: { message?: string }
}) {
  if (role === 'admin') {
    return (
      <Field>
        <FieldLabel>Programmes</FieldLabel>
        <FieldDescription>Admins see and manage every programme.</FieldDescription>
      </Field>
    )
  }
  return (
    <Field data-invalid={!!error}>
      <FieldLabel htmlFor={id}>Programmes</FieldLabel>
      <Controller
        control={control as Control<EditValues>}
        name="programme_ids"
        render={({ field }) => (
          <ProgrammePicker id={id} value={field.value} onChange={field.onChange} />
        )}
      />
      <FieldDescription>
        {role === 'planner'
          ? 'The programmes this planner can run reviews for.'
          : 'The programmes this viewer can read.'}{' '}
        They see general documents too.
      </FieldDescription>
      <FieldError errors={[error]} />
    </Field>
  )
}
