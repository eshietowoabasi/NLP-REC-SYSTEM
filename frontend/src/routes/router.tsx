import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'
import { UsersPage } from '@/features/admin/users/UsersPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProfilePage } from '@/features/auth/ProfilePage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'

import { RequireAuth, RequireRole } from './guards'
import type { RouteHandle } from './handle'
import { NotFoundPage } from './NotFoundPage'

const title = (value: string) => ({ title: value }) satisfies RouteHandle

export const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage />, handle: title('Sign in') },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage />, handle: title('Dashboard') },
          { path: 'profile', element: <ProfilePage />, handle: title('Profile') },
          {
            path: 'admin',
            element: <RequireRole roles={['admin']} />,
            children: [{ path: 'users', element: <UsersPage />, handle: title('Users') }],
          },
          { path: '*', element: <NotFoundPage />, handle: title('Not found') },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
