import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus } from '@/test/fixtures'
import { mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { HarvestRun, HarvestState, Programme } from '@/types/api'

const nursing: Programme = {
  id: 2,
  name: 'Synthetic Nursing Science',
  discipline_code: 'NSC',
  faculty: null,
  description: null,
  nuc_discipline: 'allied_health_sciences',
  country: 'Nigeria',
  is_active: true,
  created_at: '2026-11-01T09:00:00Z',
}

const run = (overrides: Partial<HarvestRun> = {}): HarvestRun => ({
  id: 7,
  programme_id: 2,
  status: 'completed',
  phase: 'ready',
  target_count: 10,
  pages_per_field: 2,
  examined_count: 40,
  found_count: 6,
  imported_count: 5,
  skipped_count: 35,
  documents_ready: 5,
  documents_processing: 0,
  documents_failed: 0,
  error_message: null,
  created_at: '2026-11-16T09:00:00Z',
  started_at: '2026-11-16T09:00:01Z',
  completed_at: '2026-11-16T09:02:00Z',
  ...overrides,
})

const state = (latest: HarvestRun | null): HarvestState => ({
  programme: { id: 2, name: nursing.name, discipline_code: 'NSC' },
  profile: { search_terms: ['nurse', 'nursing'], field_slugs: ['medical'] },
  latest_run: latest,
})

function setup(latest: HarvestRun | null) {
  mockApi({
    'GET /auth/me': ok(adminUser),
    'GET /health': ok(healthyStatus),
    'GET /programmes': ok([nursing]),
    'GET /harvest/programmes/:id': ok(state(latest)),
  })
  return renderApp('/admin/labour-market')
}

describe('LabourMarketPage', () => {
  it('says how many collected adverts are ready while the rest are prepared', async () => {
    setup(
      run({ phase: 'preparing', documents_ready: 2, documents_processing: 3, documents_failed: 0 }),
    )

    expect(await screen.findByText('Preparing adverts')).toBeInTheDocument()
    expect(screen.getByText('2 of 5')).toBeInTheDocument()
    expect(screen.getByText(/still being prepared and will appear in New analysis/)).toBeVisible()
    // Collecting has finished, so another collection may be started.
    expect(screen.getByRole('button', { name: /Collect jobs now/ })).toBeEnabled()
  })

  it('shows a finished collection as ready and reports adverts that failed', async () => {
    setup(run({ documents_ready: 4, documents_failed: 1 }))

    expect(await screen.findByText('Ready to analyse')).toBeInTheDocument()
    expect(screen.getByText('1 advert could not be processed and will not be used.')).toBeVisible()
  })

  it('blocks a second collection while one is collecting', async () => {
    setup(run({ status: 'running', phase: 'collecting', imported_count: 0, documents_ready: 0 }))

    expect(await screen.findByText('Collecting adverts')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Collecting/ })).toBeDisabled()
  })

  it('shows why a stopped collection failed', async () => {
    setup(
      run({
        status: 'failed',
        phase: 'failed',
        imported_count: 0,
        documents_ready: 0,
        error_message: 'The collection stopped unexpectedly before it finished. Start it again.',
      }),
    )

    expect(await screen.findByText('Failed')).toBeInTheDocument()
    expect(screen.getByText(/stopped unexpectedly/)).toBeVisible()
  })
})
