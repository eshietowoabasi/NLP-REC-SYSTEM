import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, page, plannerUser } from '@/test/fixtures'
import { mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { AuditLogEntry } from '@/types/api'

/* Synthetic fixtures. */
const entries: AuditLogEntry[] = [
  {
    id: 2,
    created_at: '2026-09-25T09:00:00Z',
    user: { id: 2, full_name: 'Test Planner' },
    action_type: 'recommendation.decided',
    entity_type: 'recommendation',
    entity_id: '31',
    detail: { from: null, to: 'accepted' },
    ip_address: '127.0.0.1',
  },
  {
    id: 1,
    created_at: '2026-09-25T08:00:00Z',
    user: null,
    action_type: 'auth.login_failed',
    entity_type: null,
    entity_id: null,
    detail: {},
    ip_address: '10.0.0.5',
  },
]
const actions = ['auth.login', 'auth.login_failed', 'recommendation.decided', 'report.generated']

function auditApi() {
  return mockApi({
    'GET /auth/me': ok(adminUser),
    'GET /health': ok(healthyStatus),
    'GET /admin/users': ok(page([adminUser, plannerUser])),
    'GET /admin/audit-logs': ok({ ...page(entries), actions }),
  })
}

describe('AuditLogPage', () => {
  it('lists entries with user, action, entity and detail', async () => {
    auditApi()
    renderApp('/admin/audit-log')

    await screen.findByText('recommendation #31') // skeleton rows show until the data arrives
    const table = screen.getByRole('table', { name: 'Audit log' })
    const rows = within(table).getAllByRole('row')
    expect(within(rows[1]).getByText('recommendation.decided')).toBeInTheDocument()
    expect(within(rows[1]).getByText('recommendation #31')).toBeInTheDocument()
    expect(within(rows[1]).getByText('from: null · to: accepted')).toBeInTheDocument()
    expect(within(rows[2]).getByText('Anonymous')).toBeInTheDocument()
  })

  it('filters by user, area and dates, and exports the same filters', async () => {
    const server = auditApi()
    const { user } = renderApp('/admin/audit-log')

    await screen.findByRole('table', { name: 'Audit log' })
    await user.click(screen.getByRole('combobox', { name: 'User' }))
    await user.click(await screen.findByRole('option', { name: 'Test Planner' }))
    await user.click(screen.getByRole('combobox', { name: 'Action' }))
    await user.click(await screen.findByRole('option', { name: 'Sign-in (all)' }))
    await user.type(screen.getByLabelText('From'), '2026-09-01')

    await waitFor(() =>
      expect(server.calls('GET', '/admin/audit-logs').at(-1)?.params).toEqual({
        page: 1,
        per_page: 50,
        user_id: 2,
        action: 'auth',
        date_from: '2026-09-01',
      }),
    )
    expect(screen.getByRole('link', { name: /Export CSV/ })).toHaveAttribute(
      'href',
      '/api/admin/audit-logs/export?user_id=2&action=auth&date_from=2026-09-01',
    )
    await user.click(screen.getByRole('button', { name: /Clear filters/ }))
    expect(screen.getByRole('link', { name: /Export CSV/ })).toHaveAttribute(
      'href',
      '/api/admin/audit-logs/export',
    )
  })
})
