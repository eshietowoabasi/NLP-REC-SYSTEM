import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, describeError, onUnauthorized } from '../../src/services/api'

function mockFetch(status, body) {
  global.fetch = vi.fn().mockResolvedValue({ ok: status < 400, status, statusText: 'x', json: () => Promise.resolve(body) })
  return global.fetch
}

afterEach(() => vi.restoreAllMocks())

describe('api client', () => {
  it('sends JSON with cookies and drops empty query params', async () => {
    const fetch = mockFetch(200, { success: true })
    await api.get('/documents', { status: 'Parsed', q: '', page: 2 })
    expect(fetch).toHaveBeenCalledWith('/api/documents?status=Parsed&page=2', expect.objectContaining({ credentials: 'same-origin' }))
    await api.post('/sessions', { a: 1 })
    const [, options] = fetch.mock.calls.at(-1)
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(options.body).toBe('{"a":1}')
  })

  it('raises ApiError from the error model', async () => {
    mockFetch(422, { success: false, error: { code: 'VALIDATION_ERROR', message: 'Invalid', details: { course_code: 'Bad code' } } })
    const error = await api.post('/x', {}).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('VALIDATION_ERROR')
    expect(describeError(error)).toBe('Invalid (course code: Bad code)')
  })

  it('calls the unauthorized handler on 401 except for login', async () => {
    const handler = vi.fn()
    onUnauthorized(handler)
    mockFetch(401, { success: false, error: { code: 'UNAUTHORIZED', message: 'Authentication required' } })
    await api.get('/dashboard/summary').catch(() => {})
    expect(handler).toHaveBeenCalledTimes(1)
    await api.post('/auth/login', {}).catch(() => {})
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('reports network failures clearly', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    const error = await api.get('/x').catch((e) => e)
    expect(error.code).toBe('NETWORK_ERROR')
  })
})
