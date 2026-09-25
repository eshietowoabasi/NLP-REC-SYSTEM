import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, page } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { SettingItem, SkillPattern, StopWord } from '@/types/api'

/* Synthetic fixtures. */
const item = <K extends SettingItem['key']>(key: K, value: unknown, extra = {}): SettingItem => ({
  key,
  value: value as never,
  default: value as never,
  description: `Synthetic description of ${key}.`,
  updated_at: null,
  updated_by: null,
  ...extra,
})

const settings: SettingItem[] = [
  item('score_weights', { ner: 0.4, topic: 0.35, novelty: 0.25 }),
  item('similarity_threshold', 0.8, {
    updated_at: '2026-09-20T09:00:00Z',
    updated_by: { id: 1, full_name: 'Test Admin' },
  }),
  item('max_recommendations', 20),
  item('passage_sentences', { min: 3, max: 5 }),
  item('passage_words', { min: 100, max: 200 }),
  item('sbert_model', 'all-MiniLM-L6-v2'),
  item('spacy_model', 'en_core_web_sm'),
  item('min_topic_size', 5),
  item('evidence_per_recommendation', 8),
  item('max_documents_per_session', 50),
  item('credit_unit_allowance', null),
]

const patterns: SkillPattern[] = [
  {
    id: 1,
    label: 'TOOL',
    pattern: 'docker',
    canonical_name: 'Docker',
    is_active: true,
    created_at: '2026-09-01T00:00:00Z',
  },
  {
    id: 2,
    label: 'LANGUAGE',
    pattern: [{ LOWER: 'go' }, { LOWER: 'developer' }],
    canonical_name: 'Go',
    is_active: false,
    created_at: '2026-09-01T00:00:00Z',
  },
]

const stopWords: StopWord[] = [
  { id: 1, word: 'applicant', is_active: true, created_at: '2026-09-01T00:00:00Z' },
]

function settingsApi(extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    'GET /auth/me': ok(adminUser),
    'GET /health': ok(healthyStatus),
    'GET /admin/settings': ok({ settings }),
    'GET /admin/skill-patterns': ok(page(patterns)),
    'GET /admin/stop-words': ok(page(stopWords)),
    ...extra,
  })
}

describe('Settings: general', () => {
  it('saves only the changed settings', async () => {
    const server = settingsApi({
      'PUT /admin/settings': ok({ settings, changed: ['similarity_threshold'] }),
    })
    const { user } = renderApp('/admin/settings')

    const threshold = await screen.findByLabelText('Duplicate threshold')
    expect(threshold).toHaveValue(0.8)
    expect(screen.getByText(/Changed by Test Admin/)).toBeInTheDocument()
    const save = screen.getByRole('button', { name: 'Save settings' })
    expect(save).toBeDisabled()

    await user.clear(threshold)
    await user.type(threshold, '0.75')
    await user.type(screen.getByLabelText('30% credit-unit allowance'), '24')
    await user.click(save)

    await waitFor(() => expect(server.calls('PUT', '/admin/settings')).toHaveLength(1))
    expect(server.calls('PUT', '/admin/settings')[0].body).toEqual({
      similarity_threshold: 0.75,
      credit_unit_allowance: 24,
    })
  })

  it('checks the weight sum and ranges before saving', async () => {
    const server = settingsApi()
    const { user } = renderApp('/admin/settings')

    const ner = await screen.findByLabelText('Skill demand (NER)')
    await user.clear(ner)
    await user.type(ner, '0.6')
    expect(screen.getByText(/Sum: 1.20 — the weights must add up to 1.00/)).toBeInTheDocument()
    const words = screen.getByLabelText('Words per passage: minimum')
    await user.clear(words)
    await user.type(words, '300')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    expect(await screen.findByText('The three weights must add up to 1.00.')).toBeInTheDocument()
    expect(screen.getByText('The minimum cannot exceed the maximum.')).toBeInTheDocument()
    expect(server.calls('PUT', '/admin/settings')).toHaveLength(0)
  })

  it('warns before changing the embedding model', async () => {
    settingsApi()
    const { user } = renderApp('/admin/settings')

    const model = await screen.findByLabelText('Embedding model (SBERT)')
    expect(screen.queryByText('Changing the embedding model')).not.toBeInTheDocument()
    await user.clear(model)
    await user.type(model, 'all-mpnet-base-v2')

    expect(screen.getByText('Changing the embedding model')).toBeInTheDocument()
  })

  it('shows server validation errors on the field', async () => {
    settingsApi({
      'PUT /admin/settings': fail(422, 'VALIDATION_ERROR', 'Some fields are invalid.', {
        fields: { spacy_model: ["The spaCy pipeline 'xx_sm' is not installed on the server."] },
      }),
    })
    const { user } = renderApp('/admin/settings')

    const spacy = await screen.findByLabelText('spaCy pipeline')
    await user.clear(spacy)
    await user.type(spacy, 'xx_sm')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    expect(await screen.findByText(/is not installed on the server/)).toBeInTheDocument()
  })
})

