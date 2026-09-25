import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, plannerUser } from '@/test/fixtures'
import { mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { User } from '@/types/api'

function signedInAs(user: User) {
  return mockApi({
    'GET /auth/me': ok(user),
    'GET /health': ok(healthyStatus),
    'POST /auth/logout': ok({ csrf_token: 'fresh-anonymous-token' }),
  })
}

describe('AppShell', () => {
  it('renders the navigation, page title, user and API status on the dashboard', async () => {
    signedInAs(adminUser)
    renderApp('/')

    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('data-active', 'true')
    expect(await screen.findByText('API connected')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Account menu' })).toHaveTextContent('Test Admin')
    await waitFor(() => expect(document.title).toBe('Dashboard · NLP-RS'))
  })

  it('shows the Administration section to admins only', async () => {
    signedInAs(adminUser)
    const { unmount } = renderApp('/')
    expect(await screen.findByText('Administration')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Users' })).toHaveAttribute('href', '/admin/users')
    unmount()

    signedInAs(plannerUser)
    renderApp('/')
    expect(await screen.findByText('Workspace')).toBeInTheDocument()
    expect(screen.queryByText('Administration')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Users' })).not.toBeInTheDocument()
  })

  it('shows screens that are not built yet as disabled, not as links', async () => {
    signedInAs(plannerUser)
    renderApp('/')

    expect(await screen.findByRole('button', { name: 'Reports' })).toBeDisabled()
    expect(screen.queryByRole('link', { name: 'Reports' })).not.toBeInTheDocument()
  })

  it('logs out from the account menu and returns to the login page', async () => {
    const server = signedInAs(plannerUser)
    const { user } = renderApp('/')

    await user.click(await screen.findByRole('button', { name: 'Account menu' }))
    const menu = await screen.findByRole('menu')
    expect(within(menu).getByText('test.planner@example.com')).toBeInTheDocument()
    await user.click(within(menu).getByRole('menuitem', { name: 'Log out' }))

    expect(await screen.findByRole('heading', { name: 'Sign in to NLP-RS' })).toBeInTheDocument()
    expect(server.calls('POST', '/auth/logout')).toHaveLength(1)
  })

  it('renders the 404 page for unknown paths', async () => {
    signedInAs(plannerUser)
    renderApp('/no-such-page')

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/')
  })
})
