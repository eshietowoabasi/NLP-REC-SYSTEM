import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, makeUser, page, plannerUser, viewerUser } from '@/test/fixtures'
import { fail, mockApi, ok, type MockRequest } from '@/test/server'
import { renderApp } from '@/test/utils'

const allUsers = [adminUser, plannerUser, viewerUser]

function usersApi(extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    'GET /auth/me': ok(adminUser),
    'GET /health': ok(healthyStatus),
    'GET /admin/users': (request: MockRequest) => {
      const role = request.params.role as string | undefined
      return ok(page(role ? allUsers.filter((u) => u.role === role) : allUsers))
    },
    ...extra,
  })
}

describe('UsersPage', () => {
  it('lists users with their role and status', async () => {
    usersApi()
    renderApp('/admin/users')

    const table = await screen.findByRole('table')
    expect(await within(table).findByText('Test Planner')).toBeInTheDocument()
    expect(within(table).getByText('test.viewer@example.com')).toBeInTheDocument()
    expect(within(table).getByText('(you)')).toBeInTheDocument()
  })

  it('filters by role', async () => {
    const server = usersApi()
    const { user } = renderApp('/admin/users')
    await screen.findByText('Test Planner')

    await user.click(screen.getByLabelText('Role'))
    await user.click(await screen.findByRole('option', { name: 'Viewer' }))

    await waitFor(() => expect(screen.queryByText('Test Planner')).not.toBeInTheDocument())
    expect(screen.getByText('Test Viewer')).toBeInTheDocument()
    const last = server.calls('GET', '/admin/users').at(-1)
    expect(last?.params).toMatchObject({ role: 'viewer', page: 1 })
  })

  it('shows an empty state when no users match', async () => {
    usersApi({ 'GET /admin/users': ok(page([])) })
    const { user } = renderApp('/admin/users')

    await user.type(await screen.findByLabelText('Search'), 'nobody')

    expect(await screen.findByText('No users match these filters.')).toBeInTheDocument()
  })

  it('shows an error with a retry button when the list fails to load', async () => {
    usersApi({ 'GET /admin/users': fail(500, 'INTERNAL_ERROR', 'An unexpected error occurred.') })
    renderApp('/admin/users')

    expect(await screen.findByText('Could not load users')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('creates a user', async () => {
    const created = makeUser({ id: 9, username: 'new.planner', role: 'planner' })
    const server = usersApi({ 'POST /admin/users': ok(created, 201) })
    const { user } = renderApp('/admin/users')

    await user.click(await screen.findByRole('button', { name: 'Add user' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Full name'), 'New Planner')
    await user.type(within(dialog).getByLabelText('Username'), 'new.planner')
    await user.type(within(dialog).getByLabelText('Email'), 'new.planner@example.com')
    await user.type(within(dialog).getByLabelText('Initial password'), 'Initial-pass-1')
    await user.click(within(dialog).getByRole('button', { name: 'Create user' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(server.calls('POST', '/admin/users')[0].body).toEqual({
      full_name: 'New Planner',
      username: 'new.planner',
      email: 'new.planner@example.com',
      role: 'planner',
      password: 'Initial-pass-1',
    })
    expect(await screen.findByText('User new.planner created.')).toBeInTheDocument()
  })

  it('shows server conflicts on the matching field', async () => {
    usersApi({
      'POST /admin/users': fail(409, 'CONFLICT', 'A user with these details already exists.', {
        fields: { username: ['This username is already in use.'] },
      }),
    })
    const { user } = renderApp('/admin/users')

    await user.click(await screen.findByRole('button', { name: 'Add user' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Full name'), 'Dup')
    await user.type(within(dialog).getByLabelText('Username'), 'test.planner')
    await user.type(within(dialog).getByLabelText('Email'), 'dup@example.com')
    await user.type(within(dialog).getByLabelText('Initial password'), 'Initial-pass-1')
    await user.click(within(dialog).getByRole('button', { name: 'Create user' }))

    expect(await within(dialog).findByText('This username is already in use.')).toBeInTheDocument()
  })

  it('sends only the changed fields when editing', async () => {
    const server = usersApi({
      'PATCH /admin/users/:id': (_request, params) =>
        ok({ ...viewerUser, id: Number(params.id), role: 'planner' }),
    })
    const { user } = renderApp('/admin/users')

    await user.click(await screen.findByRole('button', { name: 'Actions for test.viewer' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Edit details' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByLabelText('Role'))
    await user.click(await screen.findByRole('option', { name: 'Curriculum Planner' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(server.calls('PATCH', '/admin/users/3')).toHaveLength(1))
    expect(server.calls('PATCH', '/admin/users/3')[0].body).toEqual({ role: 'planner' })
  })

  it('confirms before deactivating a user', async () => {
    const server = usersApi({
      'PATCH /admin/users/:id': ok({ ...plannerUser, is_active: false }),
    })
    const { user } = renderApp('/admin/users')

    await user.click(await screen.findByRole('button', { name: 'Actions for test.planner' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Deactivate' }))
    const confirm = await screen.findByRole('alertdialog')
    expect(within(confirm).getByText(/signed out immediately/)).toBeInTheDocument()
    await user.click(within(confirm).getByRole('button', { name: 'Deactivate' }))

    await waitFor(() => expect(server.calls('PATCH', '/admin/users/2')).toHaveLength(1))
    expect(server.calls('PATCH', '/admin/users/2')[0].body).toEqual({ is_active: false })
  })

  it('does not offer to deactivate your own account', async () => {
    usersApi()
    const { user } = renderApp('/admin/users')

    await user.click(await screen.findByRole('button', { name: 'Actions for test.admin' }))

    expect(await screen.findByRole('menuitem', { name: 'Deactivate' })).toHaveAttribute(
      'aria-disabled',
      'true',
    )
  })
})
