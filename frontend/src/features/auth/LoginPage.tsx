import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'

import { Logo } from '@/components/brand/Logo'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { safeNextPath } from '@/routes/next-path'

import { useCurrentUser, useLogin } from './api'
import { AuthLayout } from './AuthLayout'

const loginSchema = z.object({
  identifier: z.string().trim().min(1, 'Enter your username or email.'),
  password: z.string().min(1, 'Enter your password.'),
})

type LoginValues = z.infer<typeof loginSchema>

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'NETWORK_ERROR') return 'Cannot reach the server. Check your connection.'
    return error.message
  }
  return 'Something went wrong. Please try again.'
}

/** Sign-in (Login.dc.html). */
export function LoginPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const next = safeNextPath(searchParams.get('next'))
  const { data: currentUser } = useCurrentUser()
  const login = useLogin()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: '', password: '' },
  })

  if (currentUser) return <Navigate to={next} replace />

  const onSubmit = handleSubmit((values) => {
    login.mutate(values, { onSuccess: () => navigate(next, { replace: true }) })
  })

  return (
    <AuthLayout>
      <Logo size={44} subtitle="University of Uyo · Department of Computer Science" />

      <div className="flex flex-col gap-[30px]">
        <div className="flex flex-col gap-2.5">
          <h1 className="text-[34px] leading-[1.08] font-extrabold tracking-[-0.035em] text-ink sm:text-[44px]">
            Sign in to SkillBridge
          </h1>
          <p className="text-base leading-relaxed text-body-soft">
            Curriculum recommendation system
          </p>
        </div>

        <form onSubmit={onSubmit} noValidate>
          <FieldGroup className="gap-[18px]">
            {login.isError && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{loginErrorMessage(login.error)}</AlertDescription>
              </Alert>
            )}
            <Field data-invalid={!!errors.identifier}>
              <FieldLabel htmlFor="identifier" className="text-sm">
                Username or email
              </FieldLabel>
              <Input
                id="identifier"
                autoComplete="username"
                autoFocus
                className="h-[54px] rounded-[14px] px-[18px]"
                aria-invalid={!!errors.identifier}
                {...register('identifier')}
              />
              <FieldError errors={[errors.identifier]} />
            </Field>
            <Field data-invalid={!!errors.password}>
              <FieldLabel htmlFor="password" className="text-sm">
                Password
              </FieldLabel>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                className="h-[54px] rounded-[14px] px-[18px]"
                aria-invalid={!!errors.password}
                {...register('password')}
              />
              <FieldError errors={[errors.password]} />
            </Field>
            <Button
              type="submit"
              size="lg"
              className="h-14 w-full text-base"
              disabled={login.isPending}
            >
              {login.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
              Sign in
              {!login.isPending && <ArrowRight aria-hidden="true" />}
            </Button>
          </FieldGroup>
        </form>
      </div>

      <p className="text-sm leading-normal text-body-soft">
        New to SkillBridge?{' '}
        <Link to="/register" className="font-bold text-primary hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  )
}
