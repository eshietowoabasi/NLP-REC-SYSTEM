import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, plannerUser, viewerUser } from '@/test/fixtures'
import { fail, mockApi, ok, type MockRequest } from '@/test/server'
import { renderApp } from '@/test/utils'
import type {
  CourseMapping,
  CurriculumCourse,
  KeywordResults,
  ProposedCurriculum,
  Recommendation,
  RecommendationDetail,
  RecommendationList,
  SessionDetail,
  SimilarityResults,
  User,
} from '@/types/api'

/* Synthetic fixtures. */
const session: SessionDetail = {
  id: 5,
  session_name: 'Synthetic 2026 review',
  status: 'completed',
  current_stage: 'completed',
  progress_percent: 100,
  created_by: { id: 2, full_name: 'Test Planner' },
  document_count: 3,
  recommendation_count: 3,
  created_at: '2026-09-24T10:00:00Z',
  started_at: '2026-09-24T10:00:01Z',
  completed_at: '2026-09-24T10:00:40Z',
  parameter_config: {
    weights: { ner: 0.4, topic: 0.35, novelty: 0.25 },
    similarity_threshold: 0.8,
    max_recommendations: 20,
    min_topic_size: 5,
    evidence_per_recommendation: 8,
    sbert_model: 'all-MiniLM-L6-v2',
    spacy_model: 'en_core_web_sm',
  },
  stage_timings: {},
  error_message: null,
  nuc_core_version: { id: 1, version_label: 'Synthetic core v1' },
  documents: [],
  topic_count: 3,
}

const rec = (overrides: Partial<Recommendation> = {}): Recommendation => ({
  id: 31,
  session_id: 5,
  rank: 1,
  topic_id: 0,
  auto_title: 'Cloud Security and Kubernetes',
  topic_title: 'Cloud Security and Kubernetes',
  topic_description: 'Synthetic description of securing cloud workloads.',
  keywords: [{ term: 'cloud', weight: 0.2 }],
  skills: [{ name: 'Kubernetes', label: 'TOOL', mentions: 4, document_frequency: 2 }],
  ner_score: 0.9,
  topic_score: 0.5,
  novelty_score: 0.3,
  composite_score: 0.6,
  max_similarity: 0.7,
  overlap_status: 'No Significant Overlap',
  planner_decision: null,
  planner_notes: null,
  decided_at: null,
  decided_by: null,
  has_mapping: false,
  ...overrides,
})

const list: RecommendationList = {
  items: [
    rec({ planner_decision: 'accepted' }),
    rec({
      id: 32,
      rank: 2,
      topic_title: 'Operating Systems Internals',
      overlap_status: 'Potential Duplicate',
      max_similarity: 0.86,
    }),
    rec({ id: 33, rank: 3, topic_title: 'Payment Integration', planner_decision: 'flagged' }),
  ],
  counts: {
    total: 3,
    reviewed: 2,
    undecided: 1,
    accepted: 1,
    rejected: 0,
    flagged: 1,
    potential_duplicates: 1,
  },
}

const detail = (overrides: Partial<RecommendationDetail> = {}): RecommendationDetail => ({
  ...rec(),
  evidence: [
    {
      passage_id: 101,
      relevance_score: 0.93,
      text: 'Synthetic advert passage about Kubernetes clusters.',
      page_number: 1,
      position: 0,
      document: { id: 11, title: 'Synthetic cloud advert', source_category: 'job_market' },
    },
    {
      passage_id: 102,
      relevance_score: 0.88,
      text: 'Synthetic policy passage on cloud adoption.',
      page_number: null,
      position: 4,
      document: { id: 12, title: 'Synthetic ICT policy', source_category: 'policy' },
    },
    {
      passage_id: 103,
      relevance_score: 0.8,
      text: 'Second synthetic advert passage on container security.',
      page_number: 2,
      position: 1,
      document: { id: 11, title: 'Synthetic cloud advert', source_category: 'job_market' },
    },
  ],
  closest_nuc_passage: {
    id: 900,
    text: 'Synthetic core passage on computer networks.',
    page_number: 14,
    document_title: 'Synthetic NUC core',
    version_label: 'Synthetic core v1',
  },
  session: {
    id: 5,
    session_name: 'Synthetic 2026 review',
    weights: { ner: 0.4, topic: 0.35, novelty: 0.25 },
    similarity_threshold: 0.8,
  },
  mapping: null,
  ...overrides,
})

