import { AlertTriangle, CheckCircle2, RefreshCw, XCircle } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { ServiceState } from '@/types/api'

import { useSystemHealth } from './api'

const SERVICES: { key: 'database' | 'redis'; label: string; purpose: string }[] = [
  { key: 'database', label: 'PostgreSQL', purpose: 'Documents, sessions and results' },
  { key: 'redis', label: 'Redis', purpose: 'Background job queue' },
]

function ServiceBadge({ state }: { state: ServiceState }) {
  return state === 'ok' ? (
    <Badge variant="secondary" className="gap-1 text-emerald-700 dark:text-emerald-400">
      <CheckCircle2 aria-hidden="true" /> Available
    </Badge>
  ) : (
    <Badge variant="destructive" className="gap-1">
      <XCircle aria-hidden="true" /> Unavailable
    </Badge>
  )
}

/** Detailed backend health: API reachability plus each dependency's state. */
export function SystemStatusCard() {
  const { data, isPending, isError, error, refetch, isFetching } = useSystemHealth()

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle>System status</CardTitle>
          <CardDescription>Live check of the API and the services it depends on.</CardDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void refetch()}
          disabled={isFetching}
          aria-label="Re-check system status"
        >
          <RefreshCw aria-hidden="true" className={isFetching ? 'animate-spin' : undefined} />
          Re-check
        </Button>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <div className="space-y-3" aria-label="Loading system status">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : isError ? (
          <Alert variant="destructive">
            <XCircle aria-hidden="true" />
            <AlertTitle>The API cannot be reached</AlertTitle>
            <AlertDescription>
              {error.message} Check that the backend container is running.
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-4">
            {data.status === 'degraded' && (
              <Alert>
                <AlertTriangle aria-hidden="true" />
                <AlertTitle>Some services are unavailable</AlertTitle>
                <AlertDescription>
                  Uploads and analysis will not work until every service is available.
                </AlertDescription>
              </Alert>
            )}
            <ul className="divide-y rounded-lg border">
              {SERVICES.map((service) => (
                <li key={service.key} className="flex items-center justify-between gap-4 p-3">
                  <div>
                    <p className="text-sm font-medium">{service.label}</p>
                    <p className="text-xs text-muted-foreground">{service.purpose}</p>
                  </div>
                  <ServiceBadge state={data.checks[service.key]} />
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">API version {data.version}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
