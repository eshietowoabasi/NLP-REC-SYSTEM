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

/* -------------------------------------------------------------- sessions */

export type SessionStage =
  | 'queued'
  | 'validating'
  | 'loading'
  | 'keywords'
  | 'skills'
  | 'embeddings'
  | 'themes'
  | 'overlap'
  | 'scoring'
  | 'completed'

export interface ScoreWeights {
  ner: number
  topic: number
  novelty: number
}

/** A session's parameter snapshot (defaults + overrides at creation). */
export interface SessionParameterConfig {
  weights: ScoreWeights
  similarity_threshold: number
  max_recommendations: number
  min_topic_size: number
  evidence_per_recommendation: number
  sbert_model: string
  spacy_model: string
}

export interface SessionSummary {
  id: number
  session_name: string
  status: SessionStatus
  current_stage: SessionStage | null
  progress_percent: number
  created_by: UserRef
  document_count: number
  recommendation_count: number
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface SessionDocument {
  id: number
  title: string
  source_category: SourceCategory
  processing_status: DocumentStatus
}

/** GET /api/sessions/{id} */
export interface SessionDetail extends SessionSummary {
  parameter_config: SessionParameterConfig
  stage_timings: Partial<Record<SessionStage, number>>
  error_message: string | null
  nuc_core_version: { id: number; version_label: string } | null
  documents: SessionDocument[]
  topic_count: number | null
}

/** GET /api/sessions/defaults */
export interface SessionDefaults {
  parameters: SessionParameterConfig
  max_documents: number
  nuc_core_version: { id: number; version_label: string } | null
}

/** POST /api/sessions */
export interface CreateSessionRequest {
  session_name: string
  document_ids: number[]
  parameters?: {
    weights?: ScoreWeights
    similarity_threshold?: number
    max_recommendations?: number
  }
  run?: boolean
}

export interface SessionListParams {
  page?: number
  per_page?: number
  status?: SessionStatus
  search?: string
}

/* ------------------------------------------------ session results (evidence) */

export interface KeywordScore {
  term: string
  score: number
  passage_count: number
}

/** GET /api/sessions/{id}/keywords[?category=] */
export interface KeywordResults {
  overall: KeywordScore[]
  by_category: Partial<Record<SourceCategory, KeywordScore[]>>
  passage_count: number
}

export type SkillLabel = 'SKILL' | 'TOOL' | 'CERT' | 'LANGUAGE'

export interface SkillStat {
  name: string
  label: SkillLabel
  mentions: number
  document_frequency: number
  by_category: Partial<Record<SourceCategory, number>>
}

/** GET /api/sessions/{id}/entities */
export interface EntityResults {
  skills: SkillStat[]
  passages_with_skills: number
  passage_count: number
  document_count: number
}

export interface WeightedTerm {
  term: string
  weight: number
}

export interface TopicSample {
  passage_id: number
  document_id: number
  document_title: string
  text: string
}

export interface TopicResult {
  topic_id: number
  title: string
  keywords: WeightedTerm[]
  size: number
  document_count: number
  mean_probability: number
  strength_raw: number
  strength: number
  samples: TopicSample[]
}

/** GET /api/sessions/{id}/topics */
export interface TopicResults {
  topic_count: number
  outlier_passages: number
  modelled_passages: number
  topics: TopicResult[]
}

export type OverlapStatus = 'Potential Duplicate' | 'No Significant Overlap'

export interface SimilarityCandidate {
  topic_id: number
  title: string
  max_similarity: number
  novelty: number
  overlap_status: OverlapStatus
  closest_nuc_passage: { id: number; text: string; page_number: number | null }
}

/** GET /api/sessions/{id}/similarity */
export interface SimilarityResults {
  threshold: number
  candidates: SimilarityCandidate[]
  nuc_core_version: { id: number; version_label: string } | null
}

/* ------------------------------------------------------- recommendations */

export type PlannerDecision = 'accepted' | 'rejected' | 'flagged'
export type DecisionFilter = 'all' | 'undecided' | PlannerDecision

export interface RecommendationSkill {
  name: string
  label: SkillLabel
  mentions: number
  document_frequency: number
}

export interface Recommendation {
  id: number
  session_id: number
  rank: number
  topic_id: number
  auto_title: string
  topic_title: string
  topic_description: string
  keywords: WeightedTerm[]
  skills: RecommendationSkill[]
  ner_score: number
  topic_score: number
  novelty_score: number
  composite_score: number
  max_similarity: number
  overlap_status: OverlapStatus
  planner_decision: PlannerDecision | null
  planner_notes: string | null
  decided_at: string | null
  decided_by: UserRef | null
  has_mapping: boolean
}

export interface ReviewCounts {
  total: number
  reviewed: number
  undecided: number
  accepted: number
  rejected: number
  flagged: number
  potential_duplicates: number
}

/** GET /api/sessions/{id}/recommendations */
export interface RecommendationList {
  items: Recommendation[]
  counts: ReviewCounts
}

export interface RecommendationListParams {
  decision?: DecisionFilter
  hide_duplicates?: boolean
}

export interface Evidence {
  passage_id: number
  relevance_score: number
  text: string
  page_number: number | null
  position: number
  document: { id: number; title: string; source_category: SourceCategory }
}

export interface NucPassage {
  id: number
  text: string
  page_number: number | null
  document_title: string
  version_label: string | null
}

export interface CourseMapping {
  id: number
  recommendation_id: number
  course_code: string
  course_title: string
  credit_units: 1 | 2 | 3
  prerequisites: string[]
  learning_outcomes: string[]
  created_by: UserRef
  created_at: string
  updated_at: string
}

/** GET /api/recommendations/{id} */
export interface RecommendationDetail extends Recommendation {
  evidence: Evidence[]
  closest_nuc_passage: NucPassage | null
  session: {
    id: number
    session_name: string
    weights: ScoreWeights
    similarity_threshold: number
  }
  mapping: CourseMapping | null
}

/** PATCH /api/recommendations/{id} */
export interface RecommendationEditRequest {
  topic_title?: string
  topic_description?: string
}

/** PATCH /api/recommendations/{id}/decision — `decision: null` clears it. */
export interface DecisionRequest {
  decision: PlannerDecision | null
  notes?: string | null
}

/** POST /api/recommendations/{id}/mapping and PUT /api/mappings/{id} */
export interface MappingRequest {
  course_code: string
  course_title: string
  credit_units: 1 | 2 | 3
  prerequisites: string[]
  learning_outcomes: string[]
}

export interface CurriculumCourse extends CourseMapping {
  recommendation: {
    id: number
    rank: number
    topic_title: string
    composite_score: number
    overlap_status: OverlapStatus
  }
}

/** GET /api/sessions/{id}/curriculum */
export interface ProposedCurriculum {
  session: { id: number; session_name: string }
  courses: CurriculumCourse[]
  total_units: number
  credit_unit_allowance: number | null
  remaining_units: number | null
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