const mapping: CourseMapping = {
  id: 7,
  recommendation_id: 31,
  course_code: 'CSC 419',
  course_title: 'Cloud Security Engineering',
  credit_units: 3,
  prerequisites: ['CSC 301'],
  learning_outcomes: ['Secure cloud workloads'],
  created_by: { id: 2, full_name: 'Test Planner' },
  created_at: '2026-09-25T09:00:00Z',
  updated_at: '2026-09-25T09:00:00Z',
}

function reviewApi(user: User, extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    'GET /auth/me': ok(user),
    'GET /health': ok(healthyStatus),
    'GET /sessions/:id': ok(session),
    'GET /sessions/:id/recommendations': ok(list),
    'GET /recommendations/:id': ok(detail()),
    ...extra,
  })
}

const decisionBody = (request: MockRequest) => request.body as { decision: string | null }

describe('RecommendationsPage', () => {
  it('lists ranked recommendations with badges, scores and review progress', async () => {
    reviewApi(plannerUser)
    renderApp('/sessions/5/recommendations')

    const items = within(
      await screen.findByRole('list', { name: 'Ranked recommendations' }),
    ).getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(
      within(items[0]).getByRole('link', { name: 'Cloud Security and Kubernetes' }),
    ).toHaveAttribute('href', '/recommendations/31')
    expect(within(items[0]).getByText('New')).toBeInTheDocument()
    expect(within(items[0]).getByText('Accepted')).toBeInTheDocument()
    expect(within(items[1]).getByText('Potential Duplicate')).toBeInTheDocument()
    expect(within(items[1]).getByText('Undecided')).toBeInTheDocument()
    expect(within(items[0]).getByRole('meter', { name: 'Composite' })).toHaveAttribute(
      'aria-valuenow',
      '0.6',
    )
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
    expect(screen.getByText(/1 potential duplicate of NUC core content/)).toBeInTheDocument()
  })

  it('filters by decision and hides duplicates through the API', async () => {
    const server = reviewApi(plannerUser)
    const { user } = renderApp('/sessions/5/recommendations')

    await user.click(await screen.findByRole('radio', { name: /Undecided/ }))
    await waitFor(() =>
      expect(server.calls('GET', '/sessions/5/recommendations').at(-1)?.params).toEqual({
        decision: 'undecided',
      }),
    )
    await user.click(screen.getByLabelText('Hide potential duplicates'))
    await waitFor(() =>
      expect(server.calls('GET', '/sessions/5/recommendations').at(-1)?.params).toEqual({
        decision: 'undecided',
        hide_duplicates: 'true',
      }),
    )
  })

  it('accepts in one click, and clicking the current decision clears it', async () => {
    const server = reviewApi(plannerUser, {
      'PATCH /recommendations/:id/decision': (request, params) =>
        ok(
          rec({ id: Number(params.id), planner_decision: decisionBody(request).decision as never }),
        ),
    })
    const { user } = renderApp('/sessions/5/recommendations')

    const second = await screen.findByRole('group', {
      name: 'Decision for Operating Systems Internals',
    })
    await user.click(within(second).getByRole('button', { name: 'Accept' }))
    const first = screen.getByRole('group', { name: 'Decision for Cloud Security and Kubernetes' })
    expect(within(first).getByRole('button', { name: 'Accept' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await user.click(within(first).getByRole('button', { name: 'Accept' }))

    await waitFor(() =>
      expect(server.calls('PATCH', '/recommendations/31/decision')).toHaveLength(1),
    )
    expect(server.calls('PATCH', '/recommendations/32/decision')[0].body).toEqual({
      decision: 'accepted',
      notes: null,
    })
    expect(
      decisionBody(server.calls('PATCH', '/recommendations/31/decision')[0]).decision,
    ).toBeNull()
  })

  it('does not let viewers decide', async () => {
    reviewApi(viewerUser)
    renderApp('/sessions/5/recommendations')

    await screen.findByRole('list', { name: 'Ranked recommendations' })
    expect(screen.queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument()
  })

  it('explains that results are not ready while the session runs', async () => {
    reviewApi(plannerUser, {
      'GET /sessions/:id': ok({ ...session, status: 'processing', current_stage: 'themes' }),
    })
    renderApp('/sessions/5/recommendations')

    expect(await screen.findByText('Results are not ready')).toBeInTheDocument()
  })
})

describe('RecommendationDetailPage', () => {
  it('shows the score formula with the real numbers, overlap and grouped evidence', async () => {
    reviewApi(plannerUser)
    renderApp('/recommendations/31')

    const formula = await screen.findByLabelText('Composite score formula')
    expect(formula).toHaveTextContent(
      '0.40 × 0.90 (skill demand) + 0.35 × 0.50 (theme strength) + 0.25 × 0.30 (novelty) = 0.60',
    )
    expect(screen.getByText('Synthetic core passage on computer networks.')).toBeInTheDocument()
    expect(screen.getByText('Synthetic core v1 · p. 14')).toBeInTheDocument()
    expect(
      screen.getByText(/Highest similarity 0.70 against a threshold of 0.80/),
    ).toBeInTheDocument()

    const advert = screen.getByRole('region', { name: 'Synthetic cloud advert' })
    expect(within(advert).getAllByRole('listitem')).toHaveLength(2)
    expect(within(advert).getByText(/Page 2 · relevance 0.80/)).toBeInTheDocument()
    const policy = screen.getByRole('region', { name: 'Synthetic ICT policy' })
    expect(within(policy).getByText(/Passage 5 · relevance 0.88/)).toBeInTheDocument()
  })

  it('edits the title and keeps the generated one for reference', async () => {
    const server = reviewApi(plannerUser, {
      'PATCH /recommendations/:id': ok(rec({ topic_title: 'Cloud Security Engineering' })),
    })
    const { user } = renderApp('/recommendations/31')

    await user.click(await screen.findByRole('button', { name: /Edit title and description/ }))
    const title = screen.getByLabelText('Title')
    await user.clear(title)
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Enter a title.')).toBeInTheDocument()

    await user.type(title, 'Cloud Security Engineering')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(
      await screen.findByRole('heading', { name: 'Cloud Security Engineering' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Generated title: Cloud Security and Kubernetes')).toBeInTheDocument()
    expect(server.calls('PATCH', '/recommendations/31')[0].body).toEqual({
      topic_title: 'Cloud Security Engineering',
      topic_description: 'Synthetic description of securing cloud workloads.',
    })
  })

  it('saves a decision with notes, then offers mapping to a course', async () => {
    const server = reviewApi(plannerUser, {
      'PATCH /recommendations/:id/decision': ok(
        rec({ planner_decision: 'accepted', planner_notes: 'Strong demand.' }),
      ),
    })
    const { user } = renderApp('/recommendations/31')

    expect(
      await screen.findByText('Accept the recommendation to map it to a proposed course.'),
    ).toBeInTheDocument()
    const save = screen.getByRole('button', { name: 'Save decision' })
    expect(save).toBeDisabled()
    await user.click(screen.getByRole('radio', { name: 'Accept' }))
    await user.type(screen.getByLabelText('Notes'), 'Strong demand.')
    await user.click(save)

    expect(await screen.findByRole('link', { name: /Map to course/ })).toHaveAttribute(
      'href',
      '/recommendations/31/mapping',
    )
    expect(server.calls('PATCH', '/recommendations/31/decision')[0].body).toEqual({
      decision: 'accepted',
      notes: 'Strong demand.',
    })
  })

  it('locks the decision while the recommendation is mapped', async () => {
    reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(
        detail({ planner_decision: 'accepted', has_mapping: true, mapping }),
      ),
    })
    renderApp('/recommendations/31')

    expect(await screen.findByText(/CSC 419/)).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Reject' })).toBeDisabled()
    expect(screen.getByRole('link', { name: 'Edit course mapping' })).toBeInTheDocument()
  })

  it('shows 404 for an unknown recommendation', async () => {
    reviewApi(plannerUser, {
      'GET /recommendations/:id': fail(404, 'NOT_FOUND', 'Recommendation not found.'),
    })
    renderApp('/recommendations/999')

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})

describe('MappingPage', () => {
  const accepted = detail({ planner_decision: 'accepted' })

  it('validates, normalises the course code and creates the mapping', async () => {
    const server = reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(accepted),
      'POST /recommendations/:id/mapping': ok(mapping, 201),
    })
    const { user, router } = renderApp('/recommendations/31/mapping')

    expect(await screen.findByLabelText('Course title')).toHaveValue(
      'Cloud Security and Kubernetes',
    )
    expect(screen.getByRole('radio', { name: '3 credit units' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
    await user.type(screen.getByLabelText('Course code'), 'Cloud1')
    await user.click(screen.getByRole('button', { name: 'Add to curriculum' }))
    expect(await screen.findByText(/Use a course code like/)).toBeInTheDocument()
    expect(screen.getByText('Add at least one learning outcome.')).toBeInTheDocument()

    await user.clear(screen.getByLabelText('Course code'))
    await user.type(screen.getByLabelText('Course code'), 'csc419')
    await user.click(screen.getByRole('radio', { name: '2 credit units' }))
    await user.type(screen.getByLabelText('Prerequisites'), 'CSC 301{Enter}csc 301{Enter}')
    expect(screen.getByText('csc 301 is already listed.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Learning outcome 1'), 'Secure cloud workloads')
    await user.click(screen.getByRole('button', { name: /Add outcome/ }))
    await user.type(screen.getByLabelText('Learning outcome 2'), 'Operate clusters')
    await user.click(screen.getByRole('button', { name: 'Add to curriculum' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/recommendations/31'))
    expect(server.calls('POST', '/recommendations/31/mapping')[0].body).toEqual({
      course_code: 'CSC 419',
      course_title: 'Cloud Security and Kubernetes',
      credit_units: 2,
      prerequisites: ['CSC 301'],
      learning_outcomes: ['Secure cloud workloads', 'Operate clusters'],
    })
  })

  it('shows a duplicate course code from the server on the field', async () => {
    reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(accepted),
      'POST /recommendations/:id/mapping': fail(409, 'CONFLICT', 'CSC 419 is already used.', {
        fields: { course_code: ['CSC 419 is already used in this session.'] },
      }),
    })
    const { user } = renderApp('/recommendations/31/mapping')

    await user.type(await screen.findByLabelText('Course code'), 'CSC 419')
    await user.type(screen.getByLabelText('Learning outcome 1'), 'Secure cloud workloads')
    await user.click(screen.getByRole('button', { name: 'Add to curriculum' }))

    expect(await screen.findByText('CSC 419 is already used in this session.')).toBeInTheDocument()
    expect(screen.getByLabelText('Course code')).toHaveAttribute('aria-invalid', 'true')
  })

  it('edits and removes an existing mapping', async () => {
    const server = reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(detail({ planner_decision: 'accepted', mapping })),
      'DELETE /mappings/:id': ok({ deleted: true }),
    })
    const { user, router } = renderApp('/recommendations/31/mapping')

    expect(await screen.findByLabelText('Course code')).toHaveValue('CSC 419')
    expect(screen.getByLabelText('Learning outcome 1')).toHaveValue('Secure cloud workloads')
    await user.click(screen.getByRole('button', { name: /Remove mapping/ }))
    await user.click(await screen.findByRole('button', { name: 'Remove' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/recommendations/31'))
    expect(server.calls('DELETE', '/mappings/7')).toHaveLength(1)
  })

  it('refuses recommendations that are not accepted', async () => {
    reviewApi(plannerUser)
    renderApp('/recommendations/31/mapping')

    expect(
      await screen.findByText('Only accepted recommendations can be mapped'),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Course code')).not.toBeInTheDocument()
  })
})

describe('CurriculumPage', () => {
  const course = (overrides: Partial<CurriculumCourse> = {}): CurriculumCourse => ({
    ...mapping,
    recommendation: {
      id: 31,
      rank: 1,
      topic_title: 'Cloud Security and Kubernetes',
      composite_score: 0.6,
      overlap_status: 'No Significant Overlap',
    },
    ...overrides,
  })
  const curriculum = (overrides: Partial<ProposedCurriculum> = {}): ProposedCurriculum => ({
    session: { id: 5, session_name: 'Synthetic 2026 review' },
    courses: [course(), course({ id: 8, course_code: 'CSC 421', credit_units: 2 })],
    total_units: 5,
    credit_unit_allowance: 12,
    remaining_units: 7,
    ...overrides,
  })

  it('lists courses with the total against the allowance', async () => {
    reviewApi(viewerUser, { 'GET /sessions/:id/curriculum': ok(curriculum()) })
    renderApp('/sessions/5/curriculum')

    const table = await screen.findByRole('table', { name: 'Proposed courses' })
    expect(within(table).getByText('CSC 421')).toBeInTheDocument()
    expect(within(table).getByText('Total (2 courses)')).toBeInTheDocument()
    expect(screen.getByText('5 of 12 credit units')).toBeInTheDocument()
    expect(screen.getByText('7 credit units remain.')).toBeInTheDocument()
  })

  it('warns when the courses exceed the allowance', async () => {
    reviewApi(plannerUser, {
      'GET /sessions/:id/curriculum': ok(
        curriculum({ credit_unit_allowance: 4, remaining_units: -1 }),
      ),
    })
    renderApp('/sessions/5/curriculum')

    expect(await screen.findByText('Over the allowance by 1 units')).toBeInTheDocument()
  })

  it('explains a missing allowance and an empty curriculum', async () => {
    reviewApi(plannerUser, {
      'GET /sessions/:id/curriculum': ok(
        curriculum({ courses: [], total_units: 0, credit_unit_allowance: null }),
      ),
    })
    renderApp('/sessions/5/curriculum')

    expect(await screen.findByText('No courses yet')).toBeInTheDocument()
  })
})

describe('EvidencePage', () => {
  const keywords: KeywordResults = {
    overall: [
      { term: 'kubernetes', score: 0.31, passage_count: 12 },
      { term: 'cloud', score: 0.25, passage_count: 20 },
    ],
    by_category: { job_market: [{ term: 'kubernetes', score: 0.4, passage_count: 12 }] },
    passage_count: 60,
  }
  const similarity: SimilarityResults = {
    threshold: 0.8,
    nuc_core_version: { id: 1, version_label: 'Synthetic core v1' },
    candidates: [
      {
        topic_id: 0,
        title: 'Cloud Security',
        max_similarity: 0.62,
        novelty: 0.38,
        overlap_status: 'No Significant Overlap',
        closest_nuc_passage: { id: 900, text: 'Synthetic networks passage.', page_number: 3 },
      },
      {
        topic_id: 1,
        title: 'Operating Systems',
        max_similarity: 0.87,
        novelty: 0.13,
        overlap_status: 'Potential Duplicate',
        closest_nuc_passage: { id: 901, text: 'Synthetic OS passage.', page_number: 9 },
      },
    ],
  }

  it('shows keywords, then the NUC overlap with duplicates highlighted', async () => {
    reviewApi(plannerUser, {
      'GET /sessions/:id/keywords': ok(keywords),
      'GET /sessions/:id/similarity': ok(similarity),
    })
    const { user } = renderApp('/sessions/5/evidence')

    // The Evidence route is lazy-loaded (it brings in the chart library), so allow extra time.
    const keywordTable = await screen.findByRole('table', { name: 'Keywords' }, { timeout: 8000 })
    expect(within(keywordTable).getByText('kubernetes')).toBeInTheDocument()
    expect(within(keywordTable).getByText('0.310')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'NUC overlap' }))
    const overlap = await screen.findByRole('table', { name: 'Overlap with the NUC core' })
    const duplicateRow = within(overlap).getByText('Operating Systems').closest('tr')!
    expect(within(duplicateRow).getByText('Potential Duplicate')).toBeInTheDocument()
    expect(duplicateRow.className).toContain('bg-amber')
    expect(within(overlap).getByText('Cloud Security').closest('tr')!.className).not.toContain(
      'bg-amber',
    )
    expect(
      screen.getByText(/potential duplicate of existing core content \(1 of 2\)/),
    ).toBeInTheDocument()
  })
})
