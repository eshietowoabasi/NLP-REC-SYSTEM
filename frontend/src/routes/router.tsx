import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'
import { DashboardPage } from '@/features/dashboard/DashboardPage'

import type { RouteHandle } from './handle'
import { NotFoundPage } from './NotFoundPage'

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
        handle: { title: 'Dashboard' } satisfies RouteHandle,
      },
      {
        path: '*',
        element: <NotFoundPage />,
        handle: { title: 'Not found' } satisfies RouteHandle,
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
