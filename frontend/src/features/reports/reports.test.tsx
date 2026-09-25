import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, page, plannerUser, viewerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { Report, SessionSummary, User } from '@/types/api'

/* Synthetic fixtures. */
const report = (overrides: Partial<Report> = {}): Report => ({
  id: 7,
  session: { id: 5, session_name: 'Synthetic 2026 review' },
  format: 'pdf',
  sections: [
    'corpus_summary',
    'nlp_findings',
    'overlap',
    'recommendations',
    'decisions',
    'proposed_courses',
  ],
  status: 'completed',
  error_message: null,
  file_size: 48_213,
  created_by: { id: 2, full_name: 'Test Planner' },
  created_at: '2026-09-25T10:00:00Z',
  completed_at: '2026-09-25T10:00:04Z',
  ...overrides,
})

const completedSession: SessionSummary = {
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
}

function reportsApi(user: User, extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    'GET /auth/me': ok(user),
    'GET /health': ok(healthyStatus),
    'GET /reports': ok(
      page([
        report(),
        report({
          id: 8,
          format: 'docx',
          sections: ['decisions'],
          status: 'failed',
          error_message: 'PDF generation is not available on this server.',
          file_size: null,
        }),
        report({ id: 9, status: 'processing', file_size: null }),
      ]),
    ),
    'GET /sessions': ok(page([completedSession])),
    ...extra,
  })
}

describe('ReportsPage', () => {
  it('lists reports with status, sections and a download link', async () => {
    reportsApi(plannerUser)
    renderApp('/reports')

    await screen.findAllByText('All sections') // skeleton rows show until the data arrives
    const table = screen.getByRole('table', { name: 'Reports' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('All sections')).toBeInTheDocument()
    expect(within(rows[0]).getByText('Ready')).toBeInTheDocument()
    expect(
      within(rows[0]).getByRole('link', { name: /Download PDF report of Synthetic 2026 review/ }),
    ).toHaveAttribute('href', '/api/reports/7/download')
    expect(within(rows[0]).getByText('47 KB')).toBeInTheDocument()
    expect(within(rows[1]).getByText('Decisions')).toBeInTheDocument()
    expect(within(rows[1]).getByText(/PDF generation is not available/)).toBeInTheDocument()
    expect(within(rows[2]).getByText('Generating')).toBeInTheDocument()
    expect(within(rows[2]).queryByRole('link', { name: /Download/ })).not.toBeInTheDocument()
    expect(within(rows[2]).queryByRole('button', { name: /Delete/ })).not.toBeInTheDocument()
  })

  it('generates a report with the chosen format and sections', async () => {
    const server = reportsApi(plannerUser, {
      'POST /sessions/:id/reports': ok(report({ id: 10, status: 'queued' }), 202),
    })
    const { user } = renderApp('/reports')

    await user.click(await screen.findByRole('button', { name: /Generate report/ }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Generate' }))
    expect(await within(dialog).findByText('Choose a completed session.')).toBeInTheDocument()

    await user.click(within(dialog).getByRole('combobox', { name: 'Session' }))
    await user.click(await screen.findByRole('option', { name: 'Synthetic 2026 review' }))
    await user.click(within(dialog).getByRole('radio', { name: 'Word (DOCX)' }))
    await user.click(within(dialog).getByRole('checkbox', { name: 'NLP findings' }))
    await user.click(within(dialog).getByRole('checkbox', { name: 'Overlap results' }))
    await user.click(within(dialog).getByRole('button', { name: 'Generate' }))

    await waitFor(() => expect(server.calls('POST', '/sessions/5/reports')).toHaveLength(1))
    expect(server.calls('POST', '/sessions/5/reports')[0].body).toEqual({
      format: 'docx',
      sections: ['corpus_summary', 'recommendations', 'decisions', 'proposed_courses'],
    })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('requires at least one section', async () => {
    const server = reportsApi(plannerUser)
    const { user } = renderApp('/reports?session=5&generate=1')

    const dialog = await screen.findByRole('dialog')
    for (const name of [
      'Corpus summary',
      'NLP findings',
      'Overlap results',
      'Recommendations',
      'Decisions',
      'Proposed courses',
    ]) {
      await user.click(within(dialog).getByRole('checkbox', { name }))
    }
    await user.click(within(dialog).getByRole('button', { name: 'Generate' }))

    expect(await within(dialog).findByText('Choose at least one section.')).toBeInTheDocument()
    expect(server.calls('POST', '/sessions/5/reports')).toHaveLength(0)
  })

  it('filters by session from the curriculum link and can clear it', async () => {
    const server = reportsApi(plannerUser)
    const { user } = renderApp('/reports?session=5')

    expect(await screen.findByText('Session: Synthetic 2026 review')).toBeInTheDocument()
    expect(server.calls('GET', '/reports')[0].params).toMatchObject({ session_id: 5 })
    await user.click(screen.getByRole('button', { name: 'Show reports of all sessions' }))

    await waitFor(() =>
      expect(server.calls('GET', '/reports').at(-1)?.params).not.toHaveProperty('session_id'),
    )
  })

  it('deletes a report after confirmation', async () => {
    const server = reportsApi(plannerUser, { 'DELETE /reports/:id': ok({ deleted: true }) })
    const { user } = renderApp('/reports')

    await user.click(
      await screen
        .findAllByRole('button', { name: 'Delete report of Synthetic 2026 review' })
        .then((buttons) => buttons[0]),
    )
    await user.click(await screen.findByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(server.calls('DELETE', '/reports/7')).toHaveLength(1))
  })

  it('lets viewers download but not generate or delete', async () => {
    reportsApi(viewerUser)
    renderApp('/reports')

    await screen.findAllByText('All sections')
    expect(screen.getAllByRole('link', { name: /Download/ })).toHaveLength(1)
    expect(screen.queryByRole('button', { name: /Generate report/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Delete report/ })).not.toBeInTheDocument()
  })

  it('shows an empty state and a load error', async () => {
    reportsApi(plannerUser, { 'GET /reports': ok(page([])) })
    const { unmount } = renderApp('/reports')
    expect(await screen.findByText('No reports yet')).toBeInTheDocument()
    unmount()

    reportsApi(plannerUser, { 'GET /reports': fail(500, 'INTERNAL_ERROR', 'Server problem.') })
    renderApp('/reports')
    expect(await screen.findByText('Could not load reports')).toBeInTheDocument()
  })
})
