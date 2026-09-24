import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { RouterProvider } from 'react-router'

import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { currentUserQueryKey } from '@/features/auth/api'
import { setUnauthorizedHandler } from '@/lib/api'
import { createQueryClient } from '@/lib/query-client'
import { router } from '@/routes/router'

/** When any request gets 401 (session expired or ended elsewhere), show the login page. */
function useSessionExpiry(queryClient: QueryClient) {
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (queryClient.getQueryData(currentUserQueryKey)) {
        queryClient.removeQueries()
        queryClient.setQueryData(currentUserQueryKey, null)
      }
    })
    return () => setUnauthorizedHandler(null)
  }, [queryClient])
}

export function App() {
  const [queryClient] = useState(createQueryClient)
  useSessionExpiry(queryClient)

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={300}>
        <RouterProvider router={router} />
        <Toaster position="top-right" richColors closeButton />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
