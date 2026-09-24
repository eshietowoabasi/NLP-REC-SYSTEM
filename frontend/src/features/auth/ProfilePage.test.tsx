import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, viewerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'

const signedIn = { 'GET /auth/me': ok(viewerUser), 'GET /health': ok(healthyStatus) }

async function fillPasswordForm(
  user: ReturnType<typeof renderApp>['user'],
  values: { current: string; next: string; confirm: string },
) {
  await user.type(await screen.findByLabelText('Current password'), values.current)
  await user.type(screen.getByLabelText('New password'), values.next)
  await user.type(screen.getByLabelText('Confirm new password'), values.confirm)
  await user.click(screen.getByRole('button', { name: 'Change password' }))
}

describe('ProfilePage', () => {
  it('shows the signed-in user details', async () => {
    mockApi(signedIn)
    renderApp('/profile')

    expect(await screen.findByText('test.viewer@example.com')).toBeInTheDocument()
    expect(screen.getAllByText('Viewer').length).toBeGreaterThan(0)
    expect(screen.getByText(/Read-only access/)).toBeInTheDocument()
  })

  it('checks the new password locally before calling the API', async () => {
    const server = mockApi(signedIn)
    const { user } = renderApp('/profile')

    await fillPasswordForm(user, { current: 'Old-pass-123', next: 'short', confirm: 'other' })

    expect(await screen.findByText('Password must be at least 8 characters.')).toBeInTheDocument()
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument()
    expect(server.calls('POST', '/auth/change-password')).toHaveLength(0)
  })

  it('attaches a wrong current password error to its field', async () => {
    mockApi({
      ...signedIn,
      'POST /auth/change-password': fail(422, 'VALIDATION_ERROR', 'Some fields are invalid.', {
        fields: { current_password: ['Current password is incorrect.'] },
      }),
    })
    const { user } = renderApp('/profile')

    await fillPasswordForm(user, {
      current: 'Wrong-pass-1',
      next: 'Brand-new-pass-1',
      confirm: 'Brand-new-pass-1',
    })

    const field = await screen.findByText('Current password is incorrect.')
    expect(field).toBeInTheDocument()
    expect(screen.getByLabelText('Current password')).toHaveAttribute('aria-invalid', 'true')
  })

  it('changes the password and clears the form', async () => {
    const server = mockApi({
      ...signedIn,
      'POST /auth/change-password': ok({ message: 'Password changed.' }),
    })
    const { user } = renderApp('/profile')

    await fillPasswordForm(user, {
      current: 'Old-pass-123',
      next: 'Brand-new-pass-1',
      confirm: 'Brand-new-pass-1',
    })

    expect(await screen.findByText(/Password changed/)).toBeInTheDocument()
    expect(server.calls('POST', '/auth/change-password')[0].body).toEqual({
      current_password: 'Old-pass-123',
      new_password: 'Brand-new-pass-1',
    })
    expect(screen.getByLabelText('Current password')).toHaveValue('')
  })
})
