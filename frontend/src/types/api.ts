/**
 * Shared types for the NLP-RS REST API. Every endpoint lives under /api and answers with
 * one of the two envelopes below. Keep this file in sync with docs/API.md.
 */

export interface ApiSuccess<T> {
  success: true
  data: T
}

export interface ApiErrorBody {
  code: string
  message: string
  details: Record<string, unknown>
}

export interface ApiFailure {
  success: false
  error: ApiErrorBody
}

export type ApiEnvelope<T> = ApiSuccess<T> | ApiFailure

/* ---------------------------------------------------------------- health */

export type ServiceState = 'ok' | 'unavailable'

export interface HealthChecks {
  database: ServiceState
  redis: ServiceState
}

/** Data of a 200 response from GET /api/health. */
export interface HealthStatus {
  status: 'ok'
  version: string
  checks: HealthChecks
}

/** `error.details` of a 503 response from GET /api/health. */
export interface HealthFailureDetails {
  version: string
  checks: HealthChecks
}
