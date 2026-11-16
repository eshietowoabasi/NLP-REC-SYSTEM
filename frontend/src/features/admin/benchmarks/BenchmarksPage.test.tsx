import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus } from '@/test/fixtures'
import { fail, mockApi, ok, type MockRequest } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { Programme } from '@/types/api'

const programme = (overrides: Partial<Programme> = {}): Programme => ({
  id: 2,
  name: 'Synthetic Nursing Science',
  discipline_code: 'NSC',
  faculty: 'Synthetic Faculty of Nursing',
  description: null,
  country: 'Nigeria',
  is_active: true,
  created_at: '2026-11-01T09:00:00Z',
  ...overrides,
})

function setup(current: Programme, patch: Parameters<typeof mockApi>[0][string]) {
  return mockApi({
    'GET /auth/me': ok(adminUser),
    'GET /health': ok(healthyStatus),
    'GET /programmes': ok([current]),
    'GET /programmes/:id/benchmarks': ok({
      programme: current,
      active: null,
      latest: null,
      versions: [],
    }),
    'PATCH /programmes/:id': patch,
  })
}

describe('BenchmarksPage', () => {
  it('lists retired programmes too and edits a programme', async () => {
    const server = setup(programme(), (request: MockRequest) =>
      ok({ ...programme(), ...(request.body as object) }),
    )
    const { user } = renderApp('/admin/benchmarks')

    await user.click(await screen.findByRole('button', { name: /Edit programme/ }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit programme' })
    await user.clear(within(dialog).getByLabelText('Faculty'))
    await user.type(within(dialog).getByLabelText('Faculty'), 'Synthetic College of Health')
    await user.click(within(dialog).getByRole('button', { name: 'Save programme' }))

    await waitFor(() => expect(server.calls('PATCH', '/programmes/2')).toHaveLength(1))
    expect(server.calls('PATCH', '/programmes/2')[0].body).toEqual({
      name: 'Synthetic Nursing Science',
      discipline_code: 'NSC',
      faculty: 'Synthetic College of Health',
      description: null,
    })
    expect(server.calls('GET', '/programmes')[0].params).toEqual({ include_inactive: true })
  })

  it('shows a duplicate name next to the field', async () => {
    setup(
      programme(),
      fail(409, 'CONFLICT', 'A programme with that name already exists.', {
        fields: { name: ['A programme with that name already exists.'] },
      }),
    )
    const { user } = renderApp('/admin/benchmarks')

    await user.click(await screen.findByRole('button', { name: /Edit programme/ }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit programme' })
    await user.type(within(dialog).getByLabelText('Name'), ' 2')
    await user.click(within(dialog).getByRole('button', { name: 'Save programme' }))

    expect(
      await within(dialog).findAllByText('A programme with that name already exists.'),
    ).not.toHaveLength(0)
  })

  it('retires a programme after confirmation and offers to restore a retired one', async () => {
    const server = setup(programme(), ok(programme({ is_active: false })))
    const { user } = renderApp('/admin/benchmarks')

    await user.click(await screen.findByRole('button', { name: /Retire programme/ }))
    const confirm = await screen.findByRole('alertdialog')
    await user.click(within(confirm).getByRole('button', { name: 'Retire programme' }))

    await waitFor(() =>
      expect(server.calls('PATCH', '/programmes/2')[0]?.body).toEqual({ is_active: false }),
    )
  })

  it('marks a retired programme', async () => {
    setup(programme({ is_active: false }), ok(programme()))
    renderApp('/admin/benchmarks')

    expect(await screen.findByText('Retired')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Restore programme/ })).toBeEnabled()
  })
})
