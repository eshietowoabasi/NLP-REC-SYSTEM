import { screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/lib/api'
import { routes } from '@/routes/router'
import { renderRoutes } from '@/test/utils'

describe('AppShell', () => {
  beforeEach(() => {
    vi.spyOn(api, 'get').mockResolvedValue({
      status: 200,
      data: {
        success: true,
        data: { status: 'ok', version: '0.1.0', checks: { database: 'ok', redis: 'ok' } },
      },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the navigation, page title and API status on the dashboard', async () => {
    renderRoutes(routes, '/')

    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('data-active', 'true')
    expect(screen.getByText('Administration')).toBeInTheDocument()
    expect(await screen.findByText('API connected')).toBeInTheDocument()
    await waitFor(() => expect(document.title).toBe('Dashboard · NLP-RS'))
  })

  it('shows screens that are not built yet as disabled, not as links', () => {
    renderRoutes(routes, '/')

    expect(screen.queryByRole('link', { name: 'Documents' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Documents' })).toBeDisabled()
  })

  it('renders the 404 page for unknown paths', () => {
    renderRoutes(routes, '/no-such-page')

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/')
  })
})
