import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, plannerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'

const anonymous = {
  'GET /auth/me': fail(401, 'UNAUTHORIZED', 'Please log in to continue.'),
  'GET /health': ok(healthyStatus),
}

describe('LoginPage', () => {
  it('redirects anonymous visitors to the login page, remembering where they were going', async () => {
    mockApi(anonymous)
    const { router } = renderApp('/profile')

    expect(await screen.findByRole('heading', { name: 'Sign in to NLP-RS' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.search).toBe('?next=%2Fprofile')
  })

  it('validates the form before calling the API', async () => {
    const server = mockApi(anonymous)
    const { user } = renderApp('/login')

    await user.click(await screen.findByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Enter your username or email.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(server.calls('POST', '/auth/login')).toHaveLength(0)
  })

  it('signs in and continues to the requested page', async () => {
    const server = mockApi({
      ...anonymous,
      'POST /auth/login': ok({ user: plannerUser, csrf_token: 'after-login' }),
    })
    const { user, router } = renderApp('/login?next=%2Fprofile')

    await user.type(await screen.findByLabelText('Username or email'), 'test.planner')
    await user.type(screen.getByLabelText('Password'), 'Correct-pass-1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Profile' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/profile')
    expect(server.calls('POST', '/auth/login')[0].body).toEqual({
      identifier: 'test.planner',
      password: 'Correct-pass-1',
    })
  })

  it('shows the server message for wrong credentials', async () => {
    mockApi({
      ...anonymous,
      'POST /auth/login': fail(401, 'INVALID_CREDENTIALS', 'Invalid username/email or password.'),
    })
    const { user } = renderApp('/login')

    await user.type(await screen.findByLabelText('Username or email'), 'someone')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid username/email or password.',
    )
  })

  it('ignores off-site "next" targets after signing in', async () => {
    mockApi({
      ...anonymous,
      'POST /auth/login': ok({ user: plannerUser, csrf_token: 'after-login' }),
    })
    const { user, router } = renderApp('/login?next=%2F%2Fevil.example.com')

    await user.type(await screen.findByLabelText('Username or email'), 'test.planner')
    await user.type(screen.getByLabelText('Password'), 'Correct-pass-1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/')
  })

  it('sends signed-in users straight to the app', async () => {
    mockApi({ 'GET /auth/me': ok(plannerUser), 'GET /health': ok(healthyStatus) })
    const { router } = renderApp('/login')

    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/')
  })
})
