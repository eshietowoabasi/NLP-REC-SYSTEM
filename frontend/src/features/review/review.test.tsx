import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

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
  Report,
  SessionDetail,
  SessionProgress,
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
  closest_nuc_course: null,
  planner_decision: null,
  planner_notes: null,
  decided_at: null,
  decided_by: null,
  has_mapping: false,
  course: null,
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
    with_courses: 0,
    accepted_with_courses: 0,
  },
}

const progress = (overrides: Partial<SessionProgress> = {}): SessionProgress => ({
  session_status: 'completed',
  total: 3,
  reviewed: 2,
  accepted: 1,
  rejected: 0,
  flagged: 1,
  courses: 0,
  accepted_with_courses: 0,
  latest_report: null,
  ...overrides,
})

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
    'GET /sessions/:id/progress': ok(progress()),
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
    expect(within(items[0]).getByText('Not in NUC core')).toBeInTheDocument()
    // Decided: a clear status, no decision buttons, and the next step for accepted topics.
    expect(within(items[0]).getByText('Accepted')).toBeInTheDocument()
    expect(within(items[0]).queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument()
    expect(within(items[0]).getByRole('link', { name: /Design course/ })).toHaveAttribute(
      'href',
      '/recommendations/31/mapping',
    )
    expect(within(items[2]).getByText('Discuss later')).toBeInTheDocument()
    // Undecided: Accept / Reject / Discuss later.
    expect(within(items[1]).getByText('May already be in NUC core')).toBeInTheDocument()
    const buttons = within(items[1])
      .getAllByRole('button')
      .map((b) => b.textContent)
    expect(buttons).toEqual(['Accept', 'Reject', 'Discuss later'])
    // The score out of 100 and its three weighted parts, readable without the colours; the
    // contributed points add up to the total (36 + 17 + 7 = 60).
    expect(
      within(items[0]).getByRole('figure', {
        name:
          'Score 60/100. Employer demand 90 (High, counts for 40%) adds 36 points; ' +
          'How often it comes up 50 (Medium, counts for 35%) adds 17 points; ' +
          'How new it is 30 (Low, counts for 25%) adds 7 points.',
      }),
    ).toBeInTheDocument()
    expect(within(items[0]).getByText('High')).toBeInTheDocument()
    expect(screen.getByText(/Each has a score out of 100: employer demand/)).toHaveTextContent(
      'employer demand counts for 40%, how often it comes up counts for 35% and how new it is counts for 25%',
    )
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
    expect(screen.getByText(/1 topic may already be in the NUC core/)).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Accepted/ })).toHaveTextContent(
      'Accepted1 · 0 with courses',
    )
  })

  it('shows the three workflow steps with live counts and links', async () => {
    reviewApi(plannerUser)
    renderApp('/sessions/5/recommendations')

    const steps = within(await screen.findByRole('navigation', { name: 'Session progress' }))
    const review = steps.getByRole('link', { name: 'Step 1: Review, 2 of 3 reviewed' })
    expect(review).toHaveAttribute('href', '/sessions/5/recommendations?decision=undecided')
    expect(review).toHaveAttribute('aria-current', 'step')
    expect(
      steps.getByRole('link', { name: 'Step 2: Design courses, 0 courses designed · 1 accepted' }),
    ).toBeInTheDocument()
    expect(steps.getByRole('link', { name: /Step 3: Report/ })).toHaveAttribute(
      'href',
      '/reports?session=5',
    )
    expect(steps.getByText('report not generated')).toBeInTheDocument()
    expect(screen.queryByText('All reviewed.')).not.toBeInTheDocument()
  })

  it('suggests designing the accepted courses once everything is reviewed', async () => {
    reviewApi(plannerUser, {
      'GET /sessions/:id/progress': ok(
        progress({ reviewed: 3, accepted: 2, courses: 1, accepted_with_courses: 1 }),
      ),
    })
    renderApp('/sessions/5/recommendations')

    expect(await screen.findByText('All reviewed.')).toBeInTheDocument()
    expect(screen.getByText(/You accepted 2 \(1 already designed\)/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Design their courses/ })).toHaveAttribute(
      'href',
      '/sessions/5/recommendations?decision=accepted',
    )
  })

  it('downloads the report in one click when every accepted topic has a course', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const ready: Report = {
      id: 77,
      session: { id: 5, session_name: 'Synthetic 2026 review' },
      format: 'docx',
      sections: [],
      status: 'completed',
      error_message: null,
      file_size: 2048,
      created_by: { id: 2, full_name: 'Test Planner' },
      created_at: '2026-09-27T10:00:00Z',
      completed_at: '2026-09-27T10:00:05Z',
    }
    const server = reviewApi(plannerUser, {
      'GET /sessions/:id/progress': ok(
        progress({ reviewed: 3, accepted: 1, courses: 1, accepted_with_courses: 1 }),
      ),
      'POST /sessions/:id/reports': ok(ready, 201),
    })
    const { user } = renderApp('/sessions/5/recommendations')

    expect(await screen.findByText('Ready.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Download your report/ }))

    await waitFor(() => expect(click).toHaveBeenCalled())
    expect(server.calls('POST', '/sessions/5/reports')[0].body).toEqual({ format: 'docx' })
    expect(await screen.findByText('Report ready. The download has started.')).toBeInTheDocument()
    click.mockRestore()
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
    await user.click(screen.getByLabelText('Hide topics that may already be in the NUC core'))
    await waitFor(() =>
      expect(server.calls('GET', '/sessions/5/recommendations').at(-1)?.params).toEqual({
        decision: 'undecided',
        hide_duplicates: 'true',
      }),
    )
  })

  it('opens with the decision filter from the link (dashboard "Awaiting review")', async () => {
    const server = reviewApi(plannerUser)
    renderApp('/sessions/5/recommendations?decision=undecided')

    expect(await screen.findByRole('radio', { name: /Undecided/ })).toBeChecked()
    expect(server.calls('GET', '/sessions/5/recommendations')[0].params).toEqual({
      decision: 'undecided',
    })
    expect(screen.getByRole('link', { name: /Download CSV/ })).toHaveAttribute(
      'href',
      '/api/sessions/5/recommendations/export',
    )
  })

  it('accepts in one click, then offers to design the course', async () => {
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

    expect(await screen.findByText('Accepted. Next: design this course')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Design course' })).toBeInTheDocument()
    expect(server.calls('PATCH', '/recommendations/32/decision')[0].body).toEqual({
      decision: 'accepted',
    })
  })

  it('changes or clears a decision through "Change decision"', async () => {
    const server = reviewApi(plannerUser, {
      'PATCH /recommendations/:id/decision': (request, params) =>
        ok(
          rec({ id: Number(params.id), planner_decision: decisionBody(request).decision as never }),
        ),
    })
    const { user } = renderApp('/sessions/5/recommendations')

    const items = within(
      await screen.findByRole('list', { name: 'Ranked recommendations' }),
    ).getAllByRole('listitem')
    await user.click(within(items[0]).getByRole('button', { name: 'Change decision' }))
    const group = within(items[0]).getByRole('group', {
      name: 'Decision for Cloud Security and Kubernetes',
    })
    expect(within(group).getByRole('button', { name: 'Accept' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await user.click(within(group).getByRole('button', { name: 'Accept' }))

    await waitFor(() =>
      expect(server.calls('PATCH', '/recommendations/31/decision')).toHaveLength(1),
    )
    expect(
      decisionBody(server.calls('PATCH', '/recommendations/31/decision')[0]).decision,
    ).toBeNull()
  })

  it('shows the designed course instead of the Design course button', async () => {
    reviewApi(plannerUser, {
      'GET /sessions/:id/recommendations': ok({
        ...list,
        items: [
          rec({
            planner_decision: 'accepted',
            has_mapping: true,
            course: {
              course_code: 'CSC 419',
              course_title: 'Cloud Security Engineering',
              credit_units: 3,
            },
          }),
        ],
      }),
    })
    renderApp('/sessions/5/recommendations')

    const item = within(await screen.findByRole('list', { name: 'Ranked recommendations' }))
    expect(item.getByText(/Course:/).closest('p')).toHaveTextContent(
      /Course: CSC 419 – Cloud Security Engineering\s*·\s*Edit/,
    )
    expect(item.getByRole('link', { name: 'Edit course CSC 419' })).toHaveAttribute(
      'href',
      '/recommendations/31/mapping',
    )
    expect(item.queryByRole('link', { name: /Design course/ })).not.toBeInTheDocument()
    // A designed course locks the decision (remove the course first).
    expect(item.queryByRole('button', { name: 'Change decision' })).not.toBeInTheDocument()
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
  it('shows points out of 100, the exact calculation on request, overlap and evidence', async () => {
    reviewApi(plannerUser)
    const { user } = renderApp('/recommendations/31')

    expect(await screen.findByText(/points/, { selector: 'p strong' })).toHaveTextContent(
      '60 points',
    )
    expect(screen.getByText(/\(employer demand\)/).closest('p')).toHaveTextContent(
      '36 (employer demand) + 17 (how often it comes up) + 7 (how new it is) = 60 points out of 100',
    )
    expect(screen.queryByLabelText('Composite score formula')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Show calculation' }))
    expect(screen.getByLabelText('Composite score formula')).toHaveTextContent(
      '0.40 × 0.90 (skill demand) + 0.35 × 0.50 (theme strength) + 0.25 × 0.30 (novelty) = 0.60',
    )
    expect(screen.getByRole('button', { name: 'Hide calculation' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )

    expect(screen.getByText('Synthetic core passage on computer networks.')).toBeInTheDocument()
    expect(screen.getByText('Synthetic core v1 · p. 14')).toBeInTheDocument()
    expect(
      screen.getByText(/70% similar to the closest NUC core extract; above 80%/),
    ).toBeInTheDocument()

    const advert = screen.getByRole('region', { name: 'Synthetic cloud advert' })
    expect(within(advert).getAllByRole('listitem')).toHaveLength(2)
    expect(within(advert).getByText(/Page 2 · 80% relevant/)).toBeInTheDocument()
    const policy = screen.getByRole('region', { name: 'Synthetic ICT policy' })
    expect(within(policy).getByText(/Extract 5 · 88% relevant/)).toBeInTheDocument()
  })

  it('shows the keywords as written and an example with its readable source', async () => {
    reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(
        detail({
          keywords: [
            { term: 'problem solve', label: 'problem solving', weight: 0.3 },
            { term: 'kubernetes', label: 'Kubernetes', weight: 0.2 },
          ],
          evidence: [
            {
              passage_id: 101,
              relevance_score: 0.93,
              text: 'Synthetic advert passage about Kubernetes clusters.',
              page_number: 1,
              position: 0,
              document: {
                id: 11,
                title: 'Synthetic DevOps Engineer – Acme',
                source_category: 'job_market',
                source: 'MyJobMag',
                published_on: '2026-09-18',
                label: 'Synthetic DevOps Engineer – Acme, job advert (MyJobMag, Sep 2026)',
              },
            },
          ],
        }),
      ),
    })
    renderApp('/recommendations/31')

    expect(await screen.findByText('Keywords:')).toBeInTheDocument()
    expect(screen.getByText('Keywords:').closest('p')).toHaveTextContent(
      'Keywords: problem solving, Kubernetes',
    )
    const example = screen.getByText(/Example from a job advert/).closest('figure')!
    expect(example).toHaveTextContent(
      'Example from a job advert (Synthetic DevOps Engineer – Acme, MyJobMag, Sep 2026):',
    )
    expect(example).toHaveTextContent('“Synthetic advert passage about Kubernetes clusters.”')
    expect(
      screen.getByRole('region', {
        name: 'Synthetic DevOps Engineer – Acme, job advert (MyJobMag, Sep 2026)',
      }),
    ).toBeInTheDocument()
  })

  it('names the closest NUC course when themes were compared with courses', async () => {
    reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(
        detail({
          max_similarity: 0.63,
          closest_nuc_course: {
            id: 7,
            code: 'SEN 304',
            title: 'Software Testing & Quality Assurance',
            units: 2,
            page_number: 219,
          },
        }),
      ),
    })
    renderApp('/recommendations/31')

    const similar = await screen.findByText('63% similar')
    expect(similar.closest('p')).toHaveTextContent(
      '63% similar to the closest NUC course: SEN 304 – Software Testing & Quality Assurance · 2 units · p. 219',
    )
    expect(
      screen.getByText(/We compared this topic with every NUC core course/),
    ).toBeInTheDocument()
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

  it('decides in one click, then offers to design the course and saves notes', async () => {
    const server = reviewApi(plannerUser, {
      'PATCH /recommendations/:id/decision': (request) =>
        ok(
          rec({
            planner_decision: decisionBody(request).decision as never,
            planner_notes: (request.body as { notes?: string }).notes ?? null,
          }),
        ),
    })
    const { user } = renderApp('/recommendations/31')

    await user.click(await screen.findByRole('button', { name: 'Accept' }))
    expect(await screen.findByRole('link', { name: /Design course/ })).toHaveAttribute(
      'href',
      '/recommendations/31/mapping',
    )
    expect(screen.queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument()
    expect(server.calls('PATCH', '/recommendations/31/decision')[0].body).toEqual({
      decision: 'accepted',
    })

    const save = screen.getByRole('button', { name: 'Save notes' })
    expect(save).toBeDisabled()
    await user.type(screen.getByLabelText('Notes'), 'Strong demand.')
    await user.click(save)
    await waitFor(() =>
      expect(server.calls('PATCH', '/recommendations/31/decision')).toHaveLength(2),
    )
    expect(server.calls('PATCH', '/recommendations/31/decision')[1].body).toEqual({
      decision: 'accepted',
      notes: 'Strong demand.',
    })
  })

  it('shows the designed course and locks the decision', async () => {
    reviewApi(plannerUser, {
      'GET /recommendations/:id': ok(
        detail({
          planner_decision: 'accepted',
          has_mapping: true,
          mapping,
          course: {
            course_code: 'CSC 419',
            course_title: 'Cloud Security Engineering',
            credit_units: 3,
          },
        }),
      ),
    })
    renderApp('/recommendations/31')

    expect(await screen.findByRole('link', { name: 'Edit course CSC 419' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Change decision' })).not.toBeInTheDocument()
    expect(screen.getByText(/remove the course first/)).toBeInTheDocument()
    expect(screen.getByText(/3 credit units · 1 learning outcome/)).toBeInTheDocument()
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
    await user.click(screen.getByRole('button', { name: 'Save course' }))
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
    await user.click(screen.getByRole('button', { name: 'Save course' }))

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
    await user.click(screen.getByRole('button', { name: 'Save course' }))

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
    await user.click(screen.getByRole('button', { name: /Remove course/ }))
    await user.click(await screen.findByRole('button', { name: 'Remove' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/recommendations/31'))
    expect(server.calls('DELETE', '/mappings/7')).toHaveLength(1)
  })

  it('refuses recommendations that are not accepted', async () => {
    reviewApi(plannerUser)
    renderApp('/recommendations/31/mapping')

    expect(
      await screen.findByText('Only accepted recommendations can have a course'),
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
    basis: 'course',
    nuc_core_version: { id: 1, version_label: 'Synthetic core v1' },
    candidates: [
      {
        topic_id: 0,
        title: 'Cloud Security',
        max_similarity: 0.62,
        novelty: 0.38,
        overlap_status: 'No Significant Overlap',
        closest_nuc_passage: { id: 900, text: 'Synthetic networks passage.', page_number: 3 },
        closest_nuc_course: {
          id: 1,
          code: 'CSC 311',
          title: 'Computer Networks',
          units: 3,
          page_number: 40,
        },
      },
      {
        topic_id: 1,
        title: 'Operating Systems',
        max_similarity: 0.87,
        novelty: 0.13,
        overlap_status: 'Potential Duplicate',
        closest_nuc_passage: { id: 901, text: 'Synthetic OS passage.', page_number: 9 },
        closest_nuc_course: {
          id: 2,
          code: 'CSC 301',
          title: 'Operating Systems I',
          units: 3,
          page_number: 38,
        },
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

    await user.click(screen.getByRole('tab', { name: 'NUC core' }))
    const overlap = await screen.findByRole('table', { name: 'Overlap with the NUC core' })
    const duplicateRow = within(overlap).getByText('Operating Systems').closest('tr')!
    expect(within(duplicateRow).getByText('May already be in NUC core')).toBeInTheDocument()
    expect(within(duplicateRow).getByText('CSC 301')).toBeInTheDocument()
    expect(within(duplicateRow).getByText(/Operating Systems I$/)).toBeInTheDocument()
    expect(duplicateRow.className).toContain('bg-amber')
    expect(within(overlap).getByText('Cloud Security').closest('tr')!.className).not.toContain(
      'bg-amber',
    )
    expect(screen.getByText(/may duplicate existing core content \(1 of 2\)/)).toBeInTheDocument()
  })
})
