import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, plannerUser } from '@/test/fixtures'
import { fail, mockApi, ok, type MockRequest } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { Paginated, Programme, ProgrammeReadiness, User } from '@/types/api'

const programme = (overrides: Partial<Programme> = {}): Programme => ({
  id: 2,
  name: 'Synthetic Nursing Science',
  discipline_code: 'NSC',
  faculty: 'Synthetic Faculty of Nursing',
  description: null,
  nuc_discipline: 'allied_health_sciences',
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

describe('ProgrammesPage', () => {
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
      nuc_discipline: 'allied_health_sciences',
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

    expect(
      await screen.findByRole('button', { name: 'Synthetic Nursing Science, Retired' }),
    ).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Restore programme/ })).toBeEnabled()
  })

  it('shows what each programme still needs and opens the tab that fixes it', async () => {
    const readiness: ProgrammeReadiness = {
      programme_id: 2,
      nuc_core: null,
      discipline: { value: 'allied_health_sciences', name: 'Allied Health Sciences' },
      job_search: { ready: true, search_terms: ['nurse', 'midwife'] },
      documents_ready: 2,
      planners: 1,
      ready: false,
    }
    mockApi({
      'GET /auth/me': ok(adminUser),
      'GET /health': ok(healthyStatus),
      'GET /programmes': ok([programme()]),
      'GET /programmes/readiness': ok([readiness]),
      'GET /programmes/:id/benchmarks': ok({
        programme: programme(),
        active: null,
        latest: null,
        versions: [],
      }),
    })
    const { user } = renderApp('/admin/benchmarks')

    expect(
      await screen.findByRole('button', { name: 'Synthetic Nursing Science, 2 of 4 ready' }),
    ).toBeInTheDocument()
    const setup = screen.getByRole('region', { name: 'Set up Synthetic Nursing Science' })
    expect(within(setup).getByText('NUC core').parentElement).toHaveTextContent('(missing)')
    expect(within(setup).getByText('Skills list').parentElement).toHaveTextContent('(done)')

    await user.click(within(setup).getByRole('button', { name: /Set up NUC core/ }))
    expect(await screen.findByRole('tab', { name: 'NUC core' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(await screen.findByText('No active curriculum benchmark')).toBeInTheDocument()
  })

  it('adds a planner to the programme and removes one', async () => {
    const member: User = { ...plannerUser, id: 8, full_name: 'Synthetic Member', programmes: [] }
    member.programmes = [{ id: 2, name: 'Synthetic Nursing Science', discipline_code: 'NSC' }]
    const other: User = {
      ...plannerUser,
      id: 9,
      full_name: 'Synthetic Newcomer',
      programmes: [{ id: 1, name: 'Synthetic Computer Science', discipline_code: 'CSC' }],
    }
    const page = (items: User[]): Paginated<User> => ({
      items,
      pagination: { page: 1, per_page: 100, total: items.length, pages: 1 },
    })
    const server = mockApi({
      'GET /auth/me': ok(adminUser),
      'GET /health': ok(healthyStatus),
      'GET /programmes': ok([programme()]),
      'GET /admin/users': (request: MockRequest) =>
        ok(page(request.params?.programme_id ? [member] : [adminUser, member, other])),
      'PATCH /admin/users/:id': (request: MockRequest) =>
        ok({ ...other, ...(request.body as object) }),
    })
    const { user } = renderApp('/admin/benchmarks?programme=2&tab=people')

    const people = await screen.findByRole('region', {
      name: 'People working on Synthetic Nursing Science',
    })
    expect(within(people).getByText('Synthetic Member')).toBeInTheDocument()
    expect(server.calls('GET', '/admin/users')[0].params).toMatchObject({ programme_id: 2 })

    await user.click(screen.getByRole('combobox', { name: 'Planner or viewer' }))
    // Admins reach every programme, so only planners and viewers are offered.
    expect(screen.queryByRole('option', { name: /Test Admin|Ada/ })).not.toBeInTheDocument()
    await user.click(await screen.findByRole('option', { name: /Synthetic Newcomer/ }))
    await user.click(screen.getByRole('button', { name: 'Add to Synthetic Nursing Science' }))
    await waitFor(() =>
      expect(server.calls('PATCH', '/admin/users/9')[0]?.body).toEqual({ programme_ids: [1, 2] }),
    )

    await user.click(
      within(people).getByRole('button', {
        name: 'Remove Synthetic Member from Synthetic Nursing Science',
      }),
    )
    await waitFor(() =>
      expect(server.calls('PATCH', '/admin/users/8')[0]?.body).toEqual({ programme_ids: [] }),
    )
  })

  it('adds a programme and opens its NUC core next', async () => {
    const created = programme({
      id: 3,
      name: 'Synthetic Civil Engineering',
      discipline_code: 'CVE',
    })
    let added = false
    const server = mockApi({
      'GET /auth/me': ok(adminUser),
      'GET /health': ok(healthyStatus),
      'GET /programmes': () => ok(added ? [programme(), created] : [programme()]),
      'GET /programmes/disciplines': ok({ general_skills: 26, disciplines: [] }),
      'POST /programmes': () => {
        added = true
        return ok(created, 201)
      },
      'GET /programmes/:id/benchmarks': ok({
        programme: created,
        active: null,
        latest: null,
        versions: [],
      }),
    })
    const { user } = renderApp('/admin/benchmarks')

    await user.click(await screen.findByRole('button', { name: 'Add programme' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add programme' })
    await user.type(within(dialog).getByLabelText('Programme name'), 'Synthetic Civil Engineering')
    await user.type(within(dialog).getByLabelText('Code'), 'CVE')
    await user.click(within(dialog).getByRole('button', { name: 'Add programme' }))

    await waitFor(() => expect(server.calls('POST', '/programmes')).toHaveLength(1))
    expect(server.calls('POST', '/programmes')[0].body).toMatchObject({
      name: 'Synthetic Civil Engineering',
      discipline_code: 'CVE',
      nuc_discipline: null,
    })
    expect(
      await screen.findByRole('heading', { name: 'Synthetic Civil Engineering' }),
    ).toBeVisible()
    expect(screen.getByRole('tab', { name: 'NUC core' })).toHaveAttribute('aria-selected', 'true')
  })
})
