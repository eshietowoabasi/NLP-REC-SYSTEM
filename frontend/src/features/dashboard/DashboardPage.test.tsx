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
  recommendations: {
    total: 30,
    pending_review: 18,
    accepted: 7,
    rejected: 3,
    flagged: 2,
    review_session: null,
  },
  courses_mapped: 4,
  curriculum_session: null,
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
    // Every card is a link; without a session to review they fall back to the lists.
    const awaiting = screen.getByRole('link', { name: 'Awaiting review: 18. Reviews' })
    expect(awaiting).toHaveAttribute('href', '/sessions')
    expect(awaiting).toHaveTextContent('of 30 topics · 7 accepted')
    expect(screen.getByRole('link', { name: 'Courses designed: 4. Reports' })).toHaveTextContent(
      '2 reports generated',
    )
    const recent = screen.getByRole('table', { name: 'Recent sessions' })
    expect(within(recent).getByRole('link', { name: 'Synthetic 2026 review' })).toHaveAttribute(
      'href',
      '/sessions/5',
    )
    expect(screen.getByRole('link', { name: /New review/ })).toBeInTheDocument()
    expect(screen.getByText('NUC core: Synthetic core v1')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /^Good (morning|afternoon|evening), Test$/ }),
    ).toBeInTheDocument()
  })

  it('links the cards to the session awaiting review and its proposed curriculum', async () => {
    dashboardApi(
      plannerUser,
      summary({
        recommendations: {
          total: 30,
          pending_review: 18,
          accepted: 7,
          rejected: 3,
          flagged: 2,
          review_session: { id: 5, session_name: 'Synthetic 2026 review', undecided: 11 },
        },
        curriculum_session: { id: 4, session_name: 'Synthetic pilot' },
      }),
    )
    renderApp('/')

    const awaiting = await screen.findByRole('link', {
      name: 'Awaiting review: 18. Review Synthetic 2026 review',
    })
    expect(awaiting).toHaveAttribute('href', '/sessions/5/recommendations?decision=undecided')
    expect(awaiting).toHaveTextContent('11 not reviewed yet in “Synthetic 2026 review”')
    expect(
      screen.getByRole('link', {
        name: 'Courses designed: 4. Proposed courses of Synthetic pilot',
      }),
    ).toHaveAttribute('href', '/sessions/4/curriculum')
  })

  it('explains the five steps until the help is dismissed', async () => {
    window.localStorage.removeItem('nlprs.howThisWorks.dismissed')
    dashboardApi(plannerUser, summary())
    const { user, unmount } = renderApp('/')

    const help = await screen.findByRole('region', { name: 'How this works' })
    expect(
      within(help)
        .getAllByRole('listitem')
        .map((li) => li.firstChild?.textContent),
    ).toEqual(['1. Evidence', '2. Analyse', '3. Review', '4. Design courses', '5. Report'])
    await user.click(within(help).getByRole('button', { name: 'Hide “How this works”' }))
    expect(screen.queryByRole('region', { name: 'How this works' })).not.toBeInTheDocument()
    unmount()

    dashboardApi(plannerUser, summary())
    renderApp('/')
    await screen.findByRole('table', { name: 'Recent sessions' })
    expect(screen.queryByRole('region', { name: 'How this works' })).not.toBeInTheDocument()
    window.localStorage.removeItem('nlprs.howThisWorks.dismissed')
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

    expect(await screen.findByText('Start by gathering evidence')).toBeInTheDocument()
    expect(screen.getByText('No active NUC core reference')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Upload it now' })).toHaveAttribute(
      'href',
      '/admin/benchmarks',
    )
  })

  it('shows viewers a read-only summary instead of the next steps', async () => {
    dashboardApi(
      viewerUser,
      summary({
        recommendations: {
          total: 30,
          pending_review: 18,
          accepted: 7,
          rejected: 3,
          flagged: 2,
          review_session: { id: 5, session_name: 'Synthetic 2026 review', undecided: 11 },
        },
      }),
    )
    renderApp('/')

    await screen.findByRole('table', { name: 'Recent sessions' })
    expect(screen.queryByRole('link', { name: /New review/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Upload documents/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Continue reviewing/ })).not.toBeInTheDocument()
    const readOnly = screen.getByRole('region', { name: 'Summary' })
    expect(within(readOnly).getByRole('link', { name: 'Synthetic 2026 review' })).toHaveAttribute(
      'href',
      '/sessions/5',
    )
    expect(within(readOnly).getByText('Accepted topics').nextSibling).toHaveTextContent('7')
    expect(within(readOnly).getByText('Proposed courses').nextSibling).toHaveTextContent('4')
  })

  it('offers editors the next step: continue reviewing', async () => {
    dashboardApi(
      plannerUser,
      summary({
        recommendations: {
          total: 30,
          pending_review: 18,
          accepted: 7,
          rejected: 3,
          flagged: 2,
          review_session: { id: 5, session_name: 'Synthetic 2026 review', undecided: 11 },
        },
      }),
    )
    renderApp('/')

    expect(await screen.findByRole('link', { name: /Continue reviewing/ })).toHaveAttribute(
      'href',
      '/sessions/5/recommendations?decision=undecided',
    )
  })

  it('follows the programme chosen in the sidebar and says what it lacks', async () => {
    const server = mockApi({
      'GET /auth/me': ok(plannerUser),
      'GET /health': ok(healthyStatus),
      'GET /dashboard/summary': ok(summary()),
      'GET /programmes/:id/readiness': (_request, params) =>
        ok({
          programme_id: Number(params.id),
          nuc_core: null,
          discipline: { value: 'computing', name: 'Computing' },
          job_search: { ready: true, search_terms: ['developer'] },
          documents_ready: 12,
          planners: 2,
          ready: false,
        }),
    })
    renderApp('/')

    const readiness = await screen.findByRole('region', {
      name: 'Synthetic Computer Science needs setting up before a review',
    })
    expect(within(readiness).getByText('Not uploaded yet')).toBeInTheDocument()
    expect(within(readiness).getByText('An admin uploads the CCMAS document.')).toBeInTheDocument()
    expect(within(readiness).getByText('3 of 4 ready')).toBeInTheDocument()
    expect(server.calls('GET', '/dashboard/summary')[0].params).toEqual({ programme_id: 1 })
    expect(
      screen.getByRole('button', { name: /Programme: Synthetic Computer Science/ }),
    ).toBeInTheDocument()
  })
})
