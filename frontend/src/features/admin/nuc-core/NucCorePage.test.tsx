import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { adminUser, healthyStatus, makeDocument } from '@/test/fixtures'
import { mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { NucCoreVersion } from '@/types/api'

const version = (overrides: Partial<NucCoreVersion> = {}): NucCoreVersion => ({
  id: 1,
  version_label: 'Synthetic CCMAS v1',
  is_active: true,
  created_at: '2026-09-01T09:00:00Z',
  uploaded_by: { id: 1, full_name: 'Test Admin' },
  document: makeDocument({ id: 50, source_category: 'nuc_core', original_filename: 'core.pdf' }),
  ...overrides,
})

const exclusions = { code_prefixes: ['GST'], title_keywords: ['SIWES'] }
const noCourses = { version: null, exclusions, courses: [], excluded_count: 0 }

const base = {
  'GET /auth/me': ok(adminUser),
  'GET /health': ok(healthyStatus),
  'GET /nuc-core/courses': ok(noCourses),
}

describe('NucCorePage', () => {
  it('lists the courses and marks those excluded from comparison', async () => {
    const active = version()
    const course = (id: number, code: string, title: string, excluded: boolean) => ({
      id,
      code,
      title,
      units: 3,
      page_number: 10 + id,
      excluded,
    })
    mockApi({
      ...base,
      'GET /nuc-core': ok({ active, latest: active }),
      'GET /nuc-core/versions': ok([active]),
      'GET /nuc-core/courses': ok({
        version: active,
        exclusions,
        courses: [
          course(1, 'CSC 301', 'Synthetic Data Structures', false),
          course(2, 'CSC 299', 'SIWES I', true),
          course(3, 'GST 111', 'Synthetic Communication in English', true),
        ],
        excluded_count: 2,
      }),
    })
    const { user } = renderApp('/admin/nuc-core')

    const table = await screen.findByRole('table', { name: 'NUC core courses' })
    expect(
      screen.getByText(/3 courses found. Topics are compared with 1 of them; 2 are excluded/),
    ).toHaveTextContent('(GST courses, “SIWES”)')
    expect(within(table).getAllByText('Excluded from comparison')).toHaveLength(2)
    expect(within(table).getByText('CSC 301').closest('tr')).toHaveTextContent('Compared')

    await user.click(screen.getByLabelText('Show only excluded courses'))
    expect(within(table).queryByText('CSC 301')).not.toBeInTheDocument()
    expect(within(table).getByText('GST 111')).toBeInTheDocument()
  })

  it('explains when no course headers were recognised', async () => {
    const active = version()
    mockApi({
      ...base,
      'GET /nuc-core': ok({ active, latest: active }),
      'GET /nuc-core/versions': ok([active]),
      'GET /nuc-core/courses': ok({ ...noCourses, version: active }),
    })
    renderApp('/admin/nuc-core')

    expect(
      await screen.findByText(/topics are compared with short extracts of the NUC core instead/),
    ).toBeInTheDocument()
  })

  it('warns that sessions cannot run without an active version', async () => {
    mockApi({
      ...base,
      'GET /nuc-core': ok({ active: null, latest: null }),
      'GET /nuc-core/versions': ok([]),
    })
    renderApp('/admin/nuc-core')

    expect(await screen.findByText('No active NUC core reference')).toBeInTheDocument()
    expect(screen.getByText('No versions uploaded yet.')).toBeInTheDocument()
  })

  it('shows the active version and a failed newer upload', async () => {
    const active = version()
    const failed = version({
      id: 2,
      version_label: 'Scanned v2',
      is_active: false,
      document: makeDocument({
        id: 51,
        source_category: 'nuc_core',
        processing_status: 'failed',
        error_message: 'No extractable text (scanned PDF). OCR is not supported.',
      }),
    })
    mockApi({
      ...base,
      'GET /nuc-core': ok({ active, latest: failed }),
      'GET /nuc-core/versions': ok([failed, active]),
    })
    renderApp('/admin/nuc-core')

    expect(await screen.findByText('“Scanned v2” could not be processed')).toBeInTheDocument()
    expect(screen.getByText(/The previous version remains active/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View extracted text' })).toHaveAttribute(
      'href',
      '/documents/50',
    )
  })

  it('uploads a new version with its label', async () => {
    const server = mockApi({
      ...base,
      'GET /nuc-core': ok({ active: null, latest: null }),
      'GET /nuc-core/versions': ok([]),
      'POST /nuc-core': ok(version({ is_active: false }), 201),
    })
    const { user } = renderApp('/admin/nuc-core')

    await user.click(await screen.findByRole('button', { name: /Upload version/ }))
    expect(await screen.findByText('Enter a version label.')).toBeInTheDocument()
    expect(screen.getByText('Choose the NUC core document.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Version label'), 'Synthetic CCMAS v1')
    await user.upload(
      screen.getByLabelText('Document'),
      new File(['Synthetic core text'], 'core.pdf', { type: 'application/pdf' }),
    )
    await user.click(screen.getByRole('button', { name: /Upload version/ }))

    await waitFor(() => expect(server.calls('POST', '/nuc-core')).toHaveLength(1))
    const form = server.calls('POST', '/nuc-core')[0].body as FormData
    expect(form.get('version_label')).toBe('Synthetic CCMAS v1')
    expect((form.get('file') as File).name).toBe('core.pdf')
  })
})
