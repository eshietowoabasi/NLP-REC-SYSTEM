import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router'
import { z } from 'zod'

import { Logo } from '@/components/brand/Logo'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { apiGet, apiPost } from '@/lib/api'
import { applyServerErrors } from '@/lib/forms'
import type { LoginResponse, ProgrammeRef } from '@/types/api'

import { currentUserQueryKey, useCurrentUser } from './api'
import { AuthLayout } from './AuthLayout'
import { newPasswordSchema } from './passwordSchema'

const registerSchema = z
  .object({
    full_name: z.string().trim().min(1, 'Enter your name.').max(128),
    email: z.string().trim().email('Enter a valid email address.'),
    username: z
      .string()
      .trim()
      .regex(/^[A-Za-z0-9._-]{3,64}$/, '3 to 64 letters, numbers, dots, dashes or underscores.'),
    programme_id: z
      .number({ error: 'Choose your programme.' })
      .int()
      .positive('Choose your programme.'),
    password: newPasswordSchema,
    confirm_password: z.string(),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: 'Passwords do not match.',
    path: ['confirm_password'],
  })

type RegisterValues = z.infer<typeof registerSchema>

const inputClass = 'h-[50px] rounded-[14px] px-[18px]'

/** Create an account: a curriculum planner for one programme, signed in straight away. */
export function RegisterPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: currentUser } = useCurrentUser()
  const [formError, setFormError] = useState<string | null>(null)
  const programmes = useQuery({
    queryKey: ['auth', 'register', 'programmes'],
    queryFn: () => apiGet<ProgrammeRef[]>('/auth/register/programmes'),
  })
  const signUp = useMutation({
    mutationFn: (values: RegisterValues) =>
      apiPost<LoginResponse>('/auth/register', {
        full_name: values.full_name,
        email: values.email,
        username: values.username,
        password: values.password,
        programme_ids: [values.programme_id],
      }),
    onSuccess: ({ user }) => {
      queryClient.removeQueries()
      queryClient.setQueryData(currentUserQueryKey, user)
      void navigate('/', { replace: true })
    },
  })
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      email: '',
      username: '',
      programme_id: 0,
      password: '',
      confirm_password: '',
    },
  })

  if (currentUser) return <Navigate to="/" replace />

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    signUp.mutate(values, {
      onError: (error) => {
        setFormError(
          applyServerErrors(error, setError, ['full_name', 'email', 'username', 'password']),
        )
      },
    })
  })

  return (
    <AuthLayout>
      <Logo size={44} subtitle="University of Uyo · Department of Computer Science" />

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-[30px] leading-[1.08] font-extrabold tracking-[-0.035em] text-ink sm:text-[38px]">
            Create your account
          </h1>
          <p className="text-base leading-relaxed text-body-soft">
            For curriculum planners. You can start a review as soon as you are in.
          </p>
        </div>

        <form onSubmit={onSubmit} noValidate aria-label="Create account">
          <FieldGroup className="gap-4">
            {formError && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <Field data-invalid={!!errors.full_name}>
              <FieldLabel htmlFor="full_name">Full name</FieldLabel>
              <Input
                id="full_name"
                autoComplete="name"
                autoFocus
                className={inputClass}
                aria-invalid={!!errors.full_name}
                {...register('full_name')}
              />
              <FieldError errors={[errors.full_name]} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field data-invalid={!!errors.email}>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  className={inputClass}
                  aria-invalid={!!errors.email}
                  {...register('email')}
                />
                <FieldError errors={[errors.email]} />
              </Field>
              <Field data-invalid={!!errors.username}>
                <FieldLabel htmlFor="username">Username</FieldLabel>
                <Input
                  id="username"
                  autoComplete="username"
                  className={inputClass}
                  aria-invalid={!!errors.username}
                  {...register('username')}
                />
                <FieldError errors={[errors.username]} />
              </Field>
            </div>
            <Field data-invalid={!!errors.programme_id}>
              <FieldLabel htmlFor="programme_id">Your programme</FieldLabel>
              <select
                id="programme_id"
                className="h-[50px] w-full rounded-[14px] border border-input bg-white px-4 text-sm font-medium text-ink outline-none focus:border-ring focus:ring-3 focus:ring-ring/25"
                aria-invalid={!!errors.programme_id}
                disabled={programmes.isPending}
                {...register('programme_id', { valueAsNumber: true })}
              >
                <option value={0}>
                  {programmes.isPending ? 'Loading programmes…' : 'Choose a programme'}
                </option>
                {programmes.data?.map((programme) => (
                  <option key={programme.id} value={programme.id}>
                    {programme.name}
                  </option>
                ))}
              </select>
              <FieldDescription>
                Your reviews compare with this programme&apos;s NUC core.
              </FieldDescription>
              <FieldError errors={[errors.programme_id]} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field data-invalid={!!errors.password}>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  className={inputClass}
                  aria-invalid={!!errors.password}
                  {...register('password')}
                />
                <FieldError errors={[errors.password]} />
              </Field>
              <Field data-invalid={!!errors.confirm_password}>
                <FieldLabel htmlFor="confirm_password">Confirm password</FieldLabel>
                <Input
                  id="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  className={inputClass}
                  aria-invalid={!!errors.confirm_password}
                  {...register('confirm_password')}
                />
                <FieldError errors={[errors.confirm_password]} />
              </Field>
            </div>
            <Button
              type="submit"
              size="lg"
              className="h-14 w-full text-base"
              disabled={signUp.isPending}
            >
              {signUp.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
              Create account
              {!signUp.isPending && <ArrowRight aria-hidden="true" />}
            </Button>
          </FieldGroup>
        </form>
      </div>

      <p className="text-sm leading-normal text-body-soft">
        Already have an account?{' '}
        <Link to="/login" className="font-bold text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
