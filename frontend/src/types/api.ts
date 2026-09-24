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

/* ------------------------------------------------------------- documents */

export type SourceCategory = 'job_market' | 'institutional' | 'policy' | 'academic' | 'nuc_core'
/** Categories offered when uploading to the library (nuc_core has its own admin screen). */
export type UploadCategory = Exclude<SourceCategory, 'nuc_core'>
export type FileType = 'pdf' | 'docx' | 'txt'
export type DocumentStatus = 'uploaded' | 'parsing' | 'ready' | 'failed' | 'archived'
export type SessionStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface UserRef {
  id: number
  full_name: string
}

export interface DocumentSummary {
  id: number
  title: string
  original_filename: string
  file_type: FileType
  file_size: number
  source_category: SourceCategory
  processing_status: DocumentStatus
  error_message: string | null
  page_count: number | null
  word_count: number | null
  uploaded_at: string
  parsed_at: string | null
  uploaded_by: UserRef
}

export interface PassageSummary {
  id: number
  position: number
  page_number: number | null
  text: string
}

export interface SessionRef {
  id: number
  session_name: string
  status: SessionStatus
  created_at: string
}

/** GET /api/documents/{id} */
export interface DocumentDetail extends DocumentSummary {
  passage_count: number
  preview: PassageSummary[]
  sessions: SessionRef[]
  is_nuc_core: boolean
}

/** GET /api/documents */
export interface DocumentList extends Paginated<DocumentSummary> {
  category_counts: Record<UploadCategory, number>
}

export interface DocumentListParams {
  page?: number
  per_page?: number
  category?: SourceCategory
  status?: DocumentStatus
  search?: string
}

export interface RejectedFile {
  filename: string
  reason: string
}

/** POST /api/documents (201). A 422 carries `error.details.rejected: RejectedFile[]`. */
export interface UploadResult {
  accepted: DocumentSummary[]
  rejected: RejectedFile[]
}

/* -------------------------------------------------------------- NUC core */

export interface NucCoreVersion {
  id: number
  version_label: string
  is_active: boolean
  created_at: string
  uploaded_by: UserRef
  document: DocumentSummary
}

/** GET /api/nuc-core */
export interface NucCoreState {
  active: NucCoreVersion | null
  latest: NucCoreVersion | null
}

/** Query parameters of GET /api/admin/users */
export interface UserListParams {
  page?: number
  per_page?: number
  role?: UserRole
  is_active?: 'true' | 'false'
  search?: string
}
