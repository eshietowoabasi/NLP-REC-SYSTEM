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
            handle: title('Home'),
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
            handle: title('Library'),
          },
          {
            path: 'documents/:documentId',
            ...page(
              () => import('@/features/documents/DocumentDetailPage'),
              (m) => m.DocumentDetailPage,
            ),
            handle: title('Document', 'Library'),
          },
          {
            path: 'sessions',
            ...page(
              () => import('@/features/sessions/SessionsPage'),
              (m) => m.SessionsPage,
            ),
            handle: title('Reviews'),
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
                handle: title('New review', 'Reviews'),
              },
            ],
          },
          {
            path: 'sessions/:sessionId',
            ...page(
              () => import('@/features/sessions/SessionDetailPage'),
              (m) => m.SessionDetailPage,
            ),
            handle: title('Review', 'Reviews'),
          },
          {
            path: 'sessions/:sessionId/evidence',
            ...page(
              () => import('@/features/review/EvidencePage'),
              (m) => m.EvidencePage,
            ),
            handle: title('Analysis results', 'Reviews'),
          },
          {
            path: 'sessions/:sessionId/recommendations',
            ...page(
              () => import('@/features/review/RecommendationsPage'),
              (m) => m.RecommendationsPage,
            ),
            handle: title('Review topics', 'Reviews'),
          },
          {
            path: 'sessions/:sessionId/curriculum',
            ...page(
              () => import('@/features/review/CurriculumPage'),
              (m) => m.CurriculumPage,
            ),
            handle: title('Design courses', 'Reviews'),
          },
          {
            path: 'sessions/:sessionId/report',
            ...page(
              () => import('@/features/review/ReportStepPage'),
              (m) => m.ReportStepPage,
            ),
            handle: title('Report', 'Reviews'),
          },
          {
            path: 'recommendations/:recommendationId',
            ...page(
              () => import('@/features/review/RecommendationDetailPage'),
              (m) => m.RecommendationDetailPage,
            ),
            handle: title('Topic', 'Reviews'),
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
                handle: title('Design course', 'Reviews'),
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
                handle: title('Users', 'Admin'),
              },
              {
                path: 'labour-market',
                ...page(
                  () => import('@/features/admin/labour-market/LabourMarketPage'),
                  (m) => m.LabourMarketPage,
                ),
                handle: title('Job collection', 'Admin'),
              },
              {
                path: 'benchmarks',
                ...page(
                  () => import('@/features/admin/programmes/ProgrammesPage'),
                  (m) => m.ProgrammesPage,
                ),
                handle: title('Programmes', 'Admin'),
              },
              {
                path: 'nuc-core',
                ...page(
                  () => import('@/features/admin/nuc-core/NucCorePage'),
                  (m) => m.NucCorePage,
                ),
                handle: title('NUC core curriculum', 'Admin'),
              },
              {
                path: 'settings',
                ...page(
                  () => import('@/features/admin/settings/SettingsPage'),
                  (m) => m.SettingsPage,
                ),
                handle: title('Settings', 'Admin'),
              },
              {
                path: 'audit-log',
                ...page(
                  () => import('@/features/admin/audit/AuditLogPage'),
                  (m) => m.AuditLogPage,
                ),
                handle: title('Activity log', 'Admin'),
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
