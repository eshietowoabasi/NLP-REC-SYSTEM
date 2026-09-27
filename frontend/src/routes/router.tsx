import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'

import { RequireAuth, RequireRole } from './guards'
import type { RouteHandle } from './handle'
import { NotFoundPage } from './NotFoundPage'

const title = (value: string) => ({ title: value }) satisfies RouteHandle

/*
 * Route-level code splitting: every screen is loaded on first visit, so the initial bundle
 * only holds the shell, the router and shared libraries. Each helper below maps a page
 * module to React Router's `lazy` route property.
 */
const page = <M,>(load: () => Promise<M>, pick: (module: M) => React.ComponentType) => ({
  lazy: () => load().then((module) => ({ Component: pick(module) })),
})

export const routes: RouteObject[] = [
  {
    path: '/login',
    ...page(
      () => import('@/features/auth/LoginPage'),
      (m) => m.LoginPage,
    ),
    handle: title('Sign in'),
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            index: true,
            ...page(
              () => import('@/features/dashboard/DashboardPage'),
              (m) => m.DashboardPage,
            ),
            handle: title('Dashboard'),
          },
          {
            path: 'profile',
            ...page(
              () => import('@/features/auth/ProfilePage'),
              (m) => m.ProfilePage,
            ),
            handle: title('Profile'),
          },
          {
            path: 'documents',
            ...page(
              () => import('@/features/documents/DocumentsPage'),
              (m) => m.DocumentsPage,
            ),
            handle: title('Documents'),
          },
          {
            path: 'documents/:documentId',
            ...page(
              () => import('@/features/documents/DocumentDetailPage'),
              (m) => m.DocumentDetailPage,
            ),
            handle: title('Document'),
          },
          {
            path: 'sessions',
            ...page(
              () => import('@/features/sessions/SessionsPage'),
              (m) => m.SessionsPage,
            ),
            handle: title('Analysis Sessions'),
          },
          {
            path: 'sessions/new',
            element: <RequireRole roles={['admin', 'planner']} />,
            children: [
              {
                index: true,
                ...page(
                  () => import('@/features/sessions/NewSessionPage'),
                  (m) => m.NewSessionPage,
                ),
                handle: title('New Session'),
              },
            ],
          },
          {
            path: 'sessions/:sessionId',
            ...page(
              () => import('@/features/sessions/SessionDetailPage'),
              (m) => m.SessionDetailPage,
            ),
            handle: title('Analysis Session'),
          },
          {
            path: 'sessions/:sessionId/evidence',
            ...page(
              () => import('@/features/review/EvidencePage'),
              (m) => m.EvidencePage,
            ),
            handle: title('Evidence'),
          },
          {
            path: 'sessions/:sessionId/recommendations',
            ...page(
              () => import('@/features/review/RecommendationsPage'),
              (m) => m.RecommendationsPage,
            ),
            handle: title('Recommendations'),
          },
          {
            path: 'sessions/:sessionId/curriculum',
            ...page(
              () => import('@/features/review/CurriculumPage'),
              (m) => m.CurriculumPage,
            ),
            handle: title('Proposed courses'),
          },
          {
            path: 'recommendations/:recommendationId',
            ...page(
              () => import('@/features/review/RecommendationDetailPage'),
              (m) => m.RecommendationDetailPage,
            ),
            handle: title('Recommendation'),
          },
          {
            path: 'recommendations/:recommendationId/mapping',
            element: <RequireRole roles={['admin', 'planner']} />,
            children: [
              {
                index: true,
                ...page(
                  () => import('@/features/review/MappingPage'),
                  (m) => m.MappingPage,
                ),
                handle: title('Design course'),
              },
            ],
          },
          {
            path: 'reports',
            ...page(
              () => import('@/features/reports/ReportsPage'),
              (m) => m.ReportsPage,
            ),
            handle: title('Reports'),
          },
          {
            path: 'admin',
            element: <RequireRole roles={['admin']} />,
            children: [
              {
                path: 'users',
                ...page(
                  () => import('@/features/admin/users/UsersPage'),
                  (m) => m.UsersPage,
                ),
                handle: title('Users'),
              },
              {
                path: 'nuc-core',
                ...page(
                  () => import('@/features/admin/nuc-core/NucCorePage'),
                  (m) => m.NucCorePage,
                ),
                handle: title('NUC Core Reference'),
              },
              {
                path: 'settings',
                ...page(
                  () => import('@/features/admin/settings/SettingsPage'),
                  (m) => m.SettingsPage,
                ),
                handle: title('Settings'),
              },
              {
                path: 'audit-log',
                ...page(
                  () => import('@/features/admin/audit/AuditLogPage'),
                  (m) => m.AuditLogPage,
                ),
                handle: title('Audit Log'),
              },
            ],
          },
          { path: '*', element: <NotFoundPage />, handle: title('Not found') },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
