import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, makeDocument, page, plannerUser, viewerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { SessionDefaults, SessionDetail, SessionSummary, User } from '@/types/api'

/* Synthetic fixtures. */
const defaults: SessionDefaults = {
  parameters: {
    weights: { ner: 0.4, topic: 0.35, novelty: 0.25 },
    similarity_threshold: 0.8,
    max_recommendations: 20,
    min_topic_size: 5,
    evidence_per_recommendation: 8,
    sbert_model: 'all-MiniLM-L6-v2',
    spacy_model: 'en_core_web_sm',
  },
  max_documents: 50,
  nuc_core_version: { id: 1, version_label: 'Synthetic core v1' },
}

const summary = (overrides: Partial<SessionSummary> = {}): SessionSummary => ({
  id: 5,
  session_name: 'Synthetic 2026 review',
  status: 'completed',
  current_stage: 'completed',
  progress_percent: 100,
  created_by: { id: 2, full_name: 'Test Planner' },
  document_count: 9,
  recommendation_count: 7,
  created_at: '2026-09-24T10:00:00Z',
  started_at: '2026-09-24T10:00:01Z',
  completed_at: '2026-09-24T10:00:40Z',
  ...overrides,
})

const detail = (overrides: Partial<SessionDetail> = {}): SessionDetail => ({
  ...summary(),
  parameter_config: defaults.parameters,
  stage_timings: { validating: 0.1, themes: 3.2 },
  error_message: null,
  nuc_core_version: { id: 1, version_label: 'Synthetic core v1' },
  documents: [
    {
      id: 11,
      title: 'Synthetic advert',
      source_category: 'job_market',
      processing_status: 'ready',
    },
  ],
  topic_count: 7,
  ...overrides,
})

const readyDocuments = [
  makeDocument({ id: 11, title: 'Synthetic cloud advert' }),
  makeDocument({ id: 12, title: 'Synthetic security advert' }),
  makeDocument({ id: 13, title: 'Synthetic ICT policy', source_category: 'policy' }),
]

function sessionsApi(user: User, extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    'GET /auth/me': ok(user),
    'GET /health': ok(healthyStatus),
    'GET /sessions': ok(
      page([
        summary(),
        summary({
          id: 6,
          session_name: 'Running one',
          status: 'processing',
          current_stage: 'themes',
          progress_percent: 55,
        }),
      ]),
    ),
    'GET /sessions/defaults': ok(defaults),
    'GET /documents': ok({
      ...page(readyDocuments),
      category_counts: { job_market: 2, institutional: 0, policy: 1, academic: 0 },
    }),
    ...extra,
  })
}

describe('SessionsPage', () => {
  it('lists sessions with status and the running stage', async () => {
    sessionsApi(plannerUser)
    renderApp('/sessions')

    expect(await screen.findByRole('link', { name: 'Synthetic 2026 review' })).toHaveAttribute(
      'href',
      '/sessions/5',
    )
    const row = screen.getByRole('link', { name: 'Synthetic 2026 review' }).closest('tr')!
    expect(within(row).getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('· Themes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete Running one' })).toBeDisabled()
    expect(screen.getByRole('link', { name: /New session/ })).toBeInTheDocument()
  })

  it('hides create and delete from viewers', async () => {
    sessionsApi(viewerUser)
    renderApp('/sessions')

    await screen.findByRole('link', { name: 'Synthetic 2026 review' })
    expect(screen.queryByRole('link', { name: /New session/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Delete/ })).not.toBeInTheDocument()
  })
})

