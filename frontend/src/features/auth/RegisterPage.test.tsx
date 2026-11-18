import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, plannerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'

describe('RegisterPage', () => {
  it('is linked from sign-in and creates a planner for the chosen programme', async () => {
    let signedUp = false
    const server = mockApi({
      'GET /auth/me': () =>
        signedUp ? ok(plannerUser) : fail(401, 'UNAUTHORIZED', 'Please log in to continue.'),
      'GET /health': ok(healthyStatus),
      'GET /auth/register/programmes': ok([
        { id: 1, name: 'Synthetic Computer Science', discipline_code: 'CSC' },
        { id: 2, name: 'Synthetic Nursing Science', discipline_code: 'NS' },
      ]),
      'POST /auth/register': () => {
        signedUp = true
        return ok({ user: plannerUser, csrf_token: 'synthetic-token' }, 201)
      },
    })
    const { user, router } = renderApp('/login')

    await user.click(await screen.findByRole('link', { name: 'Create an account' }))
    expect(await screen.findByRole('heading', { name: 'Create your account' })).toBeVisible()

    await user.click(screen.getByRole('button', { name: /Create account/ }))
    expect(await screen.findByText('Enter your name.')).toBeInTheDocument()
    expect(screen.getByText('Choose your programme.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Full name'), 'Synthetic Planner')
    await user.type(screen.getByLabelText('Email'), 'synthetic.planner@example.com')
    await user.type(screen.getByLabelText('Username'), 'synthetic-planner')
    await user.selectOptions(screen.getByLabelText('Your programme'), 'Synthetic Nursing Science')
    await user.type(screen.getByLabelText('Password'), 'Synthetic-pass-2026')
    await user.type(screen.getByLabelText('Confirm password'), 'Synthetic-pass-2026')
    await user.click(screen.getByRole('button', { name: /Create account/ }))

    await waitFor(() => expect(server.calls('POST', '/auth/register')).toHaveLength(1))
    expect(server.calls('POST', '/auth/register')[0].body).toEqual({
      full_name: 'Synthetic Planner',
      email: 'synthetic.planner@example.com',
      username: 'synthetic-planner',
      password: 'Synthetic-pass-2026',
      programme_ids: [2],
    })
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })
})
