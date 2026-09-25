import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'
import { NucCorePage } from '@/features/admin/nuc-core/NucCorePage'
import { UsersPage } from '@/features/admin/users/UsersPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProfilePage } from '@/features/auth/ProfilePage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { DocumentDetailPage } from '@/features/documents/DocumentDetailPage'
import { DocumentsPage } from '@/features/documents/DocumentsPage'
import { CurriculumPage } from '@/features/review/CurriculumPage'
import { MappingPage } from '@/features/review/MappingPage'
import { RecommendationDetailPage } from '@/features/review/RecommendationDetailPage'
import { RecommendationsPage } from '@/features/review/RecommendationsPage'
import { NewSessionPage } from '@/features/sessions/NewSessionPage'
import { SessionDetailPage } from '@/features/sessions/SessionDetailPage'
import { SessionsPage } from '@/features/sessions/SessionsPage'

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
          { path: 'documents', element: <DocumentsPage />, handle: title('Documents') },
          { path: 'sessions', element: <SessionsPage />, handle: title('Analysis Sessions') },
          {
            path: 'sessions/new',
            element: <RequireRole roles={['admin', 'planner']} />,
            children: [{ index: true, element: <NewSessionPage />, handle: title('New Session') }],
          },
          {
            path: 'sessions/:sessionId',
            element: <SessionDetailPage />,
            handle: title('Analysis Session'),
          },
          {
            path: 'sessions/:sessionId/evidence',
            // Charts (Recharts) load only when the Evidence Dashboard is opened.
            lazy: () =>
              import('@/features/review/EvidencePage').then((m) => ({ Component: m.EvidencePage })),
            handle: title('Evidence'),
          },
          {
            path: 'sessions/:sessionId/recommendations',
            element: <RecommendationsPage />,
            handle: title('Recommendations'),
          },
          {
            path: 'sessions/:sessionId/curriculum',
            element: <CurriculumPage />,
            handle: title('Proposed Curriculum'),
          },
          {
            path: 'recommendations/:recommendationId',
            element: <RecommendationDetailPage />,
            handle: title('Recommendation'),
          },
          {
            path: 'recommendations/:recommendationId/mapping',
            element: <RequireRole roles={['admin', 'planner']} />,
            children: [
              { index: true, element: <MappingPage />, handle: title('Curriculum Mapping') },
            ],
          },
          {
            path: 'documents/:documentId',
            element: <DocumentDetailPage />,
            handle: title('Document'),
          },
          {
            path: 'admin',
            element: <RequireRole roles={['admin']} />,
            children: [
              { path: 'users', element: <UsersPage />, handle: title('Users') },
              {
                path: 'nuc-core',
                element: <NucCorePage />,
                handle: title('NUC Core Reference'),
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