describe('NewSessionPage', () => {
  async function toStep3(user: ReturnType<typeof renderApp>['user']) {
    await user.type(await screen.findByLabelText('Session name'), 'Synthetic review')
    await user.click(screen.getByRole('button', { name: /Next/ }))
    await user.click(await screen.findByLabelText(/Synthetic cloud advert/))
    await user.click(screen.getByLabelText(/Synthetic ICT policy/))
    expect(screen.getByText('2 of 50 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Next/ }))
  }

  it('requires a name and at least one document before moving on', async () => {
    sessionsApi(plannerUser)
    const { user } = renderApp('/sessions/new')

    await user.click(await screen.findByRole('button', { name: /Next/ }))
    expect(await screen.findByText('Enter a session name.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Session name'), 'Synthetic review')
    await user.click(screen.getByRole('button', { name: /Next/ }))
    await screen.findByRole('list', { name: 'Ready documents' })
    await user.click(screen.getByRole('button', { name: /Next/ }))
    expect(await screen.findByText('Select at least one document.')).toBeInTheDocument()
  })

  it('checks that the weights add up to 1 before creating', async () => {
    const server = sessionsApi(plannerUser)
    const { user } = renderApp('/sessions/new')
    await toStep3(user)

    const ner = screen.getByLabelText('Skill demand (NER)')
    expect(ner).toHaveValue(0.4)
    expect(screen.getByText(/Sum: 1.00 ✓/)).toBeInTheDocument()
    await user.clear(ner)
    await user.type(ner, '0.6')

    expect(screen.getByText(/Sum: 1.20 — the weights must add up to 1.00/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Create' }))
    expect(await screen.findByText('The three weights must add up to 1.00.')).toBeInTheDocument()
    expect(server.calls('POST', '/sessions')).toHaveLength(0)
  })

  it('creates and runs the session with the chosen documents and settings', async () => {
    const server = sessionsApi(plannerUser, {
      'POST /sessions': ok(detail({ id: 9, status: 'processing', current_stage: 'queued' }), 201),
      'GET /sessions/:id': ok(
        detail({ id: 9, status: 'processing', current_stage: 'queued', progress_percent: 0 }),
      ),
    })
    const { user, router } = renderApp('/sessions/new')
    await toStep3(user)

    const max = screen.getByLabelText('Maximum recommendations')
    await user.clear(max)
    await user.type(max, '10')
    await user.click(screen.getByRole('button', { name: /Create & run/ }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/sessions/9'))
    expect(server.calls('POST', '/sessions')[0].body).toEqual({
      session_name: 'Synthetic review',
      document_ids: [11, 13],
      parameters: {
        weights: { ner: 0.4, topic: 0.35, novelty: 0.25 },
        similarity_threshold: 0.8,
        max_recommendations: 10,
      },
      run: true,
    })
  })

  it('warns when there is no active NUC core and only allows Create', async () => {
    sessionsApi(plannerUser, {
      'GET /sessions/defaults': ok({ ...defaults, nuc_core_version: null }),
    })
    const { user } = renderApp('/sessions/new')

    expect(await screen.findByText('No active NUC core reference')).toBeInTheDocument()
    await toStep3(user)
    expect(screen.getByRole('button', { name: /Create & run/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Create' })).toBeEnabled()
  })
})

describe('SessionDetailPage', () => {
  it('shows the stage tracker while running', async () => {
    sessionsApi(plannerUser, {
      'GET /sessions/:id': ok(
        detail({
          status: 'processing',
          current_stage: 'themes',
          progress_percent: 55,
          topic_count: null,
        }),
      ),
    })
    renderApp('/sessions/5')

    const stages = await screen.findByRole('list', { name: 'Analysis stages' })
    expect(within(stages).getByText('Keywords').parentElement).toHaveTextContent('done')
    expect(within(stages).getByText('Themes').closest('li')).toHaveAttribute('aria-current', 'step')
    expect(within(stages).getByText('Scoring').parentElement).toHaveTextContent('not started')
    expect(screen.getByText('55%')).toBeInTheDocument()
  })

  it('explains a failure and retries', async () => {
    const server = sessionsApi(plannerUser, {
      'GET /sessions/:id': ok(
        detail({
          status: 'failed',
          current_stage: 'themes',
          error_message: 'Too little text to discover themes: 4 passages were found.',
          recommendation_count: 0,
        }),
      ),
      'POST /sessions/:id/retry': ok(
        detail({ status: 'processing', current_stage: 'queued' }),
        202,
      ),
    })
    const { user } = renderApp('/sessions/5')

    expect(await screen.findByText('The analysis failed at the Themes stage')).toBeInTheDocument()
    expect(screen.getByText(/Too little text/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Retry/ }))

    await waitFor(() => expect(server.calls('POST', '/sessions/5/retry')).toHaveLength(1))
  })

  it('summarises a completed session', async () => {
    sessionsApi(plannerUser, { 'GET /sessions/:id': ok(detail()) })
    renderApp('/sessions/5')

    expect(await screen.findByText('Analysis complete')).toBeInTheDocument()
    expect(
      screen.getByText(/7 recommendations from 7 themes found in 9 documents/),
    ).toBeInTheDocument()
    expect(screen.getByText('Synthetic core v1')).toBeInTheDocument()
  })

  it('shows 404 for an unknown session', async () => {
    sessionsApi(plannerUser, {
      'GET /sessions/:id': fail(404, 'NOT_FOUND', 'Analysis session not found.'),
    })
    renderApp('/sessions/999')

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
