import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { healthyStatus, makeDocument, page, plannerUser } from '@/test/fixtures'
import { fail, mockApi, ok } from '@/test/server'
import { renderApp } from '@/test/utils'

const emptyLibrary = {
  ...page([]),
  category_counts: { job_market: 0, institutional: 0, policy: 0, academic: 0 },
}

function file(name: string, content = 'Synthetic test content.', type = 'application/pdf') {
  return new File([content], name, { type })
}

async function openDialog() {
  const view = renderApp('/documents')
  const [button] = await screen.findAllByRole('button', { name: /Upload documents/ })
  await view.user.click(button)
  return { ...view, dialog: await screen.findByRole('dialog') }
}

async function chooseCategory(
  user: ReturnType<typeof renderApp>['user'],
  fileName: string,
  label: string,
) {
  await user.click(screen.getByLabelText(`Category for ${fileName}`))
  await user.click(await screen.findByRole('option', { name: new RegExp(`^${label}`) }))
}

describe('UploadDialog', () => {
  it('rejects unsupported files before uploading', async () => {
    mockApi({
      'GET /auth/me': ok(plannerUser),
      'GET /health': ok(healthyStatus),
      'GET /documents': ok(emptyLibrary),
    })
    const { user, dialog } = await openDialog()

    await user.upload(
      within(dialog).getByLabelText('Files to upload'),
      file('photo.png', 'x', 'image/png'),
    )

    expect(within(dialog).getByText(/Unsupported file type/)).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: /^Upload/ })).toBeDisabled()
  })

  it('requires a category for every file', async () => {
    mockApi({
      'GET /auth/me': ok(plannerUser),
      'GET /health': ok(healthyStatus),
      'GET /documents': ok(emptyLibrary),
    })
    const { user, dialog } = await openDialog()

    await user.upload(within(dialog).getByLabelText('Files to upload'), file('ad.pdf'))

    expect(within(dialog).getByRole('button', { name: 'Upload 1 file' })).toBeDisabled()
    expect(within(dialog).getByText(/Choose a category for each file/)).toBeInTheDocument()
  })

  it('uploads each file separately and reports per-file results', async () => {
    const server = mockApi({
      'GET /auth/me': ok(plannerUser),
      'GET /health': ok(healthyStatus),
      'GET /documents': ok(emptyLibrary),
      'POST /documents': (request) => {
        const form = request.body as FormData
        const upload = form.get('files') as File
        if (upload.name === 'copy.pdf') {
          return fail(422, 'VALIDATION_ERROR', 'None of the files could be accepted.', {
            rejected: [
              { filename: 'copy.pdf', reason: 'This file has already been uploaded as “ad”.' },
            ],
          })
        }
        return ok(
          { accepted: [makeDocument({ original_filename: upload.name })], rejected: [] },
          201,
        )
      },
    })
    const { user, dialog } = await openDialog()

    await user.upload(within(dialog).getByLabelText('Files to upload'), [
      file('ad.pdf'),
      file('copy.pdf'),
    ])
    await user.click(within(dialog).getByLabelText('Set all to'))
    await user.click(await screen.findByRole('option', { name: 'Policy' }))
    await chooseCategory(user, 'copy.pdf', 'Academic')
    await user.click(within(dialog).getByRole('button', { name: 'Upload 2 files' }))

    expect(await within(dialog).findByText('Uploaded; processing has started.')).toBeInTheDocument()
    expect(within(dialog).getByText(/already been uploaded as “ad”/)).toBeInTheDocument()
    await waitFor(() =>
      expect(within(dialog).getByRole('button', { name: 'Done' })).toBeInTheDocument(),
    )

    const posts = server.calls('POST', '/documents')
    expect(posts).toHaveLength(2)
    const categories = posts.map((post) => (post.body as FormData).get('categories'))
    expect(categories).toEqual(['policy', 'academic'])
  })
})
