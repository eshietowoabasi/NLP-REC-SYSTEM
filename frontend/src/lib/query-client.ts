import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/lib/api'

/** Client errors (4xx) will not succeed on retry; network and 5xx errors might. */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status !== null && error.status < 500) return false
  return failureCount < 2
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetry,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
    },
  })
}
