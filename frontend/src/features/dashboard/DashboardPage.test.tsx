import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, plannerUser, viewerUser } from '@/test/fixtures'
import { mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { DashboardSummary, User } from '@/types/api'

/* Synthetic fixtures. */
const summary = (overrides: Partial<DashboardSummary> = {}): DashboardSummary => ({
  documents: {
    total: 12,
    ready: 10,
    processing: 1,
    failed: 1,
    by_category: { job_market: 8, policy: 4 },
  },
  sessions: { total: 3, by_status: { pending: 0, processing: 1, completed: 2, failed: 0 } },
  recommendations: { total: 30, pending_review: 18, accepted: 7, rejected: 3, flagged: 2 },
  courses_mapped: 4,
  reports: 2,
  nuc_core_version: { id: 1, version_label: 'Synthetic core v1' },
  recent_sessions: [
    {
      id: 5,
      session_name: 'Synthetic 2026 review',
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      created_by: { id: 2, full_name: 'Test Planner' },
      document_count: 9,
      recommendation_count: 7,
      created_at: '2026-09-24T10:00:00Z',
      started_at: '2026-09-24T10:00:01Z',
      completed_at: '2026-09-24T10:00:40Z',
    },
  ],
  ...overrides,
})

function dashboardApi(user: User, data: DashboardSummary) {
  return mockApi({
    'GET /auth/me': ok(user),
    'GET /health': ok(healthyStatus),
    'GET /dashboard/summary': ok(data),
  })
}

describe('DashboardPage', () => {
  it('shows the headline counts, recent sessions and quick actions', async () => {
    dashboardApi(plannerUser, summary())
    renderApp('/')

    expect(await screen.findByRole('link', { name: 'Documents: 12' })).toHaveAttribute(
      'href',
      '/documents',
    )
    expect(screen.getByText('10 ready · 1 processing · 1 failed')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Awaiting review: 18' })).toHaveTextContent(
      'of 30 recommendations · 7 accepted',
    )
    expect(screen.getByRole('link', { name: 'Courses mapped: 4' })).toHaveTextContent(
      '2 reports generated',
    )
    const recent = screen.getByRole('table', { name: 'Recent sessions' })
    expect(within(recent).getByRole('link', { name: 'Synthetic 2026 review' })).toHaveAttribute(
      'href',
      '/sessions/5',
    )
    expect(screen.getByRole('link', { name: /New analysis session/ })).toBeInTheDocument()
    expect(screen.getByText('NUC core: Synthetic core v1')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Welcome, Test' })).toBeInTheDocument()
  })

  it('guides a first run and warns about a missing NUC core', async () => {
    dashboardApi(
      adminUser,
      summary({
        documents: { total: 0, ready: 0, processing: 0, failed: 0, by_category: {} },
        sessions: { total: 0, by_status: { pending: 0, processing: 0, completed: 0, failed: 0 } },
        nuc_core_version: null,
        recent_sessions: [],
      }),
    )
    renderApp('/')

    expect(await screen.findByText('Start by uploading documents')).toBeInTheDocument()
    expect(screen.getByText('No active NUC core reference')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Upload it now' })).toHaveAttribute(
      'href',
      '/admin/nuc-core',
    )
  })

  it('hides the create actions from viewers', async () => {
    dashboardApi(viewerUser, summary())
    renderApp('/')

    await screen.findByRole('table', { name: 'Recent sessions' })
    expect(screen.queryByRole('link', { name: /New analysis session/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Upload documents/ })).not.toBeInTheDocument()
    // The sidebar item and the quick action.
    expect(screen.getAllByRole('link', { name: 'Reports' })).toHaveLength(2)
  })
})
