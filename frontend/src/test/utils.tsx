import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { routes } from '@/routes/router'

/** A QueryClient with retries off so error states render immediately in tests. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  })
}

export function renderWithProviders(ui: ReactElement) {
  const queryClient = createTestQueryClient()
  return {
    user: userEvent.setup({ delay: null, applyAccept: false }),
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>{ui}</TooltipProvider>
      </QueryClientProvider>,
    ),
  }
}

/** Render the real application routes at `path` (mock the API with mockApi first). */
export function renderApp(path = '/') {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const queryClient = createTestQueryClient()
  return {
    user: userEvent.setup({ delay: null, applyAccept: false }),
    router,
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <RouterProvider router={router} />
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>,
    ),
  }
}
