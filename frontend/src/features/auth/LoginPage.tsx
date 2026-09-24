import { zodResolver } from '@hookform/resolvers/zod'
import { GraduationCap, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
    <main className="flex min-h-svh items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mx-auto mb-2 flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="size-5" aria-hidden="true" />
          </div>
          <CardTitle className="text-xl">
            <h1>Sign in to NLP-RS</h1>
          </CardTitle>
          <CardDescription>Curriculum recommendation system</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate>
            <FieldGroup>
              {login.isError && (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{loginErrorMessage(login.error)}</AlertDescription>
                </Alert>
              )}
              <Field data-invalid={!!errors.identifier}>
                <FieldLabel htmlFor="identifier">Username or email</FieldLabel>
                <Input
                  id="identifier"
                  autoComplete="username"
                  autoFocus
                  aria-invalid={!!errors.identifier}
                  {...register('identifier')}
                />
                <FieldError errors={[errors.identifier]} />
              </Field>
              <Field data-invalid={!!errors.password}>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={!!errors.password}
                  {...register('password')}
                />
                <FieldError errors={[errors.password]} />
              </Field>
              <Button type="submit" className="w-full" disabled={login.isPending}>
                {login.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
                Sign in
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Accounts are created by an administrator.
              </p>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
