import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'

import { Logo } from '@/components/brand/Logo'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { safeNextPath } from '@/routes/next-path'

import { useCurrentUser, useLogin } from './api'

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

const STEPS = ['1 · Review', '2 · Design courses', '3 · Report']

/** Sign-in (Login.dc.html): the form on the left, the photo with a caption on the right. */
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
    <main className="flex min-h-svh gap-7 bg-sand p-4 sm:p-7">
      <div className="flex w-full flex-col justify-between gap-10 rounded-[28px] border-[1.5px] border-[#e8c9b6] bg-white px-6 py-8 sm:px-12 sm:py-12 lg:w-[620px] lg:shrink-0 lg:px-[72px]">
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

        <p className="text-[13px] leading-normal text-muted-ink">
          Accounts are created by an administrator.
        </p>
      </div>

      <div className="relative hidden flex-1 overflow-hidden rounded-[28px] bg-[#e9d8c8] lg:block">
        <img
          src="/assets/login-photo.jpg"
          alt="Two students reading a book together in a library"
          className="absolute inset-0 size-full object-cover"
        />
        <div className="absolute inset-x-7 bottom-7 flex flex-col gap-3.5 rounded-[22px] bg-ink/85 px-7 py-[26px] text-white">
          <p className="text-[26px] leading-tight font-extrabold tracking-[-0.02em]">
            Design the courses the job market is asking for.
          </p>
          <ul className="flex flex-wrap gap-2.5" aria-label="How it works">
            {STEPS.map((step) => (
              <li
                key={step}
                className="rounded-full bg-white/15 px-3 py-[7px] text-[13px] font-semibold"
              >
                {step}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </main>
  )
}
