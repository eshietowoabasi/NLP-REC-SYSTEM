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

/** `error.details` of a 422 VALIDATION_ERROR (and of 409 conflicts on specific fields). */
export interface FieldErrorDetails {
  fields?: Record<string, string[]>
}

export interface Pagination {
  page: number
  per_page: number
  total: number
  pages: number
}

/** Data of every paginated list endpoint. */
export interface Paginated<T> {
  items: T[]
  pagination: Pagination
}

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

/* ------------------------------------------------------------ auth/users */

export type UserRole = 'admin' | 'planner' | 'viewer'

export interface User {
  id: number
  username: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

export interface CsrfTokenResponse {
  csrf_token: string
}

/** POST /api/auth/login */
export interface LoginRequest {
  identifier: string
  password: string
}

export interface LoginResponse {
  user: User
  csrf_token: string
}

/** POST /api/auth/change-password */
export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

/** POST /api/admin/users */
export interface CreateUserRequest {
  username: string
  email: string
  full_name: string
  role: UserRole
  password: string
}

/** PATCH /api/admin/users/{id} — only supplied fields change. */
export interface UpdateUserRequest {
  full_name?: string
  email?: string
  role?: UserRole
  is_active?: boolean
  new_password?: string
}

/** Query parameters of GET /api/admin/users */
export interface UserListParams {
  page?: number
  per_page?: number
  role?: UserRole
  is_active?: 'true' | 'false'
  search?: string
}
