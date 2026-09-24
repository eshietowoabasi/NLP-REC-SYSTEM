import axios, { AxiosError, type Method } from 'axios'

import type { ApiEnvelope, ApiErrorBody, CsrfTokenResponse } from '@/types/api'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** Set on the single automatic retry after a CSRF failure, so it is never retried again. */
    csrfRetry?: boolean
  }
}

/**
 * Axios instance for the Flask API. Requests go to the same origin (/api), so the session
 * cookie is sent automatically: Vite proxies /api in development and Nginx does in Docker.
 *
 * CSRF: every state-changing request carries the X-CSRFToken header. The token is fetched
 * from GET /api/auth/csrf on first use, replaced whenever a response includes a new one
 * (login and logout do), and refreshed once automatically if the server rejects it.
 */
export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { Accept: 'application/json' },
  timeout: 30_000,
})

/** Error thrown by API helpers; carries the server's error envelope when there was one. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number | null
  readonly details: Record<string, unknown>

  constructor(body: ApiErrorBody, status: number | null) {
    super(body.message)
    this.name = 'ApiError'
    this.code = body.code
    this.status = status
    this.details = body.details
  }
}

function isEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return typeof value === 'object' && value !== null && 'success' in value
}

/** Convert any Axios failure into an ApiError with a human-readable message. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? null
    const body: unknown = error.response?.data
    if (isEnvelope(body) && !body.success) return new ApiError(body.error, status)
    if (!error.response) {
      return new ApiError(
        { code: 'NETWORK_ERROR', message: 'Cannot reach the server.', details: {} },
        null,
      )
    }
    return new ApiError(
      { code: 'HTTP_ERROR', message: `Request failed (${status}).`, details: {} },
      status,
    )
  }
  return new ApiError(
    { code: 'UNKNOWN_ERROR', message: 'Something went wrong.', details: {} },
    null,
  )
}

/* ------------------------------------------------------------------ CSRF */

const SAFE_METHODS = new Set(['get', 'head', 'options'])
let csrfToken: string | null = null
let csrfRequest: Promise<string> | null = null

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken
  csrfRequest ??= api
    .get<ApiEnvelope<CsrfTokenResponse>>('/auth/csrf')
    .then((response) => {
      if (!response.data.success) throw new ApiError(response.data.error, response.status)
      csrfToken = response.data.data.csrf_token
      return csrfToken
    })
    .finally(() => {
      csrfRequest = null
    })
  return csrfRequest
}

/* ------------------------------------------------------------ 401 handling */

let unauthorizedHandler: (() => void) | null = null

/** Called whenever a request fails with 401 (session expired or ended elsewhere). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

/** Forget cached per-session state (used by tests). */
export function resetApiState(): void {
  csrfToken = null
  csrfRequest = null
  unauthorizedHandler = null
}

api.interceptors.request.use(async (config) => {
  if (!SAFE_METHODS.has((config.method ?? 'get').toLowerCase())) {
    config.headers.set('X-CSRFToken', await getCsrfToken())
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const body: unknown = response.data
    if (isEnvelope(body) && body.success) {
      const data = body.data as { csrf_token?: unknown } | null
      if (data && typeof data === 'object' && typeof data.csrf_token === 'string') {
        csrfToken = data.csrf_token
      }
    }
    return response
  },
  async (error: unknown) => {
    if (error instanceof AxiosError && error.config) {
      const apiError = toApiError(error)
      // Axios builds a new config object for every request, so the "already retried" mark
      // must travel inside the config itself.
      if (apiError.code === 'CSRF_FAILED' && !error.config.csrfRetry) {
        csrfToken = null
        return api.request({ ...error.config, csrfRetry: true })
      }
      const url = error.config.url ?? ''
      if (apiError.status === 401 && !url.startsWith('/auth/login') && url !== '/auth/me') {
        unauthorizedHandler?.()
      }
    }
    throw error
  },
)

/* --------------------------------------------------------------- helpers */

/** Send a request and return the `data` of its success envelope (or throw ApiError). */
export async function apiRequest<T>(
  method: Method,
  url: string,
  options: { data?: unknown; params?: object } = {},
): Promise<T> {
  try {
    const response = await api.request<ApiEnvelope<T>>({ method, url, ...options })
    const body = response.data
    if (!body.success) throw new ApiError(body.error, response.status)
    return body.data
  } catch (error) {
    throw toApiError(error)
  }
}

/** POST multipart form data, reporting upload progress as a fraction from 0 to 1. */
export async function apiUpload<T>(
  url: string,
  form: FormData,
  onProgress?: (fraction: number) => void,
): Promise<T> {
  try {
    const response = await api.post<ApiEnvelope<T>>(url, form, {
      timeout: 0, // large files on slow connections
      onUploadProgress: (event) => {
        if (onProgress && event.total) onProgress(Math.min(event.loaded / event.total, 1))
      },
    })
    const body = response.data
    if (!body.success) throw new ApiError(body.error, response.status)
    return body.data
  } catch (error) {
    throw toApiError(error)
  }
}

export const apiGet = <T>(url: string, params?: object) => apiRequest<T>('GET', url, { params })
export const apiPost = <T>(url: string, data?: unknown) => apiRequest<T>('POST', url, { data })
export const apiPatch = <T>(url: string, data?: unknown) => apiRequest<T>('PATCH', url, { data })
export const apiPut = <T>(url: string, data?: unknown) => apiRequest<T>('PUT', url, { data })
export const apiDelete = <T>(url: string) => apiRequest<T>('DELETE', url)