describe('Settings: skill patterns', () => {
  it('lists phrase and token patterns and toggles them', async () => {
    const server = settingsApi({
      'PATCH /admin/skill-patterns/:id': ok({ ...patterns[1], is_active: true }),
    })
    const { user } = renderApp('/admin/settings')

    await user.click(await screen.findByRole('tab', { name: 'Skill patterns' }))
    const table = await screen.findByRole('table', { name: 'Skill patterns' })
    expect(await within(table).findByText('“docker”')).toBeInTheDocument()
    expect(within(table).getByText('[{"LOWER":"go"},{"LOWER":"developer"}]')).toBeInTheDocument()
    await user.click(within(table).getByRole('button', { name: /^Activate Go pattern/ }))

    await waitFor(() =>
      expect(server.calls('PATCH', '/admin/skill-patterns/2')[0]?.body).toEqual({
        is_active: true,
      }),
    )
  })

  it('adds a token pattern after checking the JSON', async () => {
    const server = settingsApi({
      'POST /admin/skill-patterns': ok({ ...patterns[1], id: 3, canonical_name: 'Rust' }, 201),
    })
    const { user } = renderApp('/admin/settings')

    await user.click(await screen.findByRole('tab', { name: 'Skill patterns' }))
    await user.click(await screen.findByRole('button', { name: /Add pattern/ }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Canonical name'), 'Rust')
    await user.click(within(dialog).getByRole('radio', { name: 'Token pattern' }))
    const tokens = within(dialog).getByLabelText('Token pattern (JSON)')
    await user.type(tokens, 'not json')
    await user.click(within(dialog).getByRole('button', { name: 'Save pattern' }))
    expect(await within(dialog).findByText(/Enter valid JSON/)).toBeInTheDocument()

    await user.clear(tokens)
    await user.click(tokens)
    await user.paste('[{"LOWER": "rust"}, {"LOWER": "developer"}]')
    await user.click(within(dialog).getByRole('button', { name: 'Save pattern' }))

    await waitFor(() => expect(server.calls('POST', '/admin/skill-patterns')).toHaveLength(1))
    expect(server.calls('POST', '/admin/skill-patterns')[0].body).toEqual({
      label: 'SKILL',
      canonical_name: 'Rust',
      pattern: [{ LOWER: 'rust' }, { LOWER: 'developer' }],
    })
  })

  it('shows the server explanation of an invalid pattern', async () => {
    settingsApi({
      'POST /admin/skill-patterns': fail(409, 'CONFLICT', 'This pattern already exists.', {
        fields: { pattern: ['This pattern already exists for that label.'] },
      }),
    })
    const { user } = renderApp('/admin/settings')

    await user.click(await screen.findByRole('tab', { name: 'Skill patterns' }))
    await user.click(await screen.findByRole('button', { name: /Add pattern/ }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Canonical name'), 'Docker')
    await user.type(within(dialog).getByLabelText('Phrase'), 'docker')
    await user.click(within(dialog).getByRole('button', { name: 'Save pattern' }))

    expect(
      await within(dialog).findByText('This pattern already exists for that label.'),
    ).toBeInTheDocument()
  })
})

describe('Settings: stop words', () => {
  it('adds, rejects duplicates and deactivates stop words', async () => {
    let added = false
    const server = settingsApi({
      'POST /admin/stop-words': () =>
        added
          ? fail(409, 'CONFLICT', "'lagos' is already a stop word.", {
              fields: { word: ["'lagos' is already a stop word."] },
            })
          : ((added = true),
            ok({ id: 2, word: 'lagos', is_active: true, created_at: '2026-09-25T00:00:00Z' }, 201)),
      'PATCH /admin/stop-words/:id': ok({ ...stopWords[0], is_active: false }),
    })
    const { user } = renderApp('/admin/settings')

    await user.click(await screen.findByRole('tab', { name: 'Stop words' }))
    const input = await screen.findByLabelText('Add a stop word')
    await user.type(input, 'two words')
    await user.click(screen.getByRole('button', { name: 'Add' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a single word')

    await user.clear(input)
    await user.type(input, 'Lagos')
    await user.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(server.calls('POST', '/admin/stop-words')).toHaveLength(1))
    expect(server.calls('POST', '/admin/stop-words')[0].body).toEqual({ word: 'lagos' })

    await waitFor(() => expect(input).toHaveValue(''))
    await user.type(input, 'lagos')
    await user.click(screen.getByRole('button', { name: 'Add' }))
    expect(await screen.findByText("'lagos' is already a stop word.")).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Deactivate "applicant"' }))
    await waitFor(() =>
      expect(server.calls('PATCH', '/admin/stop-words/1')[0]?.body).toEqual({ is_active: false }),
    )
  })
})
