import { screen } from '@testing-library/react'
import { AxiosError, AxiosHeaders, type AxiosResponse } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/lib/api'
import { renderWithProviders } from '@/test/utils'

import { SystemStatusCard } from './SystemStatusCard'

function axiosFailure(status: number, data: unknown): AxiosError {
  const config = { headers: new AxiosHeaders() }
  const response = { status, data, statusText: '', headers: {}, config } as AxiosResponse
  return new AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, null, response)
}

describe('SystemStatusCard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows every service as available when the API is healthy', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({
      status: 200,
      data: {
        success: true,
        data: { status: 'ok', version: '0.1.0', checks: { database: 'ok', redis: 'ok' } },
      },
    })

    renderWithProviders(<SystemStatusCard />)

    expect(await screen.findByText('API version 0.1.0')).toBeInTheDocument()
    expect(screen.getAllByText('Available')).toHaveLength(2)
    expect(screen.queryByText('Some services are unavailable')).not.toBeInTheDocument()
  })

  it('explains a degraded API and marks the failing service', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(
      axiosFailure(503, {
        success: false,
        error: {
          code: 'SERVICE_UNAVAILABLE',
          message: 'One or more backend services are unavailable.',
          details: { version: '0.1.0', checks: { database: 'ok', redis: 'unavailable' } },
        },
      }),
    )

    renderWithProviders(<SystemStatusCard />)

    expect(await screen.findByText('Some services are unavailable')).toBeInTheDocument()
    expect(screen.getByText('Available')).toBeInTheDocument()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
  })

  it('shows an error when the API cannot be reached', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'))

    renderWithProviders(<SystemStatusCard />)

    expect(await screen.findByText('The API cannot be reached')).toBeInTheDocument()
    expect(screen.getByText(/Cannot reach the server/)).toBeInTheDocument()
  })

  it('shows a loading state while the first check is in flight', () => {
    vi.spyOn(api, 'get').mockReturnValue(new Promise(() => undefined))

    renderWithProviders(<SystemStatusCard />)

    expect(screen.getByLabelText('Loading system status')).toBeInTheDocument()
  })
})
