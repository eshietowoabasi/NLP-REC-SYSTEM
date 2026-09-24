import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus } from '@/test/fixtures'
import { fail, mockApi, networkDown, ok, pending } from '@/test/server'
import { renderWithProviders } from '@/test/utils'

import { SystemStatusCard } from './SystemStatusCard'

describe('SystemStatusCard', () => {
  it('shows every service as available when the API is healthy', async () => {
    mockApi({ 'GET /health': ok(healthyStatus) })

    renderWithProviders(<SystemStatusCard />)

    expect(await screen.findByText('API version 0.1.0')).toBeInTheDocument()
    expect(screen.getAllByText('Available')).toHaveLength(2)
    expect(screen.queryByText('Some services are unavailable')).not.toBeInTheDocument()
  })

  it('explains a degraded API and marks the failing service', async () => {
    mockApi({
      'GET /health': fail(503, 'SERVICE_UNAVAILABLE', 'One or more services are unavailable.', {
        version: '0.1.0',
        checks: { database: 'ok', redis: 'unavailable' },
      }),
    })

    renderWithProviders(<SystemStatusCard />)

    expect(await screen.findByText('Some services are unavailable')).toBeInTheDocument()
    expect(screen.getByText('Available')).toBeInTheDocument()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
  })

  it('shows an error when the API cannot be reached', async () => {
    networkDown()

    renderWithProviders(<SystemStatusCard />)

    expect(await screen.findByText('The API cannot be reached')).toBeInTheDocument()
    expect(screen.getByText(/Cannot reach the server/)).toBeInTheDocument()
  })

  it('shows a loading state while the first check is in flight', () => {
    mockApi({ 'GET /health': pending })

    renderWithProviders(<SystemStatusCard />)

    expect(screen.getByLabelText('Loading system status')).toBeInTheDocument()
  })
})
