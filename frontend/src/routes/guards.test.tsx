import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, plannerUser, viewerUser } from '@/test/fixtures'
import { mockApi, networkDown, ok } from '@/test/server'
import { renderApp } from '@/test/utils'

import { safeNextPath } from './next-path'

describe('route guards', () => {
  it.each([plannerUser, viewerUser])('shows 403 when a $role opens an admin page', async (user) => {
    const server = mockApi({ 'GET /auth/me': ok(user), 'GET /health': ok(healthyStatus) })

    renderApp('/admin/users')

    expect(await screen.findByRole('heading', { name: 'Access denied' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(server.calls('GET', '/admin/users')).toHaveLength(0)
  })

  it('shows a retry message when the session check cannot reach the server', async () => {
    networkDown()

    renderApp('/')

    expect(await screen.findByText('Cannot reach NLP-RS')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('safeNextPath', () => {
  it.each([
    ['/profile', '/profile'],
    ['/admin/users?page=2', '/admin/users?page=2'],
    [null, '/'],
    ['', '/'],
    ['https://evil.example.com', '/'],
    ['//evil.example.com', '/'],
    ['/login', '/'],
  ])('%s → %s', (input, expected) => {
    expect(safeNextPath(input)).toBe(expected)
  })
})
