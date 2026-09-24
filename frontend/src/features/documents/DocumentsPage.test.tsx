import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  adminUser,
  healthyStatus,
  makeDocument,
  page,
  plannerUser,
  viewerUser,
} from '@/test/fixtures'
import { fail, mockApi, ok, type MockRequest } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { User } from '@/types/api'

const counts = { job_market: 2, institutional: 0, policy: 1, academic: 0 }
const documents = [
  makeDocument({ id: 1, title: 'Fintech advert' }),
  makeDocument({
    id: 2,
    title: 'Scanned policy',
    source_category: 'policy',
    processing_status: 'failed',
    error_message: 'No extractable text (scanned PDF). OCR is not supported.',
  }),
  makeDocument({ id: 3, title: 'Security advert', processing_status: 'parsing' }),
]

function libraryApi(user: User, extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    'GET /auth/me': ok(user),
    'GET /health': ok(healthyStatus),
    'GET /documents': (request: MockRequest) => {
      const category = request.params.category as string | undefined
      const items = category ? documents.filter((d) => d.source_category === category) : documents
      return ok({ ...page(items), category_counts: counts })
    },
    ...extra,
  })
}

describe('DocumentsPage', () => {
  it('lists documents with status badges and category counts', async () => {
    libraryApi(plannerUser)
    renderApp('/documents')

    const link = await screen.findByRole('link', { name: 'Fintech advert' })
    const table = screen.getByRole('table')
    expect(link).toHaveAttribute('href', '/documents/1')
    expect(within(table).getByText('Ready')).toBeInTheDocument()
    expect(within(table).getByText('Processing')).toBeInTheDocument()
    expect(within(table).getByLabelText(/Failed: No extractable text/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^All\s*3$/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: /^Job market\s*2$/ })).toBeInTheDocument()
  })

  it('filters by category', async () => {
    const server = libraryApi(plannerUser)
    const { user } = renderApp('/documents')
    await screen.findByText('Fintech advert')

    await user.click(screen.getByRole('button', { name: /^Policy\s*1$/ }))

    await waitFor(() => expect(screen.queryByText('Fintech advert')).not.toBeInTheDocument())
    expect(screen.getByText('Scanned policy')).toBeInTheDocument()
    expect(server.calls('GET', '/documents').at(-1)?.params).toMatchObject({ category: 'policy' })
  })

  it('shows the first-run empty state with an upload button for planners', async () => {
    libraryApi(plannerUser, {
      'GET /documents': ok({
        ...page([]),
        category_counts: { job_market: 0, institutional: 0, policy: 0, academic: 0 },
      }),
    })
    renderApp('/documents')

    expect(await screen.findByRole('heading', { name: 'No documents yet' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Upload documents/ })).toHaveLength(2)
  })

  it('hides upload, archive and delete from viewers', async () => {
    libraryApi(viewerUser)
    const { user } = renderApp('/documents')

    await user.click(await screen.findByRole('button', { name: 'Actions for Fintech advert' }))

    expect(await screen.findByRole('menuitem', { name: /Download original/ })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: /Archive/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: /Delete/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Upload documents/ })).not.toBeInTheDocument()
  })

  it('explains why a document in use cannot be deleted', async () => {
    libraryApi(adminUser, {
      'DELETE /documents/:id': fail(
        409,
        'CONFLICT',
        'This document is used by an analysis session and cannot be deleted. Archive it instead.',
      ),
    })
    const { user } = renderApp('/documents')

    await user.click(await screen.findByRole('button', { name: 'Actions for Fintech advert' }))
    await user.click(await screen.findByRole('menuitem', { name: /Delete/ }))
    const dialog = await screen.findByRole('alertdialog')
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText(/Archive it instead/)).toBeInTheDocument()
  })

  it('shows an error with retry when the list cannot load', async () => {
    libraryApi(plannerUser, { 'GET /documents': fail(500, 'INTERNAL_ERROR', 'Server error.') })
    renderApp('/documents')

    expect(await screen.findByText('Could not load documents')).toBeInTheDocument()
  })
})
