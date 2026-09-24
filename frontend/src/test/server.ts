import { AxiosError, type AxiosAdapter, type AxiosResponse } from 'axios'

import { api } from '@/lib/api'

/**
 * A tiny in-memory API for tests, installed as the Axios adapter so the real request and
 * response interceptors (CSRF header, token refresh, 401 handling) still run.
 *
 *   const server = mockApi({
 *     'GET /auth/me': ok(adminUser),
 *     'PATCH /admin/users/:id': (req, params) => ok({ ...user, id: Number(params.id) }),
 *   })
 *
 * GET /auth/csrf answers with a test token unless a handler overrides it; unmatched requests
 * get a 404 error envelope.
 */

export interface MockRequest {
  method: string
  url: string
  params: Record<string, unknown>
  body: unknown
  headers: Record<string, unknown>
}

export interface MockResponse {
  status: number
  body: unknown
}

type Handler =
  MockResponse | ((request: MockRequest, params: Record<string, string>) => MockResponse)

export const ok = (data: unknown, status = 200): MockResponse => ({
  status,
  body: { success: true, data },
})

export const fail = (
  status: number,
  code: string,
  message = 'Request failed.',
  details: Record<string, unknown> = {},
): MockResponse => ({ status, body: { success: false, error: { code, message, details } } })

/** A promise that never settles, for asserting loading states. */
export const pending = (): never => {
  throw new PendingRequest()
}
class PendingRequest extends Error {}

export const TEST_CSRF_TOKEN = 'test-csrf-token'

export function mockApi(handlers: Record<string, Handler>) {
  const requests: MockRequest[] = []
  const routes = Object.entries(handlers).map(([key, handler]) => {
    const [method, path] = key.split(' ')
    const names: string[] = []
    const pattern = path.replace(/:(\w+)/g, (_, name: string) => {
      names.push(name)
      return '([^/]+)'
    })
    return { method, regex: new RegExp(`^${pattern}$`), names, handler }
  })

  const adapter: AxiosAdapter = async (config) => {
    const method = (config.method ?? 'get').toUpperCase()
    const url = config.url ?? ''
    const body = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
    const request: MockRequest = {
      method,
      url,
      params: (config.params ?? {}) as Record<string, unknown>,
      body,
      headers: config.headers.toJSON() as Record<string, unknown>,
    }
    requests.push(request)

    const route = routes.find((r) => r.method === method && r.regex.test(url))
    let result: MockResponse
    if (route) {
      const match = route.regex.exec(url) ?? []
      const params = Object.fromEntries(route.names.map((name, i) => [name, match[i + 1]]))
      try {
        result =
          typeof route.handler === 'function' ? route.handler(request, params) : route.handler
      } catch (error) {
        if (error instanceof PendingRequest) return new Promise<AxiosResponse>(() => undefined)
        throw error
      }
    } else if (method === 'GET' && url === '/auth/csrf') {
      result = ok({ csrf_token: TEST_CSRF_TOKEN })
    } else {
      result = fail(404, 'NOT_FOUND', `No mock for ${method} ${url}`)
    }

    const response: AxiosResponse = {
      data: result.body,
      status: result.status,
      statusText: '',
      headers: {},
      config,
      request: {},
    }
    if (result.status >= 400) {
      throw new AxiosError(
        `Request failed with status code ${result.status}`,
        'ERR_BAD_REQUEST',
        config,
        {},
        response,
      )
    }
    return response
  }

  api.defaults.adapter = adapter

  return {
    requests,
    /** Requests matching a method and exact URL, in order. */
    calls: (method: string, url: string) =>
      requests.filter((r) => r.method === method.toUpperCase() && r.url === url),
  }
}

/** Simulate a network failure (no response at all). */
export function networkDown(): void {
  api.defaults.adapter = async (config) => {
    throw new AxiosError('Network Error', 'ERR_NETWORK', config)
  }
}
