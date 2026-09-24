import { Loader2 } from 'lucide-react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useCurrentUser } from '@/features/auth/api'
import { AuthUserContext } from '@/features/auth/context'
import { useAuth } from '@/features/auth/useAuth'
import type { UserRole } from '@/types/api'

import { ForbiddenPage } from './ForbiddenPage'

function FullPageMessage({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-svh items-center justify-center p-6">{children}</div>
}

/** Layout route: renders its children only for a logged-in user, else redirects to /login. */
export function RequireAuth() {
  const { data: user, isPending, isError, error, refetch } = useCurrentUser()
  const location = useLocation()

  if (isPending) {
    return (
      <FullPageMessage>
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="sr-only">Loading…</span>
      </FullPageMessage>
    )
  }
  if (isError) {
    return (
      <FullPageMessage>
        <Alert variant="destructive" className="max-w-md">
          <AlertTitle>Cannot reach NLP-RS</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>{error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      </FullPageMessage>
    )
  }
  if (!user) {
    const next = location.pathname + location.search
    const target = next === '/' ? '/login' : `/login?next=${encodeURIComponent(next)}`
    return <Navigate to={target} replace />
  }
  return (
    <AuthUserContext value={user}>
      <Outlet />
    </AuthUserContext>
  )
}

/** Layout route (inside RequireAuth): shows the 403 page unless the user has one of `roles`. */
export function RequireRole({ roles }: { roles: UserRole[] }) {
  const { hasRole } = useAuth()
  if (!hasRole(...roles)) return <ForbiddenPage />
  return <Outlet />
}
