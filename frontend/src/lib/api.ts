import axios, { AxiosError } from 'axios'

import type { ApiEnvelope, ApiErrorBody } from '@/types/api'

/**
 * Axios instance for the Flask API. Requests go to the same origin (/api), so the session
 * cookie is sent automatically: Vite proxies /api in development and Nginx does in Docker.
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

/** GET a resource and return the `data` of its success envelope. */
export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  try {
    const response = await api.get<ApiEnvelope<T>>(url, { params })
    const body = response.data
    if (!body.success) throw new ApiError(body.error, response.status)
    return body.data
  } catch (error) {
    throw toApiError(error)
  }
}
