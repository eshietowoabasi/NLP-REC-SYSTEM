import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'

import { RequireAuth, RequireRole } from './guards'
import type { RouteHandle } from './handle'
import { NotFoundPage } from './NotFoundPage'

const title = (value: string, crumb = 'Workspace') =>
  ({ title: value, crumb }) satisfies RouteHandle

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
            handle: title('Profile', 'Account'),
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
            handle: title('Document', 'Documents'),
          },
          {
            path: 'sessions',
            ...page(
              () => import('@/features/sessions/SessionsPage'),
              (m) => m.SessionsPage,
            ),
            handle: title('Analyses'),
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
                handle: title('New analysis', 'Analyses'),
              },
            ],
          },
          {
            path: 'sessions/:sessionId',
            ...page(
              () => import('@/features/sessions/SessionDetailPage'),
              (m) => m.SessionDetailPage,
            ),
            handle: title('Analysis', 'Analyses'),
          },
          {
            path: 'sessions/:sessionId/evidence',
            ...page(
              () => import('@/features/review/EvidencePage'),
              (m) => m.EvidencePage,
            ),
            handle: title('Evidence', 'Analyses'),
          },
          {
            path: 'sessions/:sessionId/recommendations',
            ...page(
              () => import('@/features/review/RecommendationsPage'),
              (m) => m.RecommendationsPage,
            ),
            handle: title('Suggested topics', 'Analyses'),
          },
          {
            path: 'sessions/:sessionId/curriculum',
            ...page(
              () => import('@/features/review/CurriculumPage'),
              (m) => m.CurriculumPage,
            ),
            handle: title('Proposed courses', 'Analyses'),
          },
          {
            path: 'recommendations/:recommendationId',
            ...page(
              () => import('@/features/review/RecommendationDetailPage'),
              (m) => m.RecommendationDetailPage,
            ),
            handle: title('Topic', 'Analyses'),
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
                handle: title('Design course', 'Analyses'),
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
                handle: title('Users', 'Administration'),
              },
              {
                path: 'benchmarks',
                ...page(
                  () => import('@/features/admin/benchmarks/BenchmarksPage'),
                  (m) => m.BenchmarksPage,
                ),
                handle: title(
                  'Curriculum benchmarks',
                  'Administration',
                ),
              },
              {
                path: 'nuc-core',
                ...page(
                  () => import('@/features/admin/nuc-core/NucCorePage'),
                  (m) => m.NucCorePage,
                ),
                handle: title('NUC core curriculum', 'Administration'),
              },
              {
                path: 'settings',
                ...page(
                  () => import('@/features/admin/settings/SettingsPage'),
                  (m) => m.SettingsPage,
                ),
                handle: title('Settings', 'Administration'),
              },
              {
                path: 'audit-log',
                ...page(
                  () => import('@/features/admin/audit/AuditLogPage'),
                  (m) => m.AuditLogPage,
                ),
                handle: title('Activity log', 'Administration'),
              },
            ],
          },
          { path: '*', element: <NotFoundPage />, handle: title('Not found', '') },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
