import { describe, expect, it, vi } from 'vitest'

import { fail, mockApi, ok, TEST_CSRF_TOKEN } from '@/test/server'

import { ApiError, apiGet, apiPost, setUnauthorizedHandler } from './api'

describe('api client', () => {
  it('returns the data of a success envelope', async () => {
    mockApi({ 'GET /things': ok([1, 2, 3]) })

    await expect(apiGet('/things')).resolves.toEqual([1, 2, 3])
  })

  it('turns an error envelope into an ApiError with code, status and details', async () => {
    mockApi({
      'GET /things': fail(422, 'VALIDATION_ERROR', 'Bad input.', { fields: { a: ['x'] } }),
    })

    const error = await apiGet('/things').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      code: 'VALIDATION_ERROR',
      status: 422,
      message: 'Bad input.',
      details: { fields: { a: ['x'] } },
    })
  })

  it('fetches a CSRF token once and sends it on state-changing requests only', async () => {
    const server = mockApi({ 'POST /things': ok({}), 'GET /things': ok([]) })

    await apiPost('/things', { a: 1 })
    await apiPost('/things', { a: 2 })
    await apiGet('/things')

    expect(server.calls('GET', '/auth/csrf')).toHaveLength(1)
    const [first, second] = server.calls('POST', '/things')
    expect(first.headers['X-CSRFToken']).toBe(TEST_CSRF_TOKEN)
    expect(second.headers['X-CSRFToken']).toBe(TEST_CSRF_TOKEN)
    expect(server.calls('GET', '/things')[0].headers['X-CSRFToken']).toBeUndefined()
  })

  it('switches to the new token returned by login', async () => {
    const server = mockApi({
      'POST /auth/login': ok({ user: {}, csrf_token: 'after-login-token' }),
      'POST /things': ok({}),
    })

    await apiPost('/auth/login', {})
    await apiPost('/things')

    expect(server.calls('POST', '/things')[0].headers['X-CSRFToken']).toBe('after-login-token')
  })

  it('refreshes the token and retries once when the server rejects it', async () => {
    let attempts = 0
    const server = mockApi({
      'POST /things': () => {
        attempts += 1
        return attempts === 1 ? fail(400, 'CSRF_FAILED', 'Expired.') : ok({ saved: true })
      },
    })

    await expect(apiPost('/things')).resolves.toEqual({ saved: true })
    expect(server.calls('GET', '/auth/csrf')).toHaveLength(2)
    expect(server.calls('POST', '/things')).toHaveLength(2)
  })

  it('does not retry a CSRF failure more than once', async () => {
    const server = mockApi({ 'POST /things': fail(400, 'CSRF_FAILED', 'Expired.') })

    await expect(apiPost('/things')).rejects.toMatchObject({ code: 'CSRF_FAILED' })
    expect(server.calls('POST', '/things')).toHaveLength(2)
  })

  it('calls the unauthorized handler on 401, except for the session check itself', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockApi({
      'GET /things': fail(401, 'UNAUTHORIZED', 'Please log in.'),
      'GET /auth/me': fail(401, 'UNAUTHORIZED', 'Please log in.'),
    })

    await apiGet('/auth/me').catch(() => undefined)
    expect(handler).not.toHaveBeenCalled()

    await apiGet('/things').catch(() => undefined)
    expect(handler).toHaveBeenCalledOnce()
  })
})
