import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, makeDocumentDetail, page, plannerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'
import type { DocumentDetail } from '@/types/api'

function detailApi(detail: DocumentDetail | ReturnType<typeof fail>) {
  return mockApi({
    'GET /auth/me': ok(plannerUser),
    'GET /health': ok(healthyStatus),
    'GET /documents/:id': 'status' in detail ? detail : ok(detail),
    'GET /documents/:id/passages': ok(
      page([
        { id: 101, position: 0, page_number: 1, text: 'Synthetic passage about Python APIs.' },
        { id: 102, position: 1, page_number: 2, text: 'Synthetic passage about cloud security.' },
      ]),
    ),
  })
}

describe('DocumentDetailPage', () => {
  it('shows metadata, passages with page numbers and sessions', async () => {
    detailApi(
      makeDocumentDetail({
        sessions: [
          {
            id: 7,
            session_name: 'Synthetic session',
            status: 'completed',
            created_at: '2026-09-21T00:00:00Z',
          },
        ],
      }),
    )
    renderApp('/documents/10')

    expect(
      await screen.findByRole('heading', { name: 'Synthetic backend engineer advert' }),
    ).toBeInTheDocument()
    expect(screen.getByText('synthetic-backend-ad.pdf')).toBeInTheDocument()
    expect(await screen.findByText('Synthetic passage about cloud security.')).toBeInTheDocument()
    expect(screen.getByText('· Page 2')).toBeInTheDocument()
    expect(screen.getByText('Synthetic session')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Download/ })).toHaveAttribute(
      'href',
      '/api/documents/10/file',
    )
  })

  it('shows the failure reason', async () => {
    detailApi(
      makeDocumentDetail({
        processing_status: 'failed',
        error_message: 'No extractable text (scanned PDF). OCR is not supported.',
        passage_count: 0,
      }),
    )
    renderApp('/documents/10')

    expect(await screen.findByText('Processing failed')).toBeInTheDocument()
    expect(screen.getByText(/OCR is not supported/)).toBeInTheDocument()
  })

  it('shows a processing notice while the document is being parsed', async () => {
    detailApi(makeDocumentDetail({ processing_status: 'parsing', passage_count: 0 }))
    renderApp('/documents/10')

    expect(await screen.findByText(/updates automatically/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Archive/ })).toBeDisabled()
  })

  it('shows the 404 page for unknown documents', async () => {
    detailApi(fail(404, 'NOT_FOUND', 'Document not found.'))
    renderApp('/documents/999')

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
