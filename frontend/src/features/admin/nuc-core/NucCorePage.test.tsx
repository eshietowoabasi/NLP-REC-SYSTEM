import { screen, waitFor } from '@testing-library/react'
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

const base = { 'GET /auth/me': ok(adminUser), 'GET /health': ok(healthyStatus) }

describe('NucCorePage', () => {
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
